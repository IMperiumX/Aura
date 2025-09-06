"""
Use case for scheduling therapy sessions.
Orchestrates the scheduling process with validation and business rules.
"""

from dataclasses import dataclass
from datetime import datetime

from ...domain.entities.therapy_session import SessionType
from ...domain.entities.therapy_session import TargetAudience
from ...domain.entities.therapy_session import TherapySession
from ...domain.repositories.therapy_session_repository import TherapySessionRepository
from ...domain.services.therapy_session_service import TherapySessionDomainService


@dataclass
class ScheduleTherapySessionRequest:
    """Request data for scheduling a therapy session."""

    therapist_id: int
    patient_id: int
    scheduled_at: datetime
    session_type: SessionType
    target_audience: TargetAudience
    notes: str | None = None


@dataclass
class ScheduleTherapySessionResponse:
    """Response data for scheduling a therapy session."""

    success: bool
    session: TherapySession | None = None
    error_message: str | None = None


class ScheduleTherapySessionUseCase:
    """Use case for scheduling therapy sessions."""

    def __init__(
        self,
        therapy_session_repository: TherapySessionRepository,
        therapy_session_service: TherapySessionDomainService,
    ):
        self._repository = therapy_session_repository
        self._service = therapy_session_service

    def execute(self, request: ScheduleTherapySessionRequest) -> ScheduleTherapySessionResponse:
        """Execute the schedule therapy session use case."""
        try:
            # Validate request
            self._validate_request(request)

            # Use domain service to schedule session
            session = self._service.schedule_session(
                therapist_id=request.therapist_id,
                patient_id=request.patient_id,
                scheduled_at=request.scheduled_at,
                session_type=request.session_type,
                target_audience=request.target_audience.value,
            )

            # Add notes if provided
            if request.notes:
                session.notes = request.notes
                session = self._repository.update(session)

            return ScheduleTherapySessionResponse(
                success=True,
                session=session,
            )

        except ValueError as e:
            return ScheduleTherapySessionResponse(
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return ScheduleTherapySessionResponse(
                success=False,
                error_message=f"An unexpected error occurred: {e!s}",
            )

    def _validate_request(self, request: ScheduleTherapySessionRequest) -> None:
        """Validate the scheduling request."""
        if not request.therapist_id:
            raise ValueError("Therapist ID is required")

        if not request.patient_id:
            raise ValueError("Patient ID is required")

        if not request.scheduled_at:
            raise ValueError("Scheduled time is required")

        if not request.session_type:
            raise ValueError("Session type is required")

        if not request.target_audience:
            raise ValueError("Target audience is required")

        if request.therapist_id == request.patient_id:
            raise ValueError("Therapist and patient cannot be the same person")
