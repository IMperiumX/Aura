"""
Use cases for matching operations.
Contains business logic for finding therapist matches and processing feedback.
"""

from dataclasses import dataclass

from aura.core.domain.repositories.matching_repository import MatchingRepository
from aura.users.models import User


@dataclass
class GetPatientMatchesRequest:
    """Request for getting patient matches."""

    patient_user: User
    limit: int = 10
    location_radius: int = 25
    refresh: bool = False


@dataclass
class GetPatientMatchesResponse:
    """Response for getting patient matches."""

    success: bool
    matches: list | None = None
    total_matches: int = 0
    error_message: str | None = None


@dataclass
class SubmitMatchFeedbackRequest:
    """Request for submitting match feedback."""

    patient_user: User
    therapist_id: str
    feedback_type: str
    feedback_details: dict
    preference_updates: dict | None = None


@dataclass
class SubmitMatchFeedbackResponse:
    """Response for submitting match feedback."""

    success: bool
    feedback_processed: bool = False
    preferences_updated: bool = False
    error_message: str | None = None


class GetPatientMatchesUseCase:
    """Use case for getting therapist matches for a patient."""

    def __init__(self, matching_repository: MatchingRepository):
        self._repository = matching_repository

    def execute(self, request: GetPatientMatchesRequest) -> GetPatientMatchesResponse:
        """Execute the get patient matches use case."""
        try:
            # Get patient profile
            patient_profile = self._repository.find_patient_profile(request.patient_user.id)
            if not patient_profile:
                return GetPatientMatchesResponse(success=False, error_message="Patient profile not found")

            if not patient_profile.profile_completed:
                return GetPatientMatchesResponse(
                    success=False, error_message="Patient profile must be completed before matching"
                )

            # Find matching therapists
            therapist_profiles = self._repository.find_therapist_profiles_for_matching(
                specializations=patient_profile.therapy_types,
                location=patient_profile.location,
                radius=request.location_radius,
                therapy_types=patient_profile.therapy_types,
                budget_range=patient_profile.budget_range,
                session_format=patient_profile.session_format,
                therapist_gender_preference=patient_profile.therapist_gender_preference,
                languages=patient_profile.languages,
            )

            # Calculate compatibility scores and sort
            matches = []
            for therapist_profile in therapist_profiles:
                compatibility_score = self._repository.calculate_compatibility_score(patient_profile, therapist_profile)

                match_data = {
                    "therapist_id": str(therapist_profile.user.id),
                    "name": f"Dr. {therapist_profile.user.first_name} {therapist_profile.user.last_name}",
                    "credentials": therapist_profile.credentials,
                    "years_experience": therapist_profile.years_experience,
                    "specializations": therapist_profile.specializations,
                    "therapeutic_approaches": therapist_profile.therapeutic_approaches,
                    "base_rate": therapist_profile.base_rate,
                    "compatibility_score": compatibility_score,
                    "session_formats": therapist_profile.session_formats,
                    "languages": therapist_profile.languages,
                }
                matches.append(match_data)

            # Sort by compatibility score and limit results
            matches.sort(key=lambda x: x["compatibility_score"], reverse=True)
            matches = matches[: request.limit]

            return GetPatientMatchesResponse(success=True, matches=matches, total_matches=len(matches))

        except Exception as e:
            return GetPatientMatchesResponse(success=False, error_message=f"Failed to get matches: {e!s}")


class SubmitMatchFeedbackUseCase:
    """Use case for submitting feedback on therapist matches."""

    def __init__(self, matching_repository: MatchingRepository):
        self._repository = matching_repository

    def execute(self, request: SubmitMatchFeedbackRequest) -> SubmitMatchFeedbackResponse:
        """Execute the submit match feedback use case."""
        try:
            # Validate feedback type
            if request.feedback_type not in ["positive", "negative", "neutral"]:
                return SubmitMatchFeedbackResponse(success=False, error_message="Invalid feedback type")

            # Save feedback
            feedback_saved = self._repository.save_match_feedback(
                patient_id=request.patient_user.id,
                therapist_id=request.therapist_id,
                feedback_type=request.feedback_type,
                feedback_data=request.feedback_details,
            )

            # Update patient preferences if provided
            preferences_updated = False
            if request.preference_updates:
                patient_profile = self._repository.find_patient_profile(request.patient_user.id)
                if patient_profile:
                    self._repository.update_patient_preferences(patient_profile, request.preference_updates)
                    preferences_updated = True

            return SubmitMatchFeedbackResponse(
                success=True, feedback_processed=feedback_saved, preferences_updated=preferences_updated
            )

        except Exception as e:
            return SubmitMatchFeedbackResponse(success=False, error_message=f"Failed to submit feedback: {e!s}")
