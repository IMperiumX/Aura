"""
Integrates with a video conferencing service (e.g., Twilio Video, Jitsi, Zoom API, Agora)
or implements WebRTC directly.

- Text Chat: Real-time messaging for sessions and offline communication.
- Video/Audio Calls: Secure, high-quality video/audio communication.
- File Sharing: Secure file transfer for sharing documents, worksheets, etc.
        - Appointment Scheduling: Integration with communication tools for reminders.
- Notifications: Real-time and scheduled notifications via email, SMS, or in-app.
- Group Sessions: Support for group therapy or multiparty communication.
- Recording (Optional): Secure storage and retrieval of session recordings.
- 1.2 Compliance & Security Requirements:
- HIPAA Compliance: Ensure all communication methods comply with healthcare regulations (e.g., encryption, data retention).
- GDPR Compliance: For platforms operating in Europe.
- Data Encryption: Use end-to-end encryption for all communication.
"""

# creat a robust data models for this feature
import hashlib
import logging

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

from aura.communication.managers import MessageManager
from aura.communication.managers import ThreadManager
from aura.mentalhealth.models import TherapySession

from . import MAX_LENGTH
from . import MAX_LENGTH_SMALL
from . import MAX_LENGTH_TINY

logger = logging.getLogger(__name__)


class Thread(TimeStampedModel):
    """
    A thread represents a conversation between two or more users.
    """

    subject = models.CharField(
        max_length=MAX_LENGTH_SMALL,
        blank=True,
        default="",
        verbose_name=_("subject"),
    )
    is_group = models.BooleanField(default=False, verbose_name=_("is group"))
    is_active = models.BooleanField(default=True, verbose_name=_("is active"))

    # relations
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="threads",
        verbose_name=_("participants"),
    )
    last_message = models.ForeignKey(
        "communication.Message",
        on_delete=models.SET_NULL,
        related_name="message_thread",
        blank=True,
        null=True,
        verbose_name=_("last message"),
    )

    objects = ThreadManager()

    class Meta:
        verbose_name = _("thread")
        verbose_name_plural = _("threads")

    def __str__(self):
        return self.subject or f"Thread {self.id}: {self.subject}"

    def get_absolute_url(self):
        return reverse("communication:thread-detail", kwargs={"pk": self.pk})


# TODO: Add a ReadReceipt model to track when messages are read by each participant.
class Message(TimeStampedModel):
    """
    A message represents a single message in a thread.
    """

    class MessageTypes(models.TextChoices):
        TEXT = "text", _("Text")
        SYSTEM = "system", _("System")
        FILE = "file", _("File")

        __empty__ = _("(Unknown)")

    text = models.TextField(verbose_name=_("text"))
    read_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("read at"),
    )
    message_type = models.CharField(
        max_length=MAX_LENGTH_TINY,
        choices=MessageTypes.choices,
        default="text",
        verbose_name=_("message type"),
    )
    data_retention_period = models.DurationField(
        default=timezone.timedelta(days=settings.DATA_RETENTION_PERIOD),
        verbose_name=_("data retention period"),
    )

    # relateions
    thread = models.ForeignKey(
        "communication.Thread",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("thread"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name=_("sender"),
    )

    objects = MessageManager()

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __str__(self):
        return f"Message {self.id}"

    def get_absolute_url(self):
        return reverse("communication:message-detail", kwargs={"pk": self.pk})

    def mark_read(self):
        self.read_at = timezone.now()
        self.save()

    def is_read(self):
        return self.read_at is not None

    def is_unread(self):
        return self.read_at is None


class TherapySessionThread(Thread):
    """
    A thread represents a conversation between two or more users.
    """

    # relations
    session = models.OneToOneField(
        TherapySession,
        on_delete=models.CASCADE,
        related_name="thread",
        verbose_name=_("session"),
    )

    class Meta:
        verbose_name = _("therapy session thread")
        verbose_name_plural = _("therapy session threads")

    def __str__(self):
        return self.subject or f"Therapy Session Thread {self.id}: {self.subject}"


class FileContent(models.Model):
    hash = models.CharField(max_length=64, unique=True)
    content = models.FileField(upload_to="file_contents/")

    def __str__(self):
        return self.hash


class Attachment(TimeStampedModel):
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    version_number = models.PositiveIntegerField(default=1)
    file_content = models.ForeignKey(FileContent, on_delete=models.PROTECT)

    message = models.ForeignKey(
        "communication.Message",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    previous_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="next_version",
        blank=True,
        null=True,
    )

    @property
    def file(self):
        return self.file_content.content

    @classmethod
    def create_from_file(cls, file, **kwargs):
        file_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)  # Reset file pointer

        file_content, created = FileContent.objects.get_or_create(
            hash=file_hash,
            defaults={"content": file},
        )

        return cls.objects.create(file_content=file_content, size=file.size, **kwargs)


class Folder(TimeStampedModel):
    """
    A folder represents a folder in a user's file system.
    """

    name = models.CharField(max_length=MAX_LENGTH, verbose_name=_("name"))

    # relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="folders",
        verbose_name=_("user"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
        verbose_name=_("parent"),
    )

    class Meta:
        verbose_name = _("folder")
        verbose_name_plural = _("folders")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("communication:folder-detail", kwargs={"pk": self.pk})
