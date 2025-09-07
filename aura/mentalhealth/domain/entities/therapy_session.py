"""
Domain entity for Therapy Session.
Contains business logic and rules for therapy sessions.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum

from django.utils import timezone


class SessionType(Enum):
    CHAT = "chat"
    VIDEO = "video"
    AUDIO = "audio"


class SessionStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class TargetAudience(Enum):
    INDIVIDUAL = "individual"
    COUPLES = "couples"
    TEENS = "teens"
    MEDICATION = "medication"
    VETERANS = "veterans"


@dataclass
class TherapySession:
    """Domain entity representing a therapy session."""

    id: int | None = None
    session_type: SessionType = SessionType.CHAT
    status: SessionStatus = SessionStatus.PENDING
    summary: str = ""
    notes: str = ""
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    target_audience: TargetAudience = TargetAudience.INDIVIDUAL
    therapist_id: int | None = None
    patient_id: int | None = None
    created_at: datetime | None = field(default_factory=datetime.now)
    updated_at: datetime | None = field(default_factory=datetime.now)

    def start_session(self) -> None:
        """Start the therapy session."""
        if self.status != SessionStatus.ACCEPTED:
            msg = "Session must be accepted before starting"
            raise ValueError(msg)

        if self.started_at is not None:
            msg = "Session has already been started"
            raise ValueError(msg)

        self.started_at = timezone.now()
        self.status = SessionStatus.COMPLETED
        self.updated_at = timezone.now()

    def end_session(self, summary: str = "", notes: str = "") -> None:
        """End the therapy session."""
        if self.started_at is None:
            msg = "Session must be started before ending"
            raise ValueError(msg)

        if self.ended_at is not None:
            msg = "Session has already been ended"
            raise ValueError(msg)

        self.ended_at = timezone.now()
        self.summary = summary
        self.notes = notes
        self.updated_at = timezone.now()

    def accept_session(self) -> None:
        """Accept the therapy session."""
        if self.status != SessionStatus.PENDING:
            msg = "Only pending sessions can be accepted"
            raise ValueError(msg)

        self.status = SessionStatus.ACCEPTED
        self.updated_at = timezone.now()

    def reject_session(self, reason: str = "") -> None:
        """Reject the therapy session."""
        if self.status not in [SessionStatus.PENDING, SessionStatus.ACCEPTED]:
            msg = "Only pending or accepted sessions can be rejected"
            raise ValueError(msg)

        self.status = SessionStatus.REJECTED
        if reason:
            self.notes = f"Rejection reason: {reason}"
        self.updated_at = timezone.now()

    def cancel_session(self, reason: str = "") -> None:
        """Cancel the therapy session."""
        if self.status == SessionStatus.COMPLETED:
            msg = "Cannot cancel a completed session"
            raise ValueError(msg)

        self.status = SessionStatus.CANCELLED
        if reason:
            self.notes = f"Cancellation reason: {reason}"
        self.updated_at = timezone.now()

    def can_be_started(self) -> bool:
        """Check if session can be started."""
        return (
            self.status == SessionStatus.ACCEPTED
            and self.started_at is None
            and self.scheduled_at is not None
            and self.scheduled_at <= timezone.now()
        )

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.started_at is not None and self.ended_at is None

    def get_duration_minutes(self) -> int | None:
        """Get session duration in minutes."""
        if self.started_at is None or self.ended_at is None:
            return None

        duration = self.ended_at - self.started_at
        return int(duration.total_seconds() / 60)

    def validate(self) -> None:
        """Validate the therapy session entity."""
        errors = []

        if self.scheduled_at is None:
            errors.append("Scheduled time is required")

        if self.therapist_id is None:
            errors.append("Therapist is required")

        if self.patient_id is None:
            errors.append("Patient is required")

        if self.started_at and self.ended_at and self.ended_at <= self.started_at:
            errors.append("End time must be after start time")

        if errors:
            msg = f"Validation failed: {', '.join(errors)}"
            raise ValueError(msg)
