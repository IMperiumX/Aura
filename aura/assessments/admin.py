from django.contrib import admin, messages
from django.db.models import Q
from django.utils.translation import ngettext

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction


@admin.register(HealthAssessment)
class HealthAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "status",
        "risk_level",
        "assessment_type",
        "recommendations",
        "result",
        "created",
        "modified",
        "status_changed",
    )
    list_filter = [
        "created",
        "modified",
        "status_changed",
    ]
    readonly_fields = [
        "patient",
    ]
    actions = [
        "mark_as_completed",
    ]
    show_facets = admin.ShowFacets.ALLOW

    @admin.display(description="Mark selected assessments as completed")
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(~Q(status=HealthAssessment.COMPLETED)).update(
            status=HealthAssessment.COMPLETED,
        )
        self.message_user(
            request,
            ngettext(
                "%s assessment was marked as completed.",
                "%s assessments were marked as completed.",
                updated,
            ),
            messages.SUCCESS if updated else messages.WARNING,
        )


@admin.register(HealthRiskPrediction)
class HealthRiskPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "health_issue",
        "preventive_measures",
        "confidence_level",
        "source",
        "assessment",
        "patient",
    )
    list_filter = (
        "created",
        "modified",
    )
    readonly_fields = [
        "patient",
    ]

    list_select_related = [
        "assessment",
    ]
