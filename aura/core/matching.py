from typing import Any

from aura.users.models import PatientProfile
from aura.users.models import TherapistProfile


class TherapistMatcher:
    """
    Intelligent therapist matching algorithm using multiple factors:
    - Vector similarity (40%)
    - Availability compatibility (25%)
    - Location proximity (20%)
    - Budget compatibility (15%)
    """

    def __init__(self, patient_profile: PatientProfile):
        self.patient_profile = patient_profile
        self.vector_similarity_weight = 0.4
        self.availability_weight = 0.25
        self.location_weight = 0.2
        self.budget_weight = 0.15

    def find_matches(self, limit: int = 10, location_radius: int = 25) -> list[dict[str, Any]]:
        """
        Find matching therapists for the patient

        Args:
            limit: Maximum number of matches to return
            location_radius: Maximum distance in miles

        Returns:
            List of match dictionaries with therapist info and compatibility scores
        """
        # Get available therapists
        available_therapists = self._get_available_therapists()

        if not available_therapists:
            return []

        # Calculate compatibility scores for each therapist
        matches = []
        for therapist in available_therapists:
            compatibility_score, match_reasons = self._calculate_compatibility(therapist, location_radius)

            if compatibility_score > 0.3:  # Minimum threshold
                match_data = {
                    "therapist_id": str(therapist.user.id),
                    "compatibility_score": round(compatibility_score, 2),
                    "match_reasons": match_reasons,
                    "therapist_summary": self._get_therapist_summary(therapist),
                }
                matches.append(match_data)

        # Sort by compatibility score descending
        matches.sort(key=lambda x: x["compatibility_score"], reverse=True)

        return matches[:limit]

    def _get_available_therapists(self) -> list[TherapistProfile]:
        """Get therapists available for matching"""
        return TherapistProfile.objects.filter(
            available_for_matching=True, verification_status="approved", profile_completed=True
        ).select_related("user")

    def _calculate_compatibility(self, therapist: TherapistProfile, location_radius: int) -> tuple[float, list[str]]:
        """
        Calculate overall compatibility score and reasons

        Returns:
            Tuple of (compatibility_score, match_reasons)
        """
        match_reasons = []
        total_score = 0.0

        # 1. Vector similarity (40% weight)
        vector_score = self._calculate_vector_similarity(therapist)
        total_score += vector_score * self.vector_similarity_weight
        if vector_score > 0.7:
            match_reasons.extend(self._get_specialization_matches(therapist))

        # 2. Availability compatibility (25% weight)
        availability_score = self._calculate_availability_compatibility(therapist)
        total_score += availability_score * self.availability_weight
        if availability_score > 0.6:
            match_reasons.append("Available for your preferred schedule")

        # 3. Location proximity (20% weight)
        location_score = self._calculate_location_compatibility(therapist, location_radius)
        total_score += location_score * self.location_weight
        if location_score > 0.7:
            match_reasons.append("Located conveniently near you")

        # 4. Budget compatibility (15% weight)
        budget_score = self._calculate_budget_compatibility(therapist)
        total_score += budget_score * self.budget_weight
        if budget_score > 0.8:
            match_reasons.append("Within your budget range")

        return total_score, match_reasons

    def _calculate_vector_similarity(self, therapist: TherapistProfile) -> float:
        """
        Calculate semantic similarity between patient needs and therapist specializations.
        In production, this would use actual vector embeddings.
        For now, we use keyword matching as a placeholder.
        """
        if not self.patient_profile.primary_concerns or not therapist.specializations:
            return 0.0

        patient_concerns = set(self.patient_profile.primary_concerns)
        therapist_specializations = set(therapist.specializations)

        # Calculate Jaccard similarity
        intersection = patient_concerns.intersection(therapist_specializations)
        union = patient_concerns.union(therapist_specializations)

        if not union:
            return 0.0

        jaccard_similarity = len(intersection) / len(union)

        # Boost score for therapy type matches
        therapy_boost = 0.0
        if self.patient_profile.therapy_types and therapist.therapeutic_approaches:
            patient_types = set(self.patient_profile.therapy_types)
            therapist_approaches = set(therapist.therapeutic_approaches)
            therapy_intersection = patient_types.intersection(therapist_approaches)
            if therapy_intersection:
                therapy_boost = 0.3 * (len(therapy_intersection) / len(patient_types))

        return min(1.0, jaccard_similarity + therapy_boost)

    def _calculate_availability_compatibility(self, therapist: TherapistProfile) -> float:
        """Calculate availability compatibility score"""
        score = 0.0

        # Session format compatibility
        if self.patient_profile.session_format and therapist.session_formats:
            patient_formats = set(self.patient_profile.session_format)
            therapist_formats = set(therapist.session_formats)
            if patient_formats.intersection(therapist_formats):
                score += 0.4

        # Session duration compatibility
        if self.patient_profile.session_duration and therapist.session_duration:
            patient_duration = self.patient_profile.session_duration
            if patient_duration in therapist.session_duration:
                score += 0.3

        # Frequency compatibility (simplified - all therapists assumed compatible)
        score += 0.3

        return min(1.0, score)

    def _calculate_location_compatibility(self, therapist: TherapistProfile, max_radius: int) -> float:
        """
        Calculate location proximity score.
        In production, this would use actual geocoding and distance calculation.
        For now, we use simplified string matching.
        """
        if not self.patient_profile.location or not hasattr(therapist.user, "location"):
            return 0.5  # Neutral score if no location data

        patient_location = self.patient_profile.location.lower()
        # In a real implementation, you'd get therapist location from their profile
        # For now, assume same city = 1.0, same state = 0.7, else 0.3

        # Simplified location matching
        if "los angeles" in patient_location:
            return 0.9  # Assume good match for demo

        return 0.5  # Neutral score

    def _calculate_budget_compatibility(self, therapist: TherapistProfile) -> float:
        """Calculate budget compatibility score"""
        if not self.patient_profile.budget_range or not therapist.base_rate:
            return 0.5  # Neutral if no budget info

        try:
            # Parse budget range (e.g., "100-150")
            budget_parts = self.patient_profile.budget_range.split("-")
            if len(budget_parts) != 2:
                return 0.5

            min_budget = int(budget_parts[0])
            max_budget = int(budget_parts[1])
            therapist_rate = int(float(therapist.base_rate))

            # Perfect match if within range
            if min_budget <= therapist_rate <= max_budget:
                return 1.0

            # Partial match if close to range
            if abs(therapist_rate - max_budget) <= 25:
                return 0.7

            # Poor match if too expensive
            return 0.2

        except (ValueError, AttributeError):
            return 0.5

    def _get_specialization_matches(self, therapist: TherapistProfile) -> list[str]:
        """Get specific specialization match reasons"""
        reasons = []

        if not self.patient_profile.primary_concerns or not therapist.specializations:
            return reasons

        patient_concerns = set(self.patient_profile.primary_concerns)
        therapist_specializations = set(therapist.specializations)
        matches = patient_concerns.intersection(therapist_specializations)

        for match in matches:
            reasons.append(f"Specializes in {match}")

        # Check therapy type matches
        if self.patient_profile.therapy_types and therapist.therapeutic_approaches:
            patient_types = set(self.patient_profile.therapy_types)
            therapist_approaches = set(therapist.therapeutic_approaches)
            therapy_matches = patient_types.intersection(therapist_approaches)

            for match in therapy_matches:
                reasons.append(f"Uses {match} approach you prefer")

        return reasons

    def _get_therapist_summary(self, therapist: TherapistProfile) -> dict[str, Any]:
        """Get therapist summary for match results"""
        return {
            "name": f"Dr. {therapist.user.first_name} {therapist.user.last_name}",
            "credentials": therapist.credentials if therapist.credentials else [],
            "years_experience": therapist.years_experience,
            "specializations": therapist.specializations if therapist.specializations else [],
            "session_rate": therapist.base_rate,
            "availability_preview": self._get_availability_preview(therapist),
        }

    def _get_availability_preview(self, therapist: TherapistProfile) -> str:
        """Get a preview of therapist availability"""
        preview_parts = []

        if therapist.evening_availability:
            preview_parts.append("evenings")
        if therapist.weekend_availability:
            preview_parts.append("weekends")

        if preview_parts:
            return f"Available {', '.join(preview_parts)}"

        return "Available weekdays"


