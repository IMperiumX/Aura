from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import StatusModel
from model_utils.models import TimeStampedModel
from pgvector.django import VectorField
from sentence_transformers import SentenceTransformer

from aura.assessments.services import RecommendationEngine


class HealthAssessment(StatusModel, TimeStampedModel):
    """A model to represent a health risk assessment"""

    DRAFT = "draft"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    STATUS = (
        (DRAFT, _("Draft")),
        (COMPLETED, _("Completed")),
        (IN_PROGRESS, _("In Progress")),
        (SUBMITTED, _("Submitted")),
    )

    class AssessmentType(models.TextChoices):
        """Choices for the type of health assessment"""

        GENERAL = "general", "General"
        CARDIOVASCULAR = "cardiovascular", "Cardiovascular"
        DIABETES = "diabetes", "Diabetes"
        MENTAL_HEALTH = "mental_health", "Mental Health"
        ANXIETY = "anxiety", "Anxiety"
        DEPRESSION = "depression", "Depression"
        BIPOLAR_DISORDER = "bipolar_disorder", "Bipolar Disorder"
        OCD = "ocd", "OCD"
        PTSD = "ptsd", "PTSD"
        POST_PARTUM_DEPRESSION = "post_partum_depression", "Post-partum Depression"
        PANIC_DISORDER = "panic_disorder", "Panic Disorder"

    class RiskLevel(models.TextChoices):
        """Choices for the risk level of health assessment"""

        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    assessment_type = models.CharField(
        max_length=50,
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
        help_text=_("Recommendations based on the assessment"),
    )
    responses = models.JSONField(
        verbose_name="Responses",
        help_text=_("Responses provided during the assessment"),
    )
    result = models.TextField(
        verbose_name="Result",
        help_text=_("Result of the health assessment"),
    )
    patient = models.ForeignKey(
        "users.Patient",
        on_delete=models.CASCADE,
        related_name="health_assessments",
    )
    embedding = VectorField(
        dimensions=settings.EMBEDDING_MODEL_DIMENSIONS,
        null=True,
    )

    class Meta:
        verbose_name = "Health Assessment"
        verbose_name_plural = "Health Assessments"

    def __str__(self):
        return f"{self.patient} - {self.assessment_type}"

    def get_recommendations(self):
        return RecommendationEngine.get_mental_health_recommendations(self)

    def save(self, *args, **kwargs):
        if not self.embedding:
            model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
            self.embedding = model.encode(self.result).tolist()
        super().save(*args, **kwargs)


class HealthRiskPrediction(TimeStampedModel):
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
    confidence_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Confidence level of the prediction"),
    )
    source = models.CharField(
        max_length=100,
        help_text=_("Source or method of the prediction"),
    )

    assessment = models.ForeignKey(
        "assessments.HealthAssessment",
        on_delete=models.CASCADE,
        related_name="health_risk_predictions",
        verbose_name="Health Assessment",
    )
    patient = models.ForeignKey(
        "users.Patient",
        on_delete=models.CASCADE,
        related_name="health_risk_predictions",
        verbose_name="User",
    )

    class Meta:
        verbose_name = "Health Risk Prediction"
        verbose_name_plural = "Health Risk Predictions"

    def __str__(self):
        return f"{self.patient} - {self.health_issue}"
