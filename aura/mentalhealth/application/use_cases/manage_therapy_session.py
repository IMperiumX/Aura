"""
Use cases for managing therapy sessions (start, end, cancel, etc.).
"""

from dataclasses import dataclass

from ...domain.entities.therapy_session import TherapySession
from ...domain.repositories.therapy_session_repository import TherapySessionRepository


@dataclass
class ManageSessionRequest:
    """Base request for session management operations."""

    session_id: int
    user_id: int  # For authorization


@dataclass
class StartSessionRequest(ManageSessionRequest):
    """Request to start a therapy session."""


@dataclass
class EndSessionRequest(ManageSessionRequest):
    """Request to end a therapy session."""

    summary: str | None = None
    notes: str | None = None


@dataclass
class CancelSessionRequest(ManageSessionRequest):
    """Request to cancel a therapy session."""

    reason: str | None = None


@dataclass
class SessionManagementResponse:
    """Response for session management operations."""

    success: bool
    session: TherapySession | None = None
    error_message: str | None = None


class StartTherapySessionUseCase:
    """Use case for starting therapy sessions."""

    def __init__(self, therapy_session_repository: TherapySessionRepository):
        self._repository = therapy_session_repository

    def execute(self, request: StartSessionRequest) -> SessionManagementResponse:
        """Execute the start therapy session use case."""
        try:
            # Get the session
            session = self._repository.find_by_id(request.session_id)
            if not session:
                return SessionManagementResponse(
                    success=False,
                    error_message="Session not found",
                )

            # Authorize the operation
            if not self._can_user_start_session(request.user_id, session):
                return SessionManagementResponse(
                    success=False,
                    error_message="User not authorized to start this session",
                )

            # Start the session
            session.start_session()
            updated_session = self._repository.update(session)

            return SessionManagementResponse(
                success=True,
                session=updated_session,
            )

        except ValueError as e:
            return SessionManagementResponse(
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return SessionManagementResponse(
                success=False,
                error_message=f"An unexpected error occurred: {e!s}",
            )

    def _can_user_start_session(self, user_id: int, session: TherapySession) -> bool:
        """Check if user can start the session."""
        return user_id in [session.therapist_id, session.patient_id]


class EndTherapySessionUseCase:
    """Use case for ending therapy sessions."""

    def __init__(self, therapy_session_repository: TherapySessionRepository):
        self._repository = therapy_session_repository

    def execute(self, request: EndSessionRequest) -> SessionManagementResponse:
        """Execute the end therapy session use case."""
        try:
            # Get the session
            session = self._repository.find_by_id(request.session_id)
            if not session:
                return SessionManagementResponse(
                    success=False,
                    error_message="Session not found",
                )

            # Authorize the operation
            if not self._can_user_end_session(request.user_id, session):
                return SessionManagementResponse(
                    success=False,
                    error_message="User not authorized to end this session",
                )

            # End the session
            session.end_session(
                summary=request.summary or "",
                notes=request.notes or "",
            )
            updated_session = self._repository.update(session)

            return SessionManagementResponse(
                success=True,
                session=updated_session,
            )

        except ValueError as e:
            return SessionManagementResponse(
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return SessionManagementResponse(
                success=False,
                error_message=f"An unexpected error occurred: {e!s}",
            )

    def _can_user_end_session(self, user_id: int, session: TherapySession) -> bool:
        """Check if user can end the session."""
        # Typically only therapist can end sessions
        return user_id == session.therapist_id


class CancelTherapySessionUseCase:
    """Use case for canceling therapy sessions."""

    def __init__(self, therapy_session_repository: TherapySessionRepository):
        self._repository = therapy_session_repository

    def execute(self, request: CancelSessionRequest) -> SessionManagementResponse:
        """Execute the cancel therapy session use case."""
        try:
            # Get the session
            session = self._repository.find_by_id(request.session_id)
            if not session:
                return SessionManagementResponse(
                    success=False,
                    error_message="Session not found",
                )

            # Authorize the operation
            if not self._can_user_cancel_session(request.user_id, session):
                return SessionManagementResponse(
                    success=False,
                    error_message="User not authorized to cancel this session",
                )

            # Cancel the session
            session.cancel_session(reason=request.reason)
            updated_session = self._repository.update(session)

            return SessionManagementResponse(
                success=True,
                session=updated_session,
            )

        except ValueError as e:
            return SessionManagementResponse(
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return SessionManagementResponse(
                success=False,
                error_message=f"An unexpected error occurred: {e!s}",
            )

    def _can_user_cancel_session(self, user_id: int, session: TherapySession) -> bool:
        """Check if user can cancel the session."""
        return user_id in [session.therapist_id, session.patient_id]
