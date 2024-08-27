import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.decorators import parser_classes
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


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer


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
            for chunk in file.chunks():
                destination.write(chunk)

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


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer


class TherapySessionThreadViewSet(viewsets.ModelViewSet):
    queryset = TherapySessionThread.objects.all()
    serializer_class = TherapySessionThreadSerializer
