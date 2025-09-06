"""
Domain service for therapy session business logic.
Contains complex business rules and operations.
"""

from datetime import datetime
from datetime import timedelta

from aura.mentalhealth.domain.entities.therapy_session import SessionStatus
from aura.mentalhealth.domain.entities.therapy_session import SessionType
from aura.mentalhealth.domain.entities.therapy_session import TherapySession
from aura.mentalhealth.domain.repositories.therapy_session_repository import (
    TherapySessionRepository,
)


class TherapySessionDomainService:
    """Domain service for therapy session business logic."""

    def __init__(self, therapy_session_repository: TherapySessionRepository):
        self._repository = therapy_session_repository

    def schedule_session(
        self,
        therapist_id: int,
        patient_id: int,
        scheduled_at: datetime,
        session_type: SessionType,
        target_audience: str,
    ) -> TherapySession:
        """Schedule a new therapy session with business rules validation."""

        # Validate scheduling rules
        self._validate_scheduling_rules(therapist_id, patient_id, scheduled_at)

        # Create session
        session = TherapySession(
            therapist_id=therapist_id,
            patient_id=patient_id,
            scheduled_at=scheduled_at,
            session_type=session_type,
            target_audience=target_audience,
            status=SessionStatus.PENDING,
        )

        session.validate()
        return self._repository.save(session)

    def can_schedule_session(
        self,
        therapist_id: int,
        patient_id: int,
        scheduled_at: datetime,
    ) -> bool:
        """Check if a session can be scheduled."""
        try:
            self._validate_scheduling_rules(therapist_id, patient_id, scheduled_at)
            return True
        except ValueError:
            return False

    def _validate_scheduling_rules(
        self,
        therapist_id: int,
        patient_id: int,
        scheduled_at: datetime,
    ) -> None:
        """Validate business rules for scheduling."""

        # Rule 1: Cannot schedule in the past
        if scheduled_at <= datetime.now():
            raise ValueError("Cannot schedule sessions in the past")

        # Rule 2: Must be scheduled at least 1 hour in advance
        if scheduled_at <= datetime.now() + timedelta(hours=1):
            raise ValueError("Sessions must be scheduled at least 1 hour in advance")

        # Rule 3: Check for therapist conflicts
        if self._has_therapist_conflict(therapist_id, scheduled_at):
            raise ValueError("Therapist has a conflicting session at this time")

        # Rule 4: Check for patient conflicts
        if self._has_patient_conflict(patient_id, scheduled_at):
            raise ValueError("Patient has a conflicting session at this time")

        # Rule 5: Therapist should not have more than 8 sessions per day
        if self._therapist_daily_session_count(therapist_id, scheduled_at.date()) >= 8:
            raise ValueError("Therapist has reached maximum daily session limit")

    def _has_therapist_conflict(self, therapist_id: int, scheduled_at: datetime) -> bool:
        """Check if therapist has a conflicting session."""
        window_start = scheduled_at - timedelta(minutes=30)
        window_end = scheduled_at + timedelta(minutes=90)  # Assume 1 hour session + 30 min buffer

        conflicting_sessions = self._repository.find_by_date_range(window_start, window_end)
        return any(
            session.therapist_id == therapist_id
            and session.status in [SessionStatus.ACCEPTED, SessionStatus.PENDING]
            for session in conflicting_sessions
        )

    def _has_patient_conflict(self, patient_id: int, scheduled_at: datetime) -> bool:
        """Check if patient has a conflicting session."""
        window_start = scheduled_at - timedelta(minutes=30)
        window_end = scheduled_at + timedelta(minutes=90)

        conflicting_sessions = self._repository.find_by_date_range(window_start, window_end)
        return any(
            session.patient_id == patient_id
            and session.status in [SessionStatus.ACCEPTED, SessionStatus.PENDING]
            for session in conflicting_sessions
        )

    def _therapist_daily_session_count(self, therapist_id: int, date) -> int:
        """Count therapist's sessions for a given day."""
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())

        daily_sessions = self._repository.find_by_date_range(start_of_day, end_of_day)
        return len(
            [
                session
                for session in daily_sessions
                if session.therapist_id == therapist_id
                and session.status
                in [SessionStatus.ACCEPTED, SessionStatus.PENDING, SessionStatus.COMPLETED]
            ],
        )

    def reschedule_session(self, session_id: int, new_scheduled_at: datetime) -> TherapySession:
        """Reschedule an existing session."""
        session = self._repository.find_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        if session.status not in [SessionStatus.PENDING, SessionStatus.ACCEPTED]:
            raise ValueError("Only pending or accepted sessions can be rescheduled")

        # Validate new time
        self._validate_scheduling_rules(session.therapist_id, session.patient_id, new_scheduled_at)

        # Update session
        session.scheduled_at = new_scheduled_at
        session.updated_at = datetime.now()

        return self._repository.update(session)

    def get_therapist_availability(self, therapist_id: int, date) -> list[datetime]:
        """Get available time slots for a therapist on a given date."""
        start_of_day = datetime.combine(date, datetime.min.time().replace(hour=9))  # 9 AM
        end_of_day = datetime.combine(date, datetime.max.time().replace(hour=18))  # 6 PM

        # Get existing sessions
        existing_sessions = self._repository.find_by_date_range(start_of_day, end_of_day)
        therapist_sessions = [
            session
            for session in existing_sessions
            if session.therapist_id == therapist_id
            and session.status in [SessionStatus.ACCEPTED, SessionStatus.PENDING]
        ]

        # Generate available slots (hourly slots)
        available_slots = []
        current_time = start_of_day

        while current_time < end_of_day:
            # Check if slot conflicts with existing sessions
            has_conflict = any(
                abs((session.scheduled_at - current_time).total_seconds()) < 3600  # 1 hour buffer
                for session in therapist_sessions
            )

            if not has_conflict:
                available_slots.append(current_time)

            current_time += timedelta(hours=1)

        return available_slots

    def calculate_session_statistics(
        self,
        therapist_id: int | None = None,
        patient_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Calculate session statistics."""

        # Get sessions based on filters
        if therapist_id:
            sessions = self._repository.find_by_therapist_id(therapist_id)
        elif patient_id:
            sessions = self._repository.find_by_patient_id(patient_id)
        else:
            sessions = self._repository.find_by_date_range(
                start_date or datetime.now() - timedelta(days=30),
                end_date or datetime.now(),
            )

        # Filter by date range if specified
        if start_date or end_date:
            sessions = [
                session
                for session in sessions
                if (not start_date or session.scheduled_at >= start_date)
                and (not end_date or session.scheduled_at <= end_date)
            ]

        # Calculate statistics
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == SessionStatus.COMPLETED])
        cancelled_sessions = len([s for s in sessions if s.status == SessionStatus.CANCELLED])
        pending_sessions = len([s for s in sessions if s.status == SessionStatus.PENDING])

        # Calculate average duration for completed sessions
        completed_with_duration = [s for s in sessions if s.get_duration_minutes()]
        avg_duration = (
            sum(s.get_duration_minutes() for s in completed_with_duration)
            / len(completed_with_duration)
            if completed_with_duration
            else 0
        )

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "cancelled_sessions": cancelled_sessions,
            "pending_sessions": pending_sessions,
            "completion_rate": completed_sessions / total_sessions if total_sessions > 0 else 0,
            "cancellation_rate": cancelled_sessions / total_sessions if total_sessions > 0 else 0,
            "average_duration_minutes": round(avg_duration, 2),
        }