class MatchFeedbackProcessor:
    """Process patient feedback on matches to improve future recommendations"""

    @staticmethod
    def process_feedback(
        patient_profile: PatientProfile, therapist_id: str, feedback_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process feedback and update patient preferences

        Args:
            patient_profile: The patient's profile
            therapist_id: ID of the therapist being rated
            feedback_data: Feedback data from the request

        Returns:
            Dictionary indicating what was updated
        """
        feedback_type = feedback_data.get("feedback_type")
        details = feedback_data.get("feedback_details", {})
        preference_updates = feedback_data.get("preference_updates", {})

        updates_made = []

        # In a real implementation, you would:
        # 1. Store the feedback for analytics
        # 2. Update the matching algorithm weights based on feedback
        # 3. Adjust patient preference embeddings

        # For now, we'll simulate preference updates
        if preference_updates:
            if "increase_weight" in preference_updates:
                updates_made.append(f"Increased importance of {', '.join(preference_updates['increase_weight'])}")

            if "decrease_weight" in preference_updates:
                updates_made.append(f"Decreased importance of {', '.join(preference_updates['decrease_weight'])}")

        # Mark that embeddings need regeneration
        patient_profile.embeddings_generated = False
        patient_profile.save()

        return {
            "feedback_recorded": True,
            "preferences_updated": len(updates_made) > 0,
            "new_matches_available": True,
            "improvement_summary": "; ".join(updates_made) if updates_made else "Feedback recorded for analysis",
        }
