from django.contrib import admin

from .models import ChatbotInteraction
from .models import TherapySession


@admin.register(TherapySession)
class TherapySessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "therapist",
        "patient",
        "session_type",
        "status",
        "scheduled_at",
        "started_at",
        "ended_at",
        "created_at",
    )
    list_filter = (
        "therapist",
        "patient",
        "scheduled_at",
        "started_at",
        "ended_at",
        "created_at",
    )
    date_hierarchy = "created_at"


@admin.register(ChatbotInteraction)
class ChatbotInteractionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "response", "created_at")
    list_filter = ("user", "created_at")
    date_hierarchy = "created_at"