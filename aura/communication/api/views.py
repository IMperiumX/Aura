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
from rest_framework.permissions import IsAuthenticated

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
from aura.analytics import AnalyticsRecordingMixin
from aura.communication.api.utils import get_user_type

logger = logging.getLogger(__name__)


class ThreadViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
    """
    API viewset for managing conversation threads.
    Handles thread creation, retrieval, and management.
    """
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter threads based on user participation.
        Users can only see threads they're part of.
        """
        return self.queryset.filter(
            Q(messages__sender=self.request.user) |
            Q(participants=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        """Create thread with analytics tracking."""
        thread = serializer.save(created_by=self.request.user)

        try:
            # Add creator as participant if not already included
            if not thread.participants.filter(id=self.request.user.id).exists():
                thread.participants.add(self.request.user)

            # Determine thread type
            thread_type = 'general'
            if hasattr(thread, 'therapy_session'):
                thread_type = 'therapy_session'

            self.record_analytics_event(
                "thread.created",
                instance=thread,
                request=self.request,
                thread_id=thread.id,
                created_by_id=self.request.user.id,
                thread_type=thread_type,
                participant_count=thread.participants.count(),
                therapy_session_id=getattr(thread, 'therapy_session_id', None),
            )
        except Exception as e:
            logger.warning(f"Failed to record thread creation event: {e}")

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to the thread."""
        thread = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)

            if not thread.participants.filter(id=user.id).exists():
                thread.participants.add(user)

                self.record_analytics_event(
                    "thread.participant_added",
                    instance=thread,
                    request=request,
                    thread_id=thread.id,
                    participant_id=user.id,
                    added_by_id=request.user.id,
                )

            return Response({'status': 'participant added'})

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        stats = self.get_queryset().aggregate(
            total_threads=Count("id"),
            active_threads=Count("id", filter=Q(is_active=True)),
            group_threads=Count("id", filter=Q(is_group=True)),
        )
        return Response(stats)


class MessageViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
    """
    API viewset for managing messages within threads.
    Handles message creation, retrieval, and management.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["thread", "sender", "read_at"]
    search_fields = ["text"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter messages based on thread access.
        Users can only see messages in threads they're part of.
        """
        user_threads = Thread.objects.filter(
            Q(messages__sender=self.request.user) |
            Q(participants=self.request.user)
        ).distinct()

        return self.queryset.filter(thread__in=user_threads)

    def perform_create(self, serializer):
        """Create message with analytics tracking."""
        message = serializer.save(sender=self.request.user)

        try:
            # Determine sender type
            sender_type = get_user_type(self.request.user)

            # Count recipients (thread participants excluding sender)
            recipient_count = message.thread.participants.exclude(id=self.request.user.id).count()

            # Check for attachments
            has_attachments = message.attachments.exists() if hasattr(message, 'attachments') else False

            # Determine thread type
            thread_type = 'general'
            if hasattr(message.thread, 'therapy_session'):
                thread_type = 'therapy_session'

            self.record_analytics_event(
                "message.sent",
                instance=message,
                request=self.request,
                message_id=message.id,
                thread_id=message.thread.id,
                sender_id=self.request.user.id,
                sender_type=sender_type,
                recipient_count=recipient_count,
                message_length=len(message.text) if message.text else 0,
                has_attachments=has_attachments,
                thread_type=thread_type,
            )
        except Exception as e:
            logger.warning(f"Failed to record message sent event: {e}")

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read by the current user."""
        message = self.get_object()

        # Implementation would track read status
        # For now, just return success

        try:
            self.record_analytics_event(
                "message.read",
                instance=message,
                request=request,
                message_id=message.id,
                reader_id=request.user.id,
                read_delay_minutes=0,  # Could calculate actual delay
            )
        except Exception as e:
            logger.warning(f"Failed to record message read event: {e}")

        return Response({'status': 'marked as read'})

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


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class TherapySessionThreadViewSet(ThreadViewSet):
    """
    Specialized viewset for therapy session threads.
    Inherits from ThreadViewSet with therapy-specific filtering.
    """
    queryset = TherapySessionThread.objects.all()
    serializer_class = TherapySessionThreadSerializer

    def get_queryset(self):
        """Filter therapy session threads based on user role."""
        return self.queryset.filter(
            Q(session__therapist=self.request.user)
            | Q(session__patient=self.request.user),
        )

    def perform_create(self, serializer):
        """Create therapy session thread with enhanced analytics."""
        thread = serializer.save(created_by=self.request.user)

        try:
            self.record_analytics_event(
                "thread.created",
                instance=thread,
                request=self.request,
                thread_id=thread.id,
                created_by_id=self.request.user.id,
                thread_type='therapy_session',
                participant_count=2,  # Therapist + Patient
                therapy_session_id=thread.session.id,
            )
        except Exception as e:
            logger.warning(f"Failed to record therapy session thread creation event: {e}")

    @action(detail=True, methods=['post'])
    def start_video_call(self, request, pk=None):
        """Initiate a video call for the therapy session."""
        thread = self.get_object()

        # This would integrate with your video calling system
        # For now, we'll just track the analytics event

        try:
            import uuid
            call_id = str(uuid.uuid4())

            self.record_analytics_event(
                "video_call.started",
                request=request,
                call_id=call_id,
                initiator_id=request.user.id,
                participant_count=2,  # Therapist + Patient
                call_type='therapy',
                therapy_session_id=thread.session.id,
            )

            return Response({
                'status': 'video call started',
                'call_id': call_id,
                'participants': [thread.session.therapist.id, thread.session.patient.id]
            })

        except Exception as e:
            logger.warning(f"Failed to record video call start event: {e}")
            return Response({'error': 'Failed to start video call'}, status=500)

    @action(detail=True, methods=['post'])
    def end_video_call(self, request, pk=None):
        """End a video call for the therapy session."""
        call_id = request.data.get('call_id')
        duration_minutes = request.data.get('duration_minutes', 0)
        quality_rating = request.data.get('quality_rating')

        try:
            self.record_analytics_event(
                "video_call.ended",
                request=request,
                call_id=call_id,
                duration_minutes=int(duration_minutes),
                participant_count=2,
                ended_by_id=request.user.id,
                quality_rating=int(quality_rating) if quality_rating else None,
            )

            return Response({'status': 'video call ended'})

        except Exception as e:
            logger.warning(f"Failed to record video call end event: {e}")
            return Response({'error': 'Failed to record call end'}, status=500)


class AttachmentViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
    """
    API viewset for managing file attachments.
    Handles file upload and attachment management.
    """
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter attachments based on message access."""
        user_messages = Message.objects.filter(
            thread__participants=self.request.user
        )
        return self.queryset.filter(message__in=user_messages)

    def perform_create(self, serializer):
        """Create attachment with analytics tracking."""
        attachment = serializer.save(uploaded_by=self.request.user)

        try:
            # Get file information
            file_size = attachment.file.size if hasattr(attachment.file, 'size') else 0
            file_type = attachment.file.name.split('.')[-1] if hasattr(attachment.file, 'name') else 'unknown'

            self.record_analytics_event(
                "attachment.uploaded",
                instance=attachment,
                request=self.request,
                attachment_id=attachment.id,
                uploader_id=self.request.user.id,
                file_size_bytes=file_size,
                file_type=file_type,
                thread_id=attachment.message.thread.id if attachment.message else None,
                message_id=attachment.message.id if attachment.message else None,
            )
        except Exception as e:
            logger.warning(f"Failed to record attachment upload event: {e}")

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

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        response = HttpResponse(attachment.file, content_type=attachment.content_type)
        response["Content-Disposition"] = f'attachment; filename="{attachment.name}"'
        return response
