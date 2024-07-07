from django.db import models
from django.utils.translation import gettext_lazy as _


class HealthAssessment(models.Model):
    """A model to represent a health risk assessment"""

    class AssessmentType(models.TextChoices):
        """Choices for the type of health assessment"""

        GENERAL = "general", "General"
        CARDIOVASCULAR = "cardiovascular", "Cardiovascular"
        DIABETES = "diabetes", "Diabetes"
        MENTAL_HEALTH = "mental_health", "Mental Health"

    class RiskLevel(models.TextChoices):
        """Choices for the risk level of health assessment"""

        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    assessment_type = models.CharField(
        max_length=15,
        choices=AssessmentType.choices,
        verbose_name="Assessment Type",
        help_text=_("Type of health assessment conducted"),
    )
    risk_level = models.CharField(
        max_length=8,
        choices=RiskLevel.choices,
        verbose_name="Risk Level",
        help_text=_("Level of risk identified in the assessment"),
    )
    recommendations = models.TextField(
        help_text=_("Recommendations based on the assessment"), )
    responses = models.JSONField(
        verbose_name="Responses",
        help_text=_("Responses provided during the assessment"),
    )
    result = models.TextField(
        verbose_name="Result",
        help_text=_("Result of the health assessment"),
    )
    created_at = models.DateTimeField(auto_now_add=True, )

    patient = models.ForeignKey(
        "users.PatientProfile",
        on_delete=models.CASCADE,
        related_name="health_assessments",
    )

    class Meta:
        """ """

        ordering = ["created_at"]
        verbose_name = "Health Assessment"
        verbose_name_plural = "Health Assessments"

    def __str__(self):
        return f"{self.patient} - {self.assessment_type} - {self.created_at}"


class HealthRiskPrediction(models.Model):
    """A model to represent potential health risks and preventive measures"""

    health_issue = models.CharField(
        max_length=255,
        verbose_name="Health Issue",
        help_text=_("Specific health issue identified"),
    )
    preventive_measures = models.TextField(
        verbose_name="Preventive Measures",
        help_text=_("Measures to prevent the identified health issue"),
    )
    created_at = models.DateTimeField(auto_now_add=True, )

    assessment = models.ForeignKey(
        "assessments.HealthAssessment",
        on_delete=models.CASCADE,
        related_name="health_risk_predictions",
        verbose_name="Health Assessment",
    )
    patient = models.ForeignKey(
        "users.PatientProfile",
        on_delete=models.CASCADE,
        related_name="health_risk_predictions",
        verbose_name="User",
    )

    class Meta:
        """ """

        ordering = ["created_at"]
        verbose_name = "Health Risk Prediction"
        verbose_name_plural = "Health Risk Predictions"

    def __str__(self):
        return f"{self.patient} - {self.health_issue} - {self.created_at}"
