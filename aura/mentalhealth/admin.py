from django.contrib import admin

from .models import ChatbotInteraction
from .models import TherapySession


@admin.register(TherapySession)
class TherapySessionAdmin(admin.ModelAdmin):
    """ """
    list_display = (
        "id",
        "session_type",
        "status",
        "summary",
        "notes",
        "scheduled_at",
        "started_at",
        "ended_at",
        "created_at",
        "therapist",
        "patient",
    )
    list_filter = (
        "scheduled_at",
        "started_at",
        "ended_at",
        "created_at",
        "therapist",
        "patient",
    )
    date_hierarchy = "created_at"


@admin.register(ChatbotInteraction)
class ChatbotInteractionAdmin(admin.ModelAdmin):
    """ """
    list_display = (
        "id",
        "message",
        "response",
        "conversation_log",
        "interaction_date",
        "created_at",
        "user",
    )
    list_filter = ("interaction_date", "created_at", "user")
    date_hierarchy = "created_at"
