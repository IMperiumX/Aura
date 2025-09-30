"""
Repository interface for Matching-related entity operations.
Defines the contract for matching data persistence and retrieval.
"""

from abc import ABC
from abc import abstractmethod

from aura.users.models import PatientProfile
from aura.users.models import TherapistProfile


class MatchingRepository(ABC):
    """Abstract repository interface for matching operations."""

    @abstractmethod
    def find_patient_profile(self, user_id: int) -> PatientProfile | None:
        """Find patient profile for matching."""

    @abstractmethod
    def find_therapist_profiles_for_matching(
        self,
        specializations: list[str] | None = None,
        location: str | None = None,
        radius: int = 25,
        therapy_types: list[str] | None = None,
        budget_range: str | None = None,
        session_format: list[str] | None = None,
        therapist_gender_preference: str | None = None,
        languages: list[str] | None = None,
    ) -> list[TherapistProfile]:
        """Find therapist profiles matching patient criteria."""

    @abstractmethod
    def calculate_compatibility_score(
        self, patient_profile: PatientProfile, therapist_profile: TherapistProfile
    ) -> float:
        """Calculate compatibility score between patient and therapist."""

    @abstractmethod
    def save_match_feedback(self, patient_id: int, therapist_id: int, feedback_type: str, feedback_data: dict) -> bool:
        """Save match feedback for improving future matches."""

    @abstractmethod
    def get_match_history(self, patient_id: int) -> list[dict]:
        """Get match history for a patient."""

    @abstractmethod
    def update_patient_preferences(self, patient_profile: PatientProfile, preference_updates: dict) -> PatientProfile:
        """Update patient preferences based on feedback."""
