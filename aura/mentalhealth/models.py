from django.db import models


class TherapySession(models.Model):
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

    therapist = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="therapy_sessions_as_therapist",
        verbose_name="Therapist",
    )

    patient = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="therapy_sessions_as_patient",
        verbose_name="Patient",
    )

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

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    class Meta:
        ordering = ["scheduled_at"]
        verbose_name = "Therapy Session"
        verbose_name_plural = "Therapy Sessions"

    def __str__(self):
        return f"{self.therapist} - {self.patient} - {self.scheduled_at}"


class ChatbotInteraction(models.Model):
    """
    A model to represent a chatbot interaction.
    """

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="chatbot_interactions",
        verbose_name="User",
    )

    message = models.TextField(
        verbose_name="Message",
    )

    response = models.TextField(
        verbose_name="Response",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Chatbot Interaction"
        verbose_name_plural = "Chatbot Interactions"

    def __str__(self):
        return f"{self.user} - {self.created_at}"
