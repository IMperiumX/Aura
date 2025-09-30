"""
Service layer for patient profile operations.
Orchestrates patient profile use cases and provides a clean interface for views.
"""

from aura.core.application.use_cases.patient_profile import CreatePatientProfileRequest
from aura.core.application.use_cases.patient_profile import CreatePatientProfileUseCase
from aura.core.application.use_cases.patient_profile import GetPatientProfileRequest
from aura.core.application.use_cases.patient_profile import GetPatientProfileUseCase
from aura.core.application.use_cases.patient_profile import UpdatePatientProfileRequest
from aura.core.application.use_cases.patient_profile import UpdatePatientProfileUseCase
from aura.core.domain.repositories.patient_profile_repository import PatientProfileRepository


class PatientProfileService:
    """Service for patient profile operations."""

    def __init__(self, patient_profile_repository: PatientProfileRepository):
        self._repository = patient_profile_repository
        self._create_use_case = CreatePatientProfileUseCase(patient_profile_repository)
        self._update_use_case = UpdatePatientProfileUseCase(patient_profile_repository)
        self._get_use_case = GetPatientProfileUseCase(patient_profile_repository)

    def create_profile(
        self, user, personal_info: dict, therapy_preferences: dict, therapeutic_needs: dict, therapist_preferences: dict
    ):
        """Create a new patient profile."""
        request = CreatePatientProfileRequest(
            user=user,
            personal_info=personal_info,
            therapy_preferences=therapy_preferences,
            therapeutic_needs=therapeutic_needs,
            therapist_preferences=therapist_preferences,
        )
        return self._create_use_case.execute(request)

    def get_profile(self, user):
        """Get patient profile for user."""
        request = GetPatientProfileRequest(user=user)
        return self._get_use_case.execute(request)

    def update_profile(self, user, update_data: dict):
        """Update patient profile."""
        profile = self._repository.find_by_user(user)
        if not profile:
            return {"success": False, "error_message": "Patient profile not found"}

        request = UpdatePatientProfileRequest(profile=profile, update_data=update_data)
        return self._update_use_case.execute(request)

    def serialize_profile(self, profile):
        """Serialize patient profile for API response."""
        return {
            "id": str(profile.user.id),
            "age_range": profile.age_range,
            "gender": profile.gender,
            "location": profile.location,
            "timezone": profile.timezone,
            "session_format": profile.session_format,
            "frequency": profile.frequency,
            "session_duration": profile.session_duration,
            "budget_range": profile.budget_range,
            "primary_concerns": profile.primary_concerns,
            "therapy_types": profile.therapy_types,
            "previous_therapy": profile.previous_therapy,
            "crisis_support_needed": profile.crisis_support_needed,
            "therapist_gender_preference": profile.therapist_gender_preference,
            "therapist_age_preference": profile.therapist_age_preference,
            "cultural_background": profile.cultural_background,
            "languages": profile.languages,
            "profile_completed": profile.profile_completed,
            "matching_enabled": profile.matching_enabled,
            "embeddings_generated": profile.embeddings_generated,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
