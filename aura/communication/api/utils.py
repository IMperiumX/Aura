from typing import Literal
import magic
from django.conf import settings
from pdfreader import SimplePDFViewer

from .exceptions import FileSizeExceedsLimitError
from .exceptions import PasswordProtectedPDFError
from .exceptions import UnsupportedFileTypeError


def validate_file(file_content):
    mime_type = magic.from_buffer(file_content, mime=True)
    if mime_type not in settings.ALLOWED_FILE_TYPES:
        raise UnsupportedFileTypeError(mime_type)
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise FileSizeExceedsLimitError(settings.MAX_FILE_SIZE)

    if mime_type == "application/pdf":
        if not check_pdf_password(file_content):
            raise PasswordProtectedPDFError


def check_pdf_password(file_content):
    viewer = SimplePDFViewer(file_content)
    viewer.navigate(1)
    return viewer.current_page_number == 1


def validate_image(image):
    mime_type = magic.from_buffer(image, mime=True)
    if mime_type not in settings.ALLOWED_IMAGE_TYPES:
        raise UnsupportedFileTypeError(mime_type)
    if image.size > settings.MAX_IMAGE_SIZE:
        raise FileSizeExceedsLimitError(settings.MAX_IMAGE_SIZE)

def get_user_type(user) -> Literal['admin', 'therapist', 'patient']:
    if user.is_superuser:
        return "admin"
    elif user.is_staff:
        return "therapist"
    else:
        return "patient"
