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


class Assessment(StatusModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_PROGRESS = "in_progress", _("In Progress")
        SUBMITTED = "submitted", _("Submitted")
        COMPLETED = "completed", _("Completed")

    STATUS = Status.choices

    class Type(models.TextChoices):
        GENERAL = "general", _("General")
        CARDIOVASCULAR = "cardiovascular", _("Cardiovascular")
        DIABETES = "diabetes", _("Diabetes")
        MENTAL_HEALTH = "mental_health", _("Mental Health")
        ANXIETY = "anxiety", _("Anxiety")
        DEPRESSION = "depression", _("Depression")
        BIPOLAR_DISORDER = "bipolar_disorder", _("Bipolar Disorder")
        OCD = "ocd", _("OCD")
        PTSD = "ptsd", _("PTSD")
        POST_PARTUM_DEPRESSION = "post_partum_depression", _("Post-partum Depression")
        PANIC_DISORDER = "panic_disorder", _("Panic Disorder")

    class RiskLevel(models.TextChoices):
        LOW = "low", _("Low")
        MODERATE = "moderate", _("Moderate")
        HIGH = "high", _("High")

    assessment_type = models.CharField(
        max_length=50,
        choices=Type.choices,
        verbose_name=_("Assessment Type"),
    )
    risk_level = models.CharField(
        max_length=8,
        choices=RiskLevel.choices,
        verbose_name=_("Risk Level"),
        blank=True,
    )

    def __str__(self):
        return f"{self.risk_level} - {self.get_assessment_type_display()} - {self.get_status_display()}"


class Question(TimeStampedModel):
    text = models.CharField(max_length=255, unique=True)
    allow_multiple = models.BooleanField(default=False)

    assessment = models.ForeignKey(
        "assessments.Assessment",
        on_delete=models.CASCADE,
        related_name="questions",
    )

    def __str__(self):
        return f"{self.text}, multiple: {self.allow_multiple}"


class Response(TimeStampedModel):
    text = models.TextField()

    question = models.ForeignKey(
        "assessments.Question",
        on_delete=models.CASCADE,
        related_name="responses",
    )

    def __str__(self):
        return f"{self.text}"


class PatientAssessment(TimeStampedModel, LifecycleModel):
    patient = models.ForeignKey(
        "users.Patient",
        on_delete=models.CASCADE,
        related_name="patient_assessments",
    )
    assessment = models.ForeignKey(
        "assessments.Assessment",
        on_delete=models.CASCADE,
        related_name="patient_assessments",
    )

    result = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    embedding = VectorField(
        dimensions=settings.EMBEDDING_MODEL_DIMENSIONS,
        null=True,
    )

    class Meta:
        indexes = [
            HnswIndex(
                name="pa_embedding_index",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(fields=["created"]),
            models.Index(fields=["modified"]),
        ]

    def __str__(self):
        return f"{self.patient} - {self.assessment}"

    @hook(AFTER_UPDATE, when="assessment__status", has_changed=True)
    def update_patient_risk_level(self):
        self.patient.update_risk_level()

    @hook(AFTER_UPDATE, when="assessment__status", has_changed=True)
    def update_patient_recommendations(self):
        self.patient.update_recommendations()

    @hook(AFTER_UPDATE, when="assessment__status", has_changed=True)
    def update_patient_result(self):
        self.patient.update_result()

    @hook(AFTER_UPDATE, when="assessment__status", has_changed=True)
    def update_patient_embedding(self):
        self.patient.update_embedding()

    @hook(AFTER_UPDATE, when="assessment__status", has_changed=True)
    def update_patient_risk_predictions(self):
        self.patient.update_risk_predictions()


class RiskPrediction(TimeStampedModel):
    assessment = models.ForeignKey(
        "assessments.PatientAssessment",
        on_delete=models.CASCADE,
        related_name="risk_predictions",
        verbose_name=_("Patient Assessment"),
    )
    health_issue = models.CharField(max_length=255)
    preventive_measures = models.TextField()
    confidence_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    source = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.assessment} - {self.health_issue}"
