from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_lifecycle import AFTER_UPDATE
from django_lifecycle import LifecycleModel
from django_lifecycle import hook
from model_utils.models import StatusModel
from model_utils.models import TimeStampedModel
from pgvector.django import HnswIndex
from pgvector.django import VectorField

from aura.core.services import RecommendationEngine


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

    # relations
    patient = models.ForeignKey(
        "users.Patient",
        on_delete=models.CASCADE,
        related_name="health_assessments",
    )
    embedding = VectorField(
        dimensions=settings.EMBEDDING_MODEL_DIMENSIONS,
        null=True,
    )
    questions = models.ManyToManyField(
        "assessments.Question",
        related_name="health_assessments",
        verbose_name="Questions",
        help_text=_("Questions in the health assessment"),
        through="assessments.HealthAssessmentQuestion",
    )

    class Meta:
        verbose_name = "Health Assessment"
        verbose_name_plural = "Health Assessments"
        indexes = [
            HnswIndex(
                name="ha_27072024_embedding_index",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.patient} - {self.assessment_type}"

    def get_therapist_recommendations(self):
        return RecommendationEngine().get_therapist_recommendations(self)


class Question(LifecycleModel):
    """A model to represent a question in a health assessment"""

    text = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.text

    @hook(AFTER_UPDATE, when="text", has_changed=True)
    def update_assessment(self):
        # Set the assessment to null
        self.assessment = None
        self.save()


class HealthAssessmentQuestion(models.Model):
    """A model to represent the relationship between a health assessment and a question"""

    question = models.ForeignKey(
        "assessments.Question",
        on_delete=models.CASCADE,
        related_name="health_assessment_questions",
        verbose_name="Question",
    )
    health_assessment = models.ForeignKey(
        "assessments.HealthAssessment",
        on_delete=models.SET_NULL,
        related_name="health_assessment_questions",
        verbose_name="Health Assessment",
        null=True,
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order of the question in the assessment."),
    )

    class Meta:
        verbose_name = "Health Assessment Question"
        verbose_name_plural = "Health Assessment Questions"

    def __str__(self):
        return f"# {self.order}: {self.health_assessment} - {self.question}"


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
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(100))],
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
