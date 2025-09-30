"""
Django ORM implementation of PatientProfileRepository.
Implements patient profile data operations using Django models.
"""

from django.db import transaction

from aura.core.domain.repositories.patient_profile_repository import PatientProfileRepository
from aura.users.models import PatientProfile
from aura.users.models import User


class DjangoPatientProfileRepository(PatientProfileRepository):
    """Django ORM implementation of PatientProfileRepository."""

    def find_by_id(self, profile_id: int) -> PatientProfile | None:
        """Find a patient profile by ID."""
        try:
            return PatientProfile.objects.select_related("user").get(id=profile_id)
        except PatientProfile.DoesNotExist:
            return None

    def find_by_user_id(self, user_id: int) -> PatientProfile | None:
        """Find a patient profile by user ID."""
        try:
            return PatientProfile.objects.select_related("user").get(user_id=user_id)
        except PatientProfile.DoesNotExist:
            return None

    def find_by_user(self, user: User) -> PatientProfile | None:
        """Find a patient profile by user instance."""
        try:
            return PatientProfile.objects.select_related("user").get(user=user)
        except PatientProfile.DoesNotExist:
            return None

    @transaction.atomic
    def create_profile(self, user: User, profile_data: dict) -> PatientProfile:
        """Create a new patient profile."""
        profile = PatientProfile.objects.create(user=user, **profile_data)
        return profile

    def update_profile(self, profile: PatientProfile) -> PatientProfile:
        """Update an existing patient profile."""
        profile.save()
        return profile

    @transaction.atomic
    def delete_profile(self, profile_id: int) -> bool:
        """Delete a patient profile by ID."""
        try:
            profile = PatientProfile.objects.get(id=profile_id)
            profile.delete()
            return True
        except PatientProfile.DoesNotExist:
            return False

    def find_completed_profiles(self) -> list[PatientProfile]:
        """Find all completed patient profiles."""
        return list(PatientProfile.objects.filter(profile_completed=True).select_related("user"))

    def find_profiles_for_matching(self) -> list[PatientProfile]:
        """Find patient profiles that are enabled for matching."""
        return list(PatientProfile.objects.filter(profile_completed=True, matching_enabled=True).select_related("user"))

    def find_by_location(self, location: str, radius: int = 25) -> list[PatientProfile]:
        """Find patient profiles within a location radius."""
        # Note: This would need proper geographic search implementation
        # For now, using simple string matching
        return list(PatientProfile.objects.filter(location__icontains=location).select_related("user"))

    def find_by_concerns(self, concerns: list[str]) -> list[PatientProfile]:
        """Find patient profiles with specific primary concerns."""
        return list(PatientProfile.objects.filter(primary_concerns__overlap=concerns).select_related("user"))
