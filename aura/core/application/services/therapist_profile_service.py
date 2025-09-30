"""
Service layer for therapist profile operations.
Orchestrates therapist profile use cases and provides a clean interface for views.
"""

from aura.core.application.use_cases.therapist_profile import CreateTherapistProfileRequest
from aura.core.application.use_cases.therapist_profile import CreateTherapistProfileUseCase
from aura.core.application.use_cases.therapist_profile import GetTherapistProfileRequest
from aura.core.application.use_cases.therapist_profile import GetTherapistProfileUseCase
from aura.core.application.use_cases.therapist_profile import UpdateTherapistProfileRequest
from aura.core.application.use_cases.therapist_profile import UpdateTherapistProfileUseCase
from aura.core.domain.repositories.therapist_profile_repository import TherapistProfileRepository


class TherapistProfileService:
    """Service for therapist profile operations."""

    def __init__(self, therapist_profile_repository: TherapistProfileRepository):
        self._repository = therapist_profile_repository
        self._create_use_case = CreateTherapistProfileUseCase(therapist_profile_repository)
        self._update_use_case = UpdateTherapistProfileUseCase(therapist_profile_repository)
        self._get_use_case = GetTherapistProfileUseCase(therapist_profile_repository)

    def create_profile(self, user, professional_info: dict, practice_details: dict, availability: dict, rates: dict):
        """Create a new therapist profile."""
        request = CreateTherapistProfileRequest(
            user=user,
            professional_info=professional_info,
            practice_details=practice_details,
            availability=availability,
            rates=rates,
        )
        return self._create_use_case.execute(request)

    def get_profile(self, user):
        """Get therapist profile for user."""
        request = GetTherapistProfileRequest(user=user)
        return self._get_use_case.execute(request)

    def update_profile(self, user, update_data: dict):
        """Update therapist profile."""
        profile = self._repository.find_by_user(user)
        if not profile:
            return {"success": False, "error_message": "Therapist profile not found"}

        request = UpdateTherapistProfileRequest(profile=profile, update_data=update_data)
        return self._update_use_case.execute(request)

    def serialize_profile(self, profile):
        """Serialize therapist profile for API response."""
        return {
            "id": str(profile.user.id),
            "license_number": profile.license_number,
            "license_state": profile.license_state,
            "years_experience": profile.years_experience,
            "credentials": profile.credentials,
            "specializations": profile.specializations,
            "therapeutic_approaches": profile.therapeutic_approaches,
            "session_formats": profile.session_formats,
            "languages": profile.languages,
            "age_groups": profile.age_groups,
            "timezone": profile.timezone,
            "session_duration": profile.session_duration,
            "weekly_hours": profile.weekly_hours,
            "evening_availability": profile.evening_availability,
            "weekend_availability": profile.weekend_availability,
            "base_rate": profile.base_rate,
            "sliding_scale_available": profile.sliding_scale_available,
            "insurance_accepted": profile.insurance_accepted,
            "verification_status": profile.verification_status,
            "verified_at": profile.verified_at.isoformat() if profile.verified_at else None,
            "profile_completed": profile.profile_completed,
            "available_for_matching": profile.available_for_matching,
            "embeddings_generated": profile.embeddings_generated,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
