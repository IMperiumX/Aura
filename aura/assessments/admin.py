from django.contrib import admin

from .models import Assessment
from .models import Question
from .models import Response
from .models import RiskPrediction


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "status",
        "status_changed",
        "patient",
        "assessment_type",
        "risk_level",
        "recommendations",
        "result",
        "embedding",
    )
    list_filter = ("created", "modified", "status_changed", "patient")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "assessment_type")


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "assessment",
        "question",
        "answer",
        "is_valid",
    )
    list_filter = (
        "created",
        "modified",
        "assessment",
        "question",
        "is_valid",
    )


@admin.register(RiskPrediction)
class RiskPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "assessment",
        "health_issue",
        "preventive_measures",
        "confidence_level",
        "source",
    )
    list_filter = ("created", "modified", "assessment")
