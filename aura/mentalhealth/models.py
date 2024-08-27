from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition
from model_utils.models import TimeStampedModel
from recurrence.fields import RecurrenceField

from .managers import ChatbotInteractionManager
from .managers import DisorderManager
from .managers import TherapyApproachManager
from .managers import TherapySessionManager


class TherapySession(TimeStampedModel):
    class SessionType(models.TextChoices):
        CHAT = "chat", _("Chat")
        VIDEO = "video", _("Video")
        AUDIO = "audio", _("Audio")

    class SessionStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")
        COMPLETED = "completed", _("Completed")

    class TargetAudienceType(models.TextChoices):
        INDIVIDUAL = "individual", _("Individual")
        COUPLES = "couples", _("Couples")
        TEENS = "teens", _("Teens")
        MEDICATION = "medication", _("Medication")
        VETERANS = "veterans", _("Veterans")

    session_type = models.CharField(
        max_length=5,
        choices=SessionType.choices,
        verbose_name=_("Session Type"),
    )
    status = FSMField(
        default=SessionStatus.PENDING,
        choices=SessionStatus.choices,
        verbose_name=_("Status"),
    )
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(verbose_name=_("Scheduled At"))
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Started At"),
    )
    ended_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Ended At"))
    target_audience = models.CharField(
        max_length=10,
        choices=TargetAudienceType.choices,
        verbose_name=_("Target Audience"),
    )
    recurrences = RecurrenceField()
    therapist = models.ForeignKey(
        "users.Therapist",
        on_delete=models.CASCADE,
        related_name="therapy_sessions",
        verbose_name=_("Therapist"),
    )
    patient = models.ForeignKey(
        "users.Patient",
        on_delete=models.CASCADE,
        related_name="therapy_sessions",
        verbose_name=_("Patient"),
    )

    objects = TherapySessionManager()

    class Meta:
        ordering = ["scheduled_at"]
        verbose_name = _("Therapy Session")
        verbose_name_plural = _("Therapy Sessions")
        constraints = [
            models.CheckConstraint(
                check=models.Q(ended_at__gt=models.F("started_at")),
                name="check_ended_after_started",
            ),
        ]

    def __str__(self):
        return f"{self.therapist} - {self.patient} - {self.scheduled_at}"

    @transition(
        field=status,
        source=SessionStatus.PENDING,
        target=SessionStatus.ACCEPTED,
    )
    def accept(self):
        self.started_at = timezone.now()

    @transition(
        field=status,
        source=[SessionStatus.PENDING, SessionStatus.ACCEPTED],
        target=SessionStatus.CANCELLED,
    )
    def cancel(self):
        pass

    @transition(
        field=status,
        source=SessionStatus.ACCEPTED,
        target=SessionStatus.COMPLETED,
    )
    def complete(self):
        self.ended_at = timezone.now()

    def clean(self):
        if self.ended_at and self.started_at and self.ended_at <= self.started_at:
            raise ValidationError(_("Ended at must be after started at."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class TherapyApproach(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()

    objects = TherapyApproachManager()

    class Meta:
        verbose_name = _("Therapy Approach")
        verbose_name_plural = _("Therapy Approaches")

    def __str__(self):
        return self.name


class ChatbotInteraction(TimeStampedModel):
    message = models.TextField(verbose_name=_("Message"))
    response = models.TextField(verbose_name=_("Response"))
    conversation_log = ArrayField(
        models.JSONField(),
        default=list,
        verbose_name=_("Conversation Log"),
    )
    interaction_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatbot_interactions",
        verbose_name=_("User"),
    )

    objects = ChatbotInteractionManager()

    class Meta:
        ordering = ["-interaction_date"]
        verbose_name = _("Chatbot Interaction")
        verbose_name_plural = _("Chatbot Interactions")
        indexes = [
            models.Index(fields=["user", "-interaction_date"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.interaction_date}"


class Disorder(TimeStampedModel):
    class DisorderType(models.TextChoices):
        MENTAL = "mental", _("Mental")
        PHYSICAL = "physical", _("Physical")
        GENETIC = "genetic", _("Genetic")
        EMOTIONAL = "emotional", _("Emotional")
        BEHAVIORAL = "behavioral", _("Behavioral")
        FUNCTIONAL = "functional", _("Functional")

    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(
        max_length=10,
        choices=DisorderType.choices,
        verbose_name=_("Disorder Type"),
    )
    signs_and_symptoms = models.TextField()
    description = models.TextField()
    treatment = models.TextField()
    symptoms = ArrayField(models.CharField(max_length=255), blank=True)
    causes = ArrayField(models.CharField(max_length=255), blank=True)
    prevention = models.TextField()

    objects = DisorderManager()

    class Meta:
        verbose_name = _("Disorder")
        verbose_name_plural = _("Disorders")
        indexes = [
            models.Index(fields=["name", "type"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_type_display()}"
