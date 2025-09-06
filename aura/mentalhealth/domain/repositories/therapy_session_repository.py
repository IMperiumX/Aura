"""
Repository interface for TherapySession entity.
Defines the contract for data persistence operations.
"""

from abc import ABC
from abc import abstractmethod
from datetime import datetime

from ..entities.therapy_session import SessionStatus
from ..entities.therapy_session import TherapySession


class TherapySessionRepository(ABC):
    """Abstract repository interface for therapy sessions."""

    @abstractmethod
    def save(self, therapy_session: TherapySession) -> TherapySession:
        """Save a therapy session."""

    @abstractmethod
    def find_by_id(self, session_id: int) -> TherapySession | None:
        """Find a therapy session by ID."""

    @abstractmethod
    def find_by_therapist_id(self, therapist_id: int) -> list[TherapySession]:
        """Find all therapy sessions for a therapist."""

    @abstractmethod
    def find_by_patient_id(self, patient_id: int) -> list[TherapySession]:
        """Find all therapy sessions for a patient."""

    @abstractmethod
    def find_by_status(self, status: SessionStatus) -> list[TherapySession]:
        """Find therapy sessions by status."""

    @abstractmethod
    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> list[TherapySession]:
        """Find therapy sessions within a date range."""

    @abstractmethod
    def find_upcoming_sessions(
        self,
        therapist_id: int | None = None,
        patient_id: int | None = None,
    ) -> list[TherapySession]:
        """Find upcoming therapy sessions."""

    @abstractmethod
    def find_active_sessions(self) -> list[TherapySession]:
        """Find currently active therapy sessions."""

    @abstractmethod
    def update(self, therapy_session: TherapySession) -> TherapySession:
        """Update a therapy session."""

    @abstractmethod
    def delete(self, session_id: int) -> bool:
        """Delete a therapy session."""

    @abstractmethod
    def count_by_therapist(self, therapist_id: int, status: SessionStatus | None = None) -> int:
        """Count sessions by therapist and optionally by status."""

    @abstractmethod
    def count_by_patient(self, patient_id: int, status: SessionStatus | None = None) -> int:
        """Count sessions by patient and optionally by status."""
