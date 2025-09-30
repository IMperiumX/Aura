"""
Service layer for matching operations.
Orchestrates matching use cases and provides a clean interface for views.
"""

from django.core.cache import cache

from aura.core.application.use_cases.matching import GetPatientMatchesRequest
from aura.core.application.use_cases.matching import GetPatientMatchesUseCase
from aura.core.application.use_cases.matching import SubmitMatchFeedbackRequest
from aura.core.application.use_cases.matching import SubmitMatchFeedbackUseCase
from aura.core.domain.repositories.matching_repository import MatchingRepository


class MatchingService:
    """Service for matching operations."""

    def __init__(self, matching_repository: MatchingRepository):
        self._repository = matching_repository
        self._get_matches_use_case = GetPatientMatchesUseCase(matching_repository)
        self._submit_feedback_use_case = SubmitMatchFeedbackUseCase(matching_repository)

    def get_patient_matches(self, patient_user, limit: int = 10, location_radius: int = 25, refresh: bool = False):
        """Get therapist matches for a patient."""
        # Check cache first (unless refresh requested)
        cache_key = f"patient_matches_{patient_user.id}_{limit}_{location_radius}"

        if not refresh:
            cached_matches = cache.get(cache_key)
            if cached_matches:
                return {
                    "success": True,
                    "matches": cached_matches["matches"],
                    "total_matches": cached_matches["total_matches"],
                    "generated_at": cached_matches["generated_at"],
                    "next_refresh_available": cached_matches["next_refresh_available"],
                    "cached": True,
                }

        # Generate new matches using use case
        request = GetPatientMatchesRequest(
            patient_user=patient_user, limit=limit, location_radius=location_radius, refresh=refresh
        )
        response = self._get_matches_use_case.execute(request)

        if response.success:
            # Cache results for 1 hour
            from django.utils import timezone

            now = timezone.now()
            next_refresh = now + timezone.timedelta(hours=1)

            match_data = {
                "matches": response.matches,
                "total_matches": response.total_matches,
                "generated_at": now.isoformat(),
                "next_refresh_available": next_refresh.isoformat(),
            }

            cache.set(cache_key, match_data, 3600)

            return {
                "success": True,
                "matches": response.matches,
                "total_matches": response.total_matches,
                "generated_at": match_data["generated_at"],
                "next_refresh_available": match_data["next_refresh_available"],
                "cached": False,
            }

        return {"success": False, "error_message": response.error_message}

    def submit_match_feedback(
        self,
        patient_user,
        therapist_id: str,
        feedback_type: str,
        feedback_details: dict,
        preference_updates: dict = None,
    ):
        """Submit feedback on therapist matches."""
        request = SubmitMatchFeedbackRequest(
            patient_user=patient_user,
            therapist_id=therapist_id,
            feedback_type=feedback_type,
            feedback_details=feedback_details,
            preference_updates=preference_updates,
        )

        response = self._submit_feedback_use_case.execute(request)

        if response.success:
            # Clear cached matches since preferences may have changed
            cache_pattern = f"patient_matches_{patient_user.id}_*"
            # Note: Django cache doesn't support pattern deletion by default
            # You might want to implement a more sophisticated cache invalidation
            cache.delete_many([cache_pattern])

            return {
                "success": True,
                "feedback_processed": response.feedback_processed,
                "preferences_updated": response.preferences_updated,
                "message": "Feedback submitted successfully",
            }

        return {"success": False, "error_message": response.error_message}
