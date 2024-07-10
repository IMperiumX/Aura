"""
TODOs
Implementing more sophisticated recommendation algorithms based on
    - machine learning models.
    - Custom Querysets
    - vector similarity search for Postgres
    - Patient profiles and related models.
Incorporating user feedback on recommendations to improve future suggestions.
"""

from .models import HealthAssessment
from .models import HealthRiskPrediction


class RecommendationEngine:
    @staticmethod
    def get_mental_health_recommendations(health_assessment):
        if (
            health_assessment.assessment_type
            != HealthAssessment.AssessmentType.MENTAL_HEALTH
        ):
            return []

        risk_level = health_assessment.risk_level
        responses = health_assessment.responses

        # Get base recommendations based on risk level
        recommendations = HealthRiskPrediction.objects.filter(risk_level=risk_level)

        # Personalize recommendations based on assessment responses
        return [
            rec
            for rec in recommendations
            if RecommendationEngine._is_relevant(rec, responses)
        ]

    @staticmethod
    def _is_relevant(recommendation, responses):
        # Implement logic to determine if a recommendation is relevant
        # based on the user's responses
        # This is a simplified example and
        return (
            "anxiety" in responses
            and "anxiety" in recommendation.category.lower()
            or "depression" in responses
            and "depression" in recommendation.category.lower()
        )
