"""
Django ORM implementation of TherapistProfileRepository.
Implements therapist profile data operations using Django models.
"""

from django.db import transaction

from aura.core.domain.repositories.therapist_profile_repository import TherapistProfileRepository
from aura.users.models import TherapistProfile
from aura.users.models import User


class DjangoTherapistProfileRepository(TherapistProfileRepository):
    """Django ORM implementation of TherapistProfileRepository."""

    def find_by_id(self, profile_id: int) -> TherapistProfile | None:
        """Find a therapist profile by ID."""
        try:
            return TherapistProfile.objects.select_related("user").get(id=profile_id)
        except TherapistProfile.DoesNotExist:
            return None

    def find_by_user_id(self, user_id: int) -> TherapistProfile | None:
        """Find a therapist profile by user ID."""
        try:
            return TherapistProfile.objects.select_related("user").get(user_id=user_id)
        except TherapistProfile.DoesNotExist:
            return None

    def find_by_user(self, user: User) -> TherapistProfile | None:
        """Find a therapist profile by user instance."""
        try:
            return TherapistProfile.objects.select_related("user").get(user=user)
        except TherapistProfile.DoesNotExist:
            return None

    @transaction.atomic
    def create_profile(self, user: User, profile_data: dict) -> TherapistProfile:
        """Create a new therapist profile."""
        profile = TherapistProfile.objects.create(user=user, **profile_data)
        return profile

    def update_profile(self, profile: TherapistProfile) -> TherapistProfile:
        """Update an existing therapist profile."""
        profile.save()
        return profile

    @transaction.atomic
    def delete_profile(self, profile_id: int) -> bool:
        """Delete a therapist profile by ID."""
        try:
            profile = TherapistProfile.objects.get(id=profile_id)
            profile.delete()
            return True
        except TherapistProfile.DoesNotExist:
            return False

    def find_verified_profiles(self) -> list[TherapistProfile]:
        """Find all verified therapist profiles."""
        return list(TherapistProfile.objects.filter(verification_status="verified").select_related("user"))

    def find_available_for_matching(self) -> list[TherapistProfile]:
        """Find therapist profiles available for matching."""
        return list(
            TherapistProfile.objects.filter(
                profile_completed=True, available_for_matching=True, verification_status="verified"
            ).select_related("user")
        )

    def find_by_specializations(self, specializations: list[str]) -> list[TherapistProfile]:
        """Find therapist profiles by specializations."""
        return list(TherapistProfile.objects.filter(specializations__overlap=specializations).select_related("user"))

    def find_by_location(self, location: str, radius: int = 25) -> list[TherapistProfile]:
        """Find therapist profiles within a location radius."""
        # Note: This would need proper geographic search implementation
        # For now, using simple filtering based on user location or practice location
        return list(TherapistProfile.objects.filter(user__location__icontains=location).select_related("user"))

    def find_by_approaches(self, approaches: list[str]) -> list[TherapistProfile]:
        """Find therapist profiles by therapeutic approaches."""
        return list(TherapistProfile.objects.filter(therapeutic_approaches__overlap=approaches).select_related("user"))

    def find_by_license_state(self, state: str) -> list[TherapistProfile]:
        """Find therapist profiles licensed in a specific state."""
        return list(TherapistProfile.objects.filter(license_state=state).select_related("user"))
