import logging

from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

logger = logging.getLogger(__name__)


class Review(TimeStampedModel):
    """A model to represent a review."""

    class ReviewSource(models.TextChoices):
        """Choices for the source of the review."""

        GOOGLE_PLAY_STORE = "gps", _("Google Play Store")
        APPLE_APP_STORE = "aas", _("Apple App Store")
        WEB = "web", _("Web")
        EMAIL = "email", _("Email")

    class ReviewTopic(models.TextChoices):
        """Choices for the topic of the review."""

        THERAPY = "therapy", _("Therapy")
        PSYCHIATRY = "psychiatry", _("Psychiatry")
        COACHING = "coaching", _("Coaching")
        MENTAL_HEALTH = "mental_health", _("Mental Health")
        WELLNESS = "wellness", _("Wellness")

    source = models.CharField(
        max_length=100,
        choices=ReviewSource.choices,
    )
    topic = models.CharField(
        max_length=100,
        choices=ReviewTopic.choices,
    )
    rating = models.PositiveIntegerField()
    content = models.TextField()

    reviewer = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    def __str__(self):
        return f"{self.reviewer} - {self.rating}"
