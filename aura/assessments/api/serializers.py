from rest_framework import serializers

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction


class HealthAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAssessment
        fields = [
            "assessment_type",
            "risk_level",
            "status",
            "created",
            "modified",
            "recommendations",
            "responses",
            "result",
            "patient",
        ]


class HealthRiskPredictionSerializer(serializers.ModelSerializer):
    assessment = HealthAssessmentSerializer()

    class Meta:
        model = HealthRiskPrediction
        fields = [
            "health_issue",
            "preventive_measures",
            "created",
            "modified",
            "confidence_level",
            "source",
            "assessment",
            "patient",
        ]
