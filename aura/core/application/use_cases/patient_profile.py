"""
Use cases for patient profile operations.
Contains business logic for creating, updating, and managing patient profiles.
"""

from dataclasses import dataclass

from aura.core.domain.repositories.patient_profile_repository import PatientProfileRepository
from aura.users.models import PatientProfile
from aura.users.models import User


@dataclass
class CreatePatientProfileRequest:
    """Request for creating a patient profile."""

    user: User
    personal_info: dict
    therapy_preferences: dict
    therapeutic_needs: dict
    therapist_preferences: dict


@dataclass
class CreatePatientProfileResponse:
    """Response for creating a patient profile."""

    success: bool
    profile: PatientProfile | None = None
    error_message: str | None = None


@dataclass
class UpdatePatientProfileRequest:
    """Request for updating a patient profile."""

    profile: PatientProfile
    update_data: dict


@dataclass
class UpdatePatientProfileResponse:
    """Response for updating a patient profile."""

    success: bool
    profile: PatientProfile | None = None
    error_message: str | None = None


@dataclass
class GetPatientProfileRequest:
    """Request for getting a patient profile."""

    user: User


@dataclass
class GetPatientProfileResponse:
    """Response for getting a patient profile."""

    success: bool
    profile: PatientProfile | None = None
    error_message: str | None = None


class CreatePatientProfileUseCase:
    """Use case for creating a patient profile."""

    def __init__(self, patient_profile_repository: PatientProfileRepository):
        self._repository = patient_profile_repository

    def execute(self, request: CreatePatientProfileRequest) -> CreatePatientProfileResponse:
        """Execute the create patient profile use case."""
        try:
            # Check if profile already exists
            existing_profile = self._repository.find_by_user(request.user)
            if existing_profile:
                return CreatePatientProfileResponse(success=False, error_message="Patient profile already exists")

            # Validate and prepare profile data
            profile_data = self._prepare_profile_data(
                request.personal_info,
                request.therapy_preferences,
                request.therapeutic_needs,
                request.therapist_preferences,
            )

            # Create profile
            profile = self._repository.create_profile(request.user, profile_data)

            return CreatePatientProfileResponse(success=True, profile=profile)

        except ValueError as e:
            return CreatePatientProfileResponse(success=False, error_message=str(e))
        except Exception as e:
            return CreatePatientProfileResponse(success=False, error_message=f"Profile creation failed: {e!s}")

    def _prepare_profile_data(
        self, personal_info: dict, therapy_preferences: dict, therapeutic_needs: dict, therapist_preferences: dict
    ) -> dict:
        """Prepare and validate profile data."""
        return {
            "age_range": personal_info.get("age_range"),
            "gender": personal_info.get("gender"),
            "location": personal_info.get("location"),
            "timezone": personal_info.get("timezone", "America/New_York"),
            "session_format": therapy_preferences.get("session_format", []),
            "frequency": therapy_preferences.get("frequency", "weekly"),
            "session_duration": therapy_preferences.get("duration", 60),
            "budget_range": therapy_preferences.get("budget_range"),
            "primary_concerns": therapeutic_needs.get("primary_concerns", []),
            "therapy_types": therapeutic_needs.get("therapy_types", []),
            "previous_therapy": therapeutic_needs.get("previous_therapy", False),
            "crisis_support_needed": therapeutic_needs.get("crisis_support_needed", False),
            "therapist_gender_preference": therapist_preferences.get("gender_preference", "no_preference"),
            "therapist_age_preference": therapist_preferences.get("age_preference", "no_preference"),
            "cultural_background": therapist_preferences.get("cultural_background", []),
            "languages": therapist_preferences.get("languages", ["english"]),
            "profile_completed": True,
            "matching_enabled": True,
        }


class UpdatePatientProfileUseCase:
    """Use case for updating a patient profile."""

    def __init__(self, patient_profile_repository: PatientProfileRepository):
        self._repository = patient_profile_repository

    def execute(self, request: UpdatePatientProfileRequest) -> UpdatePatientProfileResponse:
        """Execute the update patient profile use case."""
        try:
            # Update profile fields
            for key, value in request.update_data.items():
                if hasattr(request.profile, key):
                    setattr(request.profile, key, value)

            # Check if profile is now complete
            self._check_profile_completion(request.profile)

            # Save updated profile
            updated_profile = self._repository.update_profile(request.profile)

            return UpdatePatientProfileResponse(success=True, profile=updated_profile)

        except ValueError as e:
            return UpdatePatientProfileResponse(success=False, error_message=str(e))
        except Exception as e:
            return UpdatePatientProfileResponse(success=False, error_message=f"Profile update failed: {e!s}")

    def _check_profile_completion(self, profile: PatientProfile) -> None:
        """Check and update profile completion status."""
        required_fields = [
            "age_range",
            "gender",
            "location",
            "session_format",
            "frequency",
            "budget_range",
            "primary_concerns",
            "therapy_types",
        ]

        is_complete = all(getattr(profile, field, None) for field in required_fields)
        profile.profile_completed = is_complete
        if is_complete:
            profile.matching_enabled = True


class GetPatientProfileUseCase:
    """Use case for getting a patient profile."""

    def __init__(self, patient_profile_repository: PatientProfileRepository):
        self._repository = patient_profile_repository

    def execute(self, request: GetPatientProfileRequest) -> GetPatientProfileResponse:
        """Execute the get patient profile use case."""
        try:
            profile = self._repository.find_by_user(request.user)

            if not profile:
                return GetPatientProfileResponse(success=False, error_message="Patient profile not found")

            return GetPatientProfileResponse(success=True, profile=profile)

        except Exception as e:
            return GetPatientProfileResponse(success=False, error_message=f"Failed to retrieve profile: {e!s}")
