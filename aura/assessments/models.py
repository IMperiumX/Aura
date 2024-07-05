from django.db import models


class HealthAssessment(models.Model):
    """
    A model to represent a health risk assessment
    """

    class AssessmentType(models.TextChoices):
        """
        Choices for the type of health assessment
        """

        GENERAL = "general", "General"
        CARDIOVASCULAR = "cardiovascular", "Cardiovascular"
        DIABETES = "diabetes", "Diabetes"
        MENTAL_HEALTH = "mental_health", "Mental Health"

    class RiskLevel(models.TextChoices):
        """
        Choices for the risk level of health assessment
        """

        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    assessment_type = models.CharField(
        max_length=15,
        choices=AssessmentType.choices,
        verbose_name="Assessment Type",
    )
    risk_level = models.CharField(
        max_length=8,
        choices=RiskLevel.choices,
        verbose_name="Risk Level",
    )
    recommendations = models.TextField()
    responses = models.JSONField(
        verbose_name="Responses",
    )
    result = models.TextField(
        verbose_name="Result",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    patient = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="health_assessments",
        verbose_name="User",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Health Assessment"
        verbose_name_plural = "Health Assessments"

    def __str__(self):
        return f"{self.user} - {self.assessment_type} - {self.created_at}"


class HealthRiskPrediction(models.Model):
    """
    A model to represent potential health risks and preventive measures
    """

    health_issue = models.CharField(
        max_length=255,
        verbose_name="Health Issue",
    )
    preventive_measures = models.TextField(
        verbose_name="Preventive Measures",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    assessment = models.ForeignKey(
        "assesments.HealthAssessment",
        on_delete=models.CASCADE,
        related_name="health_risk_predictions",
        verbose_name="Health Assessment",
    )
    patient = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="health_risk_predictions",
        verbose_name="User",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Health Risk Prediction"
        verbose_name_plural = "Health Risk Predictions"

    def __str__(self):
        return f"{self.user} - {self.health_issue} - {self.created_at}"
