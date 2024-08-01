from rest_framework import serializers

from aura.assessments.models import HealthAssessment, HealthRiskPrediction
from aura.users.api.serializers import PatientSerializer
from aura.users.models import Patient

from decimal import Decimal


class HealthRiskPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthRiskPrediction
        fields = [
            "id",
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

    # def create(self, validated_data):
    #     patient_id = self.context["request"].data.get("patient_id")
    #     patient = Patient.objects.get(id=patient_id)
    #     validated_data["patient"] = patient
    #     return super().create(validated_data)
