from django.contrib import admin
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import ngettext

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthAssessmentQuestion
from aura.assessments.models import HealthRiskPrediction
from aura.assessments.models import Question


class QuestionInline(admin.StackedInline):
    model = HealthAssessmentQuestion
    extra = 0
    classes = ["collapse"]

    def has_add_permission(self, request, obj):
        return not self.model.objects.filter(
            health_assessment__status=HealthAssessment.COMPLETED,
        )

    def has_change_permission(self, request, obj):
        return not request.user.has_perm("assessments.change_question")

    def has_delete_permission(self, request, obj):
        if obj and hasattr(obj, "health_assessment"):
            if obj.health_assessment.status == HealthAssessment.COMPLETED:
                return False
        if request.user.has_perm("assessments.delete_question"):
            return True
        return True


@admin.register(Question)
class HealthAssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "text",
    )
    search_fields = [
        "text",
    ]


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
        "embedding",
        "result",
        "recommendations",
        "responses",
    ]
    actions = [
        "mark_as_completed",
    ]
    exclude = ["questions"]
    show_facets = admin.ShowFacets.ALLOW
    inlines = [
        QuestionInline,
    ]

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
