from django.contrib import admin

from .models import AuditLogEntry
from .models import PhysicianReferral
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


@admin.register(PhysicianReferral)
class PhysicianReferralAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "work_email",
        "work_phone_number",
        "practice_name",
        "state_of_practice",
        "medical_group_aco",
        "practice_size",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    date_hierarchy = "created_at"
