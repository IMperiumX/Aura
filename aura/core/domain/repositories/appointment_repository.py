"""
Repository interface for Appointment entity operations.
Defines the contract for appointment data persistence and retrieval.
"""

from abc import ABC
from abc import abstractmethod
from datetime import datetime

from aura.core.appointments import Appointment
from aura.users.models import User


class AppointmentRepository(ABC):
    """Abstract repository interface for appointment operations."""

    @abstractmethod
    def find_by_id(self, appointment_id: str) -> Appointment | None:
        """Find an appointment by ID."""

    @abstractmethod
    def create_appointment(self, appointment_data: dict) -> Appointment:
        """Create a new appointment."""

    @abstractmethod
    def update_appointment(self, appointment: Appointment) -> Appointment:
        """Update an existing appointment."""

    @abstractmethod
    def delete_appointment(self, appointment_id: str) -> bool:
        """Delete an appointment by ID."""

    @abstractmethod
    def find_by_patient(self, patient: User) -> list[Appointment]:
        """Find all appointments for a patient."""

    @abstractmethod
    def find_by_therapist(self, therapist: User) -> list[Appointment]:
        """Find all appointments for a therapist."""

    @abstractmethod
    def find_by_status(self, status: str) -> list[Appointment]:
        """Find appointments by status."""

    @abstractmethod
    def find_upcoming_appointments(self, user: User | None = None, days_ahead: int = 7) -> list[Appointment]:
        """Find upcoming appointments within specified days."""

    @abstractmethod
    def find_appointments_by_date_range(
        self, start_date: datetime, end_date: datetime, user: User | None = None
    ) -> list[Appointment]:
        """Find appointments within a date range."""

    @abstractmethod
    def find_conflicting_appointments(
        self, therapist: User, session_datetime: datetime, duration: int = 60
    ) -> list[Appointment]:
        """Find appointments that conflict with a given time slot."""

    @abstractmethod
    def count_appointments_by_user(self, user: User, status: str | None = None) -> int:
        """Count appointments for a user, optionally filtered by status."""
