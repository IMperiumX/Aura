import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class EncryptedJSONField(models.JSONField):
    """
    A JSONField that encrypts its content before saving to the database
    and decrypts when reading from the database.
    """

    def __init__(self, *args, **kwargs):
        self.cipher_suite = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            if isinstance(value, str) and value.startswith("gAAAAA"):
                decrypted = self.cipher_suite.decrypt(value.encode())
                return json.loads(decrypted.decode())
            return value
        except Exception:
            return value

    def to_python(self, value):
        if isinstance(value, dict) or isinstance(value, list):
            return value
        if value is None:
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def get_prep_value(self, value):
        if value is None:
            return value
        json_string = json.dumps(value)
        encrypted = self.cipher_suite.encrypt(json_string.encode())
        return encrypted.decode()


class EncryptedTextField(models.TextField):
    """
    A TextField that encrypts its content before saving to the database
    and decrypts when reading from the database.
    """

    def __init__(self, *args, **kwargs):
        self.cipher_suite = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            if isinstance(value, str) and value.startswith("gAAAAA"):
                decrypted = self.cipher_suite.decrypt(value.encode())
                return decrypted.decode()
            return value
        except Exception:
            return value

    def to_python(self, value):
        if value is None:
            return value
        return str(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        encrypted = self.cipher_suite.encrypt(str(value).encode())
        return encrypted.decode()


class EncryptedCharField(models.CharField):
    """
    A CharField that encrypts its content before saving to the database
    and decrypts when reading from the database.
    """

    def __init__(self, *args, **kwargs):
        self.cipher_suite = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            if isinstance(value, str) and value.startswith("gAAAAA"):
                decrypted = self.cipher_suite.decrypt(value.encode())
                return decrypted.decode()
            return value
        except Exception:
            return value

    def to_python(self, value):
        if value is None:
            return value
        return str(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        encrypted = self.cipher_suite.encrypt(str(value).encode())
        return encrypted.decode()
