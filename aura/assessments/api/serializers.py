from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import ModelSerializer

from aura.assessments.models import Assessment
from aura.assessments.models import PatientAssessment
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
            "patient",
            "status",
            "created",
            "modified",
            "health_risk_predictions",
        ]
        read_only_fields = ["created", "modified"]


class PatientAssessmentSerializer(HyperlinkedModelSerializer):
    patient = PatientSerializer(read_only=True)
    assessment = AssessmentSerializer(read_only=True)

    class Meta:
        model = PatientAssessment
        fields = [
            "url",
            "id",
            "patient",
            "assessment",
            "result",
            "recommendations",
            "embedding",
        ]
        extra_kwargs = {
            "url": {
                "view_name": "api:patient-assessments-detail",
                "lookup_field": "pk",
            },
        }


class AssessmentCreateSerializer(ModelSerializer):
    class Meta:
        model = Assessment
        fields = ["assessment_type"]
