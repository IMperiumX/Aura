from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.utils.html import format_html

from .models import Assessment
from .models import PatientAssessment
from .models import Question
from .models import Response
from .models import RiskPrediction


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 1
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 4, "cols": 80})},
    }


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "status_changed",
        "assessment_type",
        "risk_level",
        "created",
        "modified",
    )
    list_filter = ("created", "modified", "status_changed")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "text",
        "allow_multiple",
        "assessment",
        "created",
        "modified",
    )
    list_filter = ("created", "modified", "allow_multiple", "assessment")
    inlines = [ResponseInline]


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question", "created", "modified")
    list_filter = ("created", "modified", "question")


@admin.register(PatientAssessment)
class PatientAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "assessment",
        "result",
        "recommendations",
        "embedding",
        "created",
        "modified",
    )
    list_filter = ("created", "modified", "patient", "assessment")
    readonly_fields = ("embedding",)


@admin.register(RiskPrediction)
class RiskPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "confidence_level_c",
        "assessment",
        "health_issue",
        "preventive_measures",
        "source",
        "created",
        "modified",
    )
    list_filter = ("created", "modified", "assessment")

    def confidence_level_c(self, obj):
        color = "#FF0000"  # red
        if obj.confidence_level > 8:  # noqa: PLR2004
            color = "#FFFF00"  # green
        if obj.confidence_level > 6:  # noqa: PLR2004
            color = "#00FF00"  # yellow
        if obj.confidence_level > 4:  # noqa: PLR2004
            color = "#00FFFF"  # cyan
        return format_html('<b style="color:{};">{}</b>', color, obj.confidence_level)
