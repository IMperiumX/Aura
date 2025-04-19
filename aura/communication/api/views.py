import logging
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.decorators import parser_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from aura.communication.models import Attachment
from aura.communication.models import Folder
from aura.communication.models import Message
from aura.communication.models import TherapySessionThread
from aura.communication.models import Thread

from .serializers import AttachmentSerializer
from .serializers import FolderSerializer
from .serializers import MessageSerializer
from .serializers import TherapySessionThreadSerializer
from .serializers import ThreadSerializer
from .utils import validate_file
from .utils import validate_image

logger = logging.getLogger(__name__)


class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_group", "is_active"]
    search_fields = ["subject", "participants__username"]
    ordering_fields = ["created", "modified"]

    def get_queryset(self):
        return self.queryset.filter(participants=self.request.user)

    @action(detail=True, methods=["post"])
    def add_participant(self, request, pk=None):
        thread = self.get_object()
        user_id = request.data.get("user_id")
        if user_id:
            thread.participants.add(user_id)
            return Response({"status": "participant added"})
        return Response(
            {"error": "user_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        stats = self.get_queryset().aggregate(
            total_threads=Count("id"),
            active_threads=Count("id", filter=Q(is_active=True)),
            group_threads=Count("id", filter=Q(is_group=True)),
        )
        return Response(stats)

    @action(detail=True, methods=["post"])
    def upload_attachment(self, request, pk=None):
        thread = self.get_object()
        if not thread.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "Not a participant in this thread"},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        attachment = Attachment.objects.create(
            file=file,
            name=file.name,
            size=file.size,
            content_type=file.content_type,
            uploaded_by=request.user,
        )

        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            text=f"Shared file: {file.name}",
            message_type=Message.MessageTypes.FILE,
        )
        message.attachments.add(attachment)

        thread.last_message = message
        thread.save()

        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["thread", "sender", "read_at"]
    search_fields = ["text"]

    def get_queryset(self):
        return self.queryset.filter(thread__participants=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.mark_read()
        return Response({"status": "message marked as read"})

    @action(detail=False, methods=["post"])
    def bulk_mark_read(self, request):
        thread_id = request.data.get("thread_id")
        if thread_id:
            messages = self.get_queryset().filter(
                thread_id=thread_id,
                read_at__isnull=True,
            )
            messages.update(read_at=timezone.now())
            return Response({"status": f"{messages.count()} messages marked as read"})
        return Response(
            {"error": "thread_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def unread(self, request):
        queryset = (
            self.get_queryset()
            .filter(read_at__isnull=True)
            .exclude(sender=request.user)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class TherapySessionThreadViewSet(ThreadViewSet):
    queryset = TherapySessionThread.objects.all()
    serializer_class = TherapySessionThreadSerializer

    def get_queryset(self):
        return self.queryset.filter(
            Q(session__therapist=self.request.user)
            | Q(session__patient=self.request.user),
        )


class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer

    @action(detail=False, methods=["POST"])
    @parser_classes([MultiPartParser])
    def upload(self, request):
        file = request.FILES.get("file")
        chunk_number = int(request.POST.get("chunk_number", 0))
        total_chunks = int(request.POST.get("total_chunks", 1))
        file_id = request.POST.get("file_id")

        if not file or not file_id:
            return Response(
                {"error": "File and file_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_file_path = Path(settings.MEDIA_ROOT) / "temp" / file_id

        try:
            self.handle_chunk(temp_file_path, file, chunk_number, total_chunks)

            if chunk_number == total_chunks - 1:
                with temp_file_path.open("rb") as f:
                    file_content = f.read()

                validate_file(file_content)

                attachment = Attachment.create_from_file(
                    ContentFile(file_content, name=file.name),
                    name=file.name,
                    content_type=file.content_type,
                )

                serializer = self.get_serializer(attachment)
                temp_file_path.unlink()  # Clean up temporary file
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            progress = (chunk_number + 1) / total_chunks * 100
            return Response(
                {"message": f"Chunk received. Progress: {progress:.2f}%"},
                status=status.HTTP_202_ACCEPTED,
            )

        except (ValidationError, OSError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            # Log the unexpected exception
            logger.exception("Unexpected error occurred")
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def handle_chunk(self, temp_file_path, file, chunk_number, total_chunks):
        if chunk_number == 0:
            temp_file_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "wb"
        else:
            mode = "ab"

        with temp_file_path.open(mode) as destination:
            bytes_written = 0
            for chunk in file.chunks():
                destination.write(chunk)
                bytes_written += len(chunk)

            progress = (chunk_number + 1) / total_chunks * 100
            msg = f"Chunk {chunk_number + 1}/{total_chunks} processed. Progress: {progress:.2f}%"
            logger.info(msg)

        return bytes_written

    @action(
        detail=False,
        methods=["POST"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response(
                {"error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_image(image)
            attachment = Attachment.objects.create(
                image=image,
                name=image.name,
                content_type=image.content_type,
                size=image.size,
            )
            serializer = self.get_serializer(attachment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (ValidationError, OSError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error occurred")
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_queryset(self):
        return self.queryset.filter(message__thread__participants=self.request.user)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        response = HttpResponse(attachment.file, content_type=attachment.content_type)
        response["Content-Disposition"] = f'attachment; filename="{attachment.name}"'
        return response
