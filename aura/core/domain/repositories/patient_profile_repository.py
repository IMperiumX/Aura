"""
Repository interface for PatientProfile entity operations.
Defines the contract for patient profile data persistence and retrieval.
"""

from abc import ABC
from abc import abstractmethod

from aura.users.models import PatientProfile
from aura.users.models import User


class PatientProfileRepository(ABC):
    """Abstract repository interface for patient profile operations."""

    @abstractmethod
    def find_by_id(self, profile_id: int) -> PatientProfile | None:
        """Find a patient profile by ID."""

    @abstractmethod
    def find_by_user_id(self, user_id: int) -> PatientProfile | None:
        """Find a patient profile by user ID."""

    @abstractmethod
    def find_by_user(self, user: User) -> PatientProfile | None:
        """Find a patient profile by user instance."""

    @abstractmethod
    def create_profile(self, user: User, profile_data: dict) -> PatientProfile:
        """Create a new patient profile."""

    @abstractmethod
    def update_profile(self, profile: PatientProfile) -> PatientProfile:
        """Update an existing patient profile."""

    @abstractmethod
    def delete_profile(self, profile_id: int) -> bool:
        """Delete a patient profile by ID."""

    @abstractmethod
    def find_completed_profiles(self) -> list[PatientProfile]:
        """Find all completed patient profiles."""

    @abstractmethod
    def find_profiles_for_matching(self) -> list[PatientProfile]:
        """Find patient profiles that are enabled for matching."""

    @abstractmethod
    def find_by_location(self, location: str, radius: int = 25) -> list[PatientProfile]:
        """Find patient profiles within a location radius."""

    @abstractmethod
    def find_by_concerns(self, concerns: list[str]) -> list[PatientProfile]:
        """Find patient profiles with specific primary concerns."""
