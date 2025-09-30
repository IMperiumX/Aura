"""
Use cases for therapist profile operations.
Contains business logic for creating, updating, and managing therapist profiles.
"""

from dataclasses import dataclass

from aura.core.domain.repositories.therapist_profile_repository import TherapistProfileRepository
from aura.users.models import TherapistProfile
from aura.users.models import User


@dataclass
class CreateTherapistProfileRequest:
    """Request for creating a therapist profile."""

    user: User
    professional_info: dict
    practice_details: dict
    availability: dict
    rates: dict


@dataclass
class CreateTherapistProfileResponse:
    """Response for creating a therapist profile."""

    success: bool
    profile: TherapistProfile | None = None
    error_message: str | None = None


@dataclass
class UpdateTherapistProfileRequest:
    """Request for updating a therapist profile."""

    profile: TherapistProfile
    update_data: dict


@dataclass
class UpdateTherapistProfileResponse:
    """Response for updating a therapist profile."""

    success: bool
    profile: TherapistProfile | None = None
    error_message: str | None = None


@dataclass
class GetTherapistProfileRequest:
    """Request for getting a therapist profile."""

    user: User


@dataclass
class GetTherapistProfileResponse:
    """Response for getting a therapist profile."""

    success: bool
    profile: TherapistProfile | None = None
    error_message: str | None = None


class CreateTherapistProfileUseCase:
    """Use case for creating a therapist profile."""

    def __init__(self, therapist_profile_repository: TherapistProfileRepository):
        self._repository = therapist_profile_repository

    def execute(self, request: CreateTherapistProfileRequest) -> CreateTherapistProfileResponse:
        """Execute the create therapist profile use case."""
        try:
            # Check if profile already exists
            existing_profile = self._repository.find_by_user(request.user)
            if existing_profile:
                return CreateTherapistProfileResponse(success=False, error_message="Therapist profile already exists")

            # Validate and prepare profile data
            profile_data = self._prepare_profile_data(
                request.professional_info, request.practice_details, request.availability, request.rates
            )

            # Create profile
            profile = self._repository.create_profile(request.user, profile_data)

            return CreateTherapistProfileResponse(success=True, profile=profile)

        except ValueError as e:
            return CreateTherapistProfileResponse(success=False, error_message=str(e))
        except Exception as e:
            return CreateTherapistProfileResponse(success=False, error_message=f"Profile creation failed: {e!s}")

    def _prepare_profile_data(
        self, professional_info: dict, practice_details: dict, availability: dict, rates: dict
    ) -> dict:
        """Prepare and validate profile data."""
        return {
            "license_number": professional_info.get("license_number"),
            "license_state": professional_info.get("license_state"),
            "years_experience": professional_info.get("years_experience", 0),
            "credentials": professional_info.get("credentials", []),
            "specializations": professional_info.get("specializations", []),
            "therapeutic_approaches": practice_details.get("therapeutic_approaches", []),
            "session_formats": practice_details.get("session_formats", []),
            "languages": practice_details.get("languages", ["english"]),
            "age_groups": practice_details.get("age_groups", []),
            "timezone": availability.get("timezone", "America/New_York"),
            "session_duration": availability.get("session_duration", [45, 60]),
            "weekly_hours": availability.get("weekly_hours", 40),
            "evening_availability": availability.get("evening_availability", False),
            "weekend_availability": availability.get("weekend_availability", False),
            "base_rate": str(rates.get("base_rate", 0)),
            "sliding_scale_available": rates.get("sliding_scale_available", False),
            "insurance_accepted": rates.get("insurance_accepted", []),
            "profile_completed": True,
            "verification_status": "pending",
        }


class UpdateTherapistProfileUseCase:
    """Use case for updating a therapist profile."""

    def __init__(self, therapist_profile_repository: TherapistProfileRepository):
        self._repository = therapist_profile_repository

    def execute(self, request: UpdateTherapistProfileRequest) -> UpdateTherapistProfileResponse:
        """Execute the update therapist profile use case."""
        try:
            # Update profile fields
            for key, value in request.update_data.items():
                if hasattr(request.profile, key):
                    setattr(request.profile, key, value)

            # Check if profile is now complete
            self._check_profile_completion(request.profile)

            # Save updated profile
            updated_profile = self._repository.update_profile(request.profile)

            return UpdateTherapistProfileResponse(success=True, profile=updated_profile)

        except ValueError as e:
            return UpdateTherapistProfileResponse(success=False, error_message=str(e))
        except Exception as e:
            return UpdateTherapistProfileResponse(success=False, error_message=f"Profile update failed: {e!s}")

    def _check_profile_completion(self, profile: TherapistProfile) -> None:
        """Check and update profile completion status."""
        required_fields = [
            "license_number",
            "license_state",
            "years_experience",
            "credentials",
            "specializations",
            "therapeutic_approaches",
            "session_formats",
            "base_rate",
        ]

        is_complete = all(getattr(profile, field, None) for field in required_fields)
        profile.profile_completed = is_complete

        # Only enable matching if verified
        if is_complete and profile.verification_status == "verified":
            profile.available_for_matching = True


class GetTherapistProfileUseCase:
    """Use case for getting a therapist profile."""

    def __init__(self, therapist_profile_repository: TherapistProfileRepository):
        self._repository = therapist_profile_repository

    def execute(self, request: GetTherapistProfileRequest) -> GetTherapistProfileResponse:
        """Execute the get therapist profile use case."""
        try:
            profile = self._repository.find_by_user(request.user)

            if not profile:
                return GetTherapistProfileResponse(success=False, error_message="Therapist profile not found")

            return GetTherapistProfileResponse(success=True, profile=profile)

        except Exception as e:
            return GetTherapistProfileResponse(success=False, error_message=f"Failed to retrieve profile: {e!s}")
