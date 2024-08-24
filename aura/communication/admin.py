from django.contrib import admin

from .models import Message
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
        "encrypted_content",
        "message_type",
        "data_retention_period",
        "thread",
        "sender",
    )
    list_filter = ("created", "modified", "read_at", "thread", "sender")
