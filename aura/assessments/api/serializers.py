from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ValidationError

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction
from aura.users.api.serializers import PatientSerializer


class HealthRiskPredictionSerializer(HyperlinkedModelSerializer[HealthRiskPrediction]):
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
        extra_kwargs = {
            "url": {"view_name": "api:predictions-detail", "lookup_field": "pk"},
        }


class HealthAssessmentSerializer(ModelSerializer[HealthAssessment]):
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
            msg = "Responses must be a JSON object"
            raise ValidationError(msg)
        return value


class HealthAssessmentCreateSerializer(ModelSerializer):
    class Meta:
        model = HealthAssessment
        fields = ["assessment_type", "responses"]
