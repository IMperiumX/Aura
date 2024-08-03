from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel
from recurrence.fields import RecurrenceField


class TherapySession(TimeStampedModel):
    """
    A model to represent a therapy session.
    """

    class SessionType(models.TextChoices):
        """
        Choices for the type of therapy session.
        """

        CHAT = "chat", "Chat"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"

    class SessionStatus(models.TextChoices):
        """
        Choices for the status of a therapy session.
        """

        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    class TargetAudienceType(models.TextChoices):
        """
        Choices for the type of therapy session.
        """

        INDIVIDUAL = "individual", "Individual"
        COUPLES = "couples", "Couples"
        TEENS = "teens", "Teens"
        MEDICATION = "medication", "Medication"
        VETERANS = "veterans", "Veterans"

    session_type = models.CharField(
        max_length=5,
        choices=SessionType.choices,
        verbose_name="Session Type",
    )
    status = models.CharField(
        max_length=10,
        choices=SessionStatus.choices,
        default=SessionStatus.PENDING,
        verbose_name="Status",
    )
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    scheduled_at = models.DateTimeField(
        verbose_name="Scheduled At",
    )
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Started At",
    )
    ended_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Ended At",
    )
    target_audience = models.CharField(
        max_length=10,
        choices=TargetAudienceType.choices,
        verbose_name="Session Type",
    )

    recurrences = RecurrenceField()

    # relations
    therapist = models.ForeignKey(
        "users.Therapist",
        on_delete=models.CASCADE,
        related_name="therapy_sessions_as_therapist",
        verbose_name="Therapist",
    )
    patient = models.ForeignKey(
        "users.Patient",
        on_delete=models.CASCADE,
        related_name="therapy_sessions_as_patient",
        verbose_name="Patient",
    )

    class Meta:
        ordering = ["scheduled_at"]
        verbose_name = "Therapy Session"
        verbose_name_plural = "Therapy Sessions"

    def __str__(self):
        return f"{self.therapist} - {self.patient} - {self.recurrences}"


class TherapyApproach(models.Model):
    """
    A model to represent a therapy approach.
    """

    name = models.CharField(
        max_length=255,
    )
    description = models.TextField()

    class Meta:
        verbose_name = "Therapy Approach"
        verbose_name_plural = "Therapy Approaches"

    def __str__(self):
        return self.name


class ChatbotInteraction(TimeStampedModel):
    """
    A model to represent a chatbot interaction.
    """

    message = models.TextField(
        verbose_name="Message",
    )
    response = models.TextField(
        verbose_name="Response",
    )
    conversation_log = models.TextField()
    interaction_date = models.DateTimeField(null=True, default=timezone.now)
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="chatbot_interactions",
        verbose_name="User",
    )

    class Meta:
        ordering = ["created"]
        verbose_name = "Chatbot Interaction"
        verbose_name_plural = "Chatbot Interactions"

    def __str__(self):
        return f"{self.user}"
