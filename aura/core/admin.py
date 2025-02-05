from django.contrib import admin

from .models import AuditLogEntry
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "source",
        "topic",
        "rating",
        "content",
        "reviewer",
    )
    list_filter = ("created", "modified", "reviewer")


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "actor_label",
        "actor",
        "actor_key",
        "target_object",
        "target_user",
        "event",
        "ip_address",
        "data",
        "datetime",
    )
    list_filter = ("actor", "actor_key", "target_user", "datetime")
