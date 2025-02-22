from __future__ import annotations

import logging
from typing import Any

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

from aura.audit_log.services.log.model import AuditLogEvent
from aura.core.fields import GzippedDictField
from aura.core.utils import sane_repr
from aura.users.services.user.service import user_service

logger = logging.getLogger(__name__)

MAX_ACTOR_LABEL_LENGTH = 64


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


class AuditLogEntry(models.Model):
    actor_label = models.CharField(
        max_length=MAX_ACTOR_LABEL_LENGTH,
        blank=True,
        default="",
    )
    # if the entry was created via a user
    actor = models.ForeignKey(
        "users.User",
        related_name="audit_actors",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # if the entry was created via an api key
    actor_key = models.ForeignKey(
        "authtoken.Token",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    target_object = models.BigIntegerField(null=True)
    target_user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        related_name="audit_targets",
        on_delete=models.SET_NULL,
    )
    event = models.PositiveBigIntegerField()
    ip_address = models.GenericIPAddressField(null=True, unpack_ipv4=True)
    data: models.Field[dict[str, Any] | None, dict[str, Any]] = GzippedDictField()
    datetime = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["datetime"]),
            models.Index(fields=["event", "datetime"]),
        ]

    __repr__ = sane_repr("target_user", "type")

    def __str__(self):
        return f"{self.actor_label} {self.event} {self.datetime}"

    def save(self, *args, **kwargs):
        # trim label to the max length
        self._apply_actor_label()
        self.actor_label = (
            self.actor_label[:MAX_ACTOR_LABEL_LENGTH] if self.actor_label else ""
        )
        super().save(*args, **kwargs)

    def _apply_actor_label(self):
        if not self.actor_label:
            assert self.actor_id or self.actor_key or self.ip_address
            if self.actor_id:
                # Fetch user by RPC service as
                # Audit logs are often created in regions.
                user = user_service.get_user(self.actor_id)
                if user:
                    self.actor_label = user.username
            elif self.actor_key:
                self.actor_label = self.actor_key.key

        # Fallback to IP address if user or actor label not available
        if not self.actor_label:
            self.actor_label = self.ip_address or ""

    def as_event(self) -> AuditLogEvent:
        """
        Serializes a potential audit log database entry as a hybrid cloud event that should be deserialized and
        loaded via `from_event` as faithfully as possible.
        """
        if self.actor_label is not None:
            self.actor_label = self.actor_label[:MAX_ACTOR_LABEL_LENGTH]
        return AuditLogEvent(
            actor_label=self.actor_label,
            date_added=self.datetime or timezone.now(),
            actor_user_id=self.actor_id and self.actor_id,
            target_object_id=self.target_object,
            ip_address=self.ip_address and str(self.ip_address),
            event_id=self.event and int(self.event),
            target_user_id=self.target_user_id,
            data=self.data,
            actor_key_id=self.actor_key_id,
        )

    @classmethod
    def from_event(cls, event: AuditLogEvent) -> AuditLogEntry:
        """
        Deserializes a kafka event object into a control silo database item.  Keep in mind that these event objects
        could have been created from previous code versions -- the events are stored on an async queue for indefinite
        delivery and from possibly older code versions.
        """
        from aura.users.models import User

        if event.actor_label:
            label = event.actor_label[:MAX_ACTOR_LABEL_LENGTH]
        elif event.actor_user_id:
            try:
                label = User.objects.get(id=event.actor_user_id).username
            except User.DoesNotExist:
                label = None
        else:
            label = None
        return AuditLogEntry(
            datetime=event.date_added,
            actor_id=event.actor_user_id,
            target_object=event.target_object_id,
            ip_address=event.ip_address,
            event=event.event_id,
            data=event.data,
            actor_label=label,
            target_user_id=event.target_user_id,
            actor_key_id=event.actor_key_id,
        )

    def get_actor_name(self):
        if self.actor:
            return self.actor.get_display_name()
        if self.actor_key:
            return self.actor_key.key + " (api key)"
        return self.actor_label


class PhysicianReferral(models.Model):
    PRACTICE_SIZE_CHOICES = (
        ("1", "1"),
        ("2-10", "2-10"),
        ("11-50", "11-50"),
        ("51-100", "51-100"),
        ("101-500", "101-500"),
        ("500+", "500+"),
    )
    first_name = models.CharField(max_length=255, verbose_name="First Name")
    last_name = models.CharField(max_length=255, verbose_name="Last Name")
    work_email = models.EmailField(verbose_name="Work Email")
    work_phone_number = models.CharField(
        max_length=20,
        verbose_name="Work Phone Number",
    )  # Use CharField, validate later
    practice_name = models.CharField(max_length=255, verbose_name="Name of Practice")
    state_of_practice = models.CharField(
        max_length=2,
        verbose_name="State of Practice (2-letter code)",
    )  #  Store 2-letter state codes (e.g., "CA", "NY").
    medical_group_aco = models.CharField(
        max_length=255,
        verbose_name="Medical Group / ACO Affiliation",
    )
    practice_size = models.CharField(
        max_length=10,
        choices=PRACTICE_SIZE_CHOICES,
        verbose_name="Practice Size",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Physician Referral"
        verbose_name_plural = "Physician Referrals"

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.practice_name}"
