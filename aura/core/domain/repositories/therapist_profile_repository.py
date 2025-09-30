"""
Repository interface for TherapistProfile entity operations.
Defines the contract for therapist profile data persistence and retrieval.
"""

from abc import ABC
from abc import abstractmethod

from aura.users.models import TherapistProfile
from aura.users.models import User


class TherapistProfileRepository(ABC):
    """Abstract repository interface for therapist profile operations."""

    @abstractmethod
    def find_by_id(self, profile_id: int) -> TherapistProfile | None:
        """Find a therapist profile by ID."""

    @abstractmethod
    def find_by_user_id(self, user_id: int) -> TherapistProfile | None:
        """Find a therapist profile by user ID."""

    @abstractmethod
    def find_by_user(self, user: User) -> TherapistProfile | None:
        """Find a therapist profile by user instance."""

    @abstractmethod
    def create_profile(self, user: User, profile_data: dict) -> TherapistProfile:
        """Create a new therapist profile."""

    @abstractmethod
    def update_profile(self, profile: TherapistProfile) -> TherapistProfile:
        """Update an existing therapist profile."""

    @abstractmethod
    def delete_profile(self, profile_id: int) -> bool:
        """Delete a therapist profile by ID."""

    @abstractmethod
    def find_verified_profiles(self) -> list[TherapistProfile]:
        """Find all verified therapist profiles."""

    @abstractmethod
    def find_available_for_matching(self) -> list[TherapistProfile]:
        """Find therapist profiles available for matching."""

    @abstractmethod
    def find_by_specializations(self, specializations: list[str]) -> list[TherapistProfile]:
        """Find therapist profiles by specializations."""

    @abstractmethod
    def find_by_location(self, location: str, radius: int = 25) -> list[TherapistProfile]:
        """Find therapist profiles within a location radius."""

    @abstractmethod
    def find_by_approaches(self, approaches: list[str]) -> list[TherapistProfile]:
        """Find therapist profiles by therapeutic approaches."""

    @abstractmethod
    def find_by_license_state(self, state: str) -> list[TherapistProfile]:
        """Find therapist profiles licensed in a specific state."""
