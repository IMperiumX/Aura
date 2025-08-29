from django.contrib import admin

from .models import ChatbotInteraction
from .models import Disorder
from .models import TherapyApproach
from .models import TherapySession

ADMIN_CHAR_LIMNIT = 50


@admin.register(TherapySession)
class TherapySessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "session_type",
        "status",
        "summary",
        "notes",
        "scheduled_at",
        "started_at",
        "ended_at",
        "target_audience",
        "recurrences",
        "therapist",
        "patient",
    )
    list_filter = (
        "created",
        "modified",
        "scheduled_at",
        "started_at",
        "ended_at",
        "therapist",
        "patient",
    )


@admin.register(TherapyApproach)
class TherapyApproachAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "limited_description", "created", "modified")
    list_filter = ("created", "modified")
    search_fields = ("name",)

    @admin.display(
        description="Description",
    )
    def limited_description(self, obj):
        return obj.description[:ADMIN_CHAR_LIMNIT] + "..."


@admin.register(ChatbotInteraction)
class ChatbotInteractionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "message",
        "response",
        "conversation_log",
        "interaction_date",
        "user",
    )
    list_filter = ("created", "modified", "interaction_date", "user")


@admin.register(Disorder)
class DisorderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "name",
        "type",
        "signs_and_symptoms",
        "description",
        "treatment",
        "symptoms",
        "causes",
        "prevention",
    )
    list_filter = ("created", "modified")
    search_fields = ("name",)
