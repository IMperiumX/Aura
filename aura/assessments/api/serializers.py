from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ValidationError

from aura.assessments.models import Assessment
from aura.assessments.models import RiskPrediction
from aura.users.api.serializers import PatientSerializer


class RiskPredictionSerializer(HyperlinkedModelSerializer[RiskPrediction]):
    class Meta:
        model = RiskPrediction
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


class AssessmentSerializer(ModelSerializer[Assessment]):
    patient = PatientSerializer(read_only=True)
    health_risk_predictions = RiskPredictionSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
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


class AssessmentCreateSerializer(ModelSerializer):
    class Meta:
        model = Assessment
        fields = ["assessment_type", "responses"]
