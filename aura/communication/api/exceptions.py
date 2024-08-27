from django.core.exceptions import ValidationError


class UnsupportedFileTypeError(ValidationError):
    def __init__(self, file_type):
        super().__init__(f"Unsupported file type: {file_type}")


class FileSizeExceedsLimitError(ValidationError):
    def __init__(self, max_size):
        super().__init__(f"File size exceeds the maximum limit of {max_size} bytes")


class PasswordProtectedPDFError(ValidationError):
    def __init__(self):
        super().__init__("The PDF is password-protected")
