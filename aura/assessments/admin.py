from django.contrib import admin

from .models import HealthAssessment
from .models import HealthRiskPrediction


@admin.register(HealthAssessment)
class HealthAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "status",
        "status_changed",
        "assessment_type",
        "risk_level",
        "recommendations",
        "responses",
        "result",
        "patient",
    )
    list_filter = ("created", "modified", "status_changed", "patient")


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
    list_filter = ("created", "modified", "assessment", "patient")
