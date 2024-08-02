from rest_framework import serializers

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction
from aura.users.api.serializers import PatientSerializer


class HealthRiskPredictionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HealthRiskPrediction
        fields = [
            "url",
            "id",
            "health_issue",
            "preventive_measures",
            "confidence_level",
            "source",
        ]


class HealthAssessmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    health_risk_predictions = HealthRiskPredictionSerializer(many=True, read_only=True)

    class Meta:
        model = HealthAssessment
        fields = [
            "id",
            "assessment_type",
            "risk_level",
            "recommendations",
            "responses",
            "result",
            "patient",
            "status",
            "created",
            "modified",
            "health_risk_predictions",
        ]
        read_only_fields = ["created", "modified"]

    def validate_responses(self, value):
        # Add custom validation for responses JSON field
        if not isinstance(value, dict):
            raise serializers.ValidationError("Responses must be a JSON object")
        return value


class HealthAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAssessment
        fields = ["assessment_type", "responses"]
