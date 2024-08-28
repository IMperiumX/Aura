from django.contrib import admin

from .models import Attachment
from .models import FileContent
from .models import Folder
from .models import Message
from .models import TherapySessionThread
from .models import Thread


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "subject",
        "is_group",
        "is_active",
        "last_message",
    )
    list_filter = (
        "created",
        "modified",
        "is_group",
        "is_active",
        "last_message",
    )
    raw_id_fields = ("participants",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "text",
        "read_at",
        "message_type",
        "data_retention_period",
        "thread",
        "sender",
    )
    list_filter = ("created", "modified", "read_at", "thread", "sender")


@admin.register(TherapySessionThread)
class TherapySessionThreadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "subject",
        "is_group",
        "is_active",
        "last_message",
        "session",
    )
    list_filter = (
        "created",
        "modified",
        "is_group",
        "is_active",
        "last_message",
        "session",
    )


@admin.register(FileContent)
class FileContentAdmin(admin.ModelAdmin):
    list_display = ("id", "hash", "content")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "name",
        "content_type",
        "size",
        "version_number",
        "file_content",
        "message",
        "previous_version",
    )
    list_filter = (
        "created",
        "modified",
        "file_content",
        "message",
        "previous_version",
    )
    search_fields = ("name",)


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("id", "created", "modified", "name", "user", "parent")
    list_filter = ("created", "modified", "user", "parent")
    search_fields = ("name",)
