from django.db.models import Q
from django_filters import rest_framework as drf_filters

from aura.assessments.models import Assessment
from aura.assessments.models import PatientAssessment
from aura.assessments.models import RiskPrediction
from aura.core.filters import FullTextSearchFilter


class PatientAssessmentFilterSet(drf_filters.FilterSet):
    search = FullTextSearchFilter(
        field_name="result",
        search_fields=["result", "recommendations"],
    )
    class Meta:
        model = PatientAssessment
        exclude = ["embedding"]


class RiskPredictionFilterSet(drf_filters.FilterSet):
    min_confidence_level = drf_filters.NumberFilter(
        field_name="confidence_level",
        lookup_expr="gte",
    )
    max_confidence_level = drf_filters.NumberFilter(
        field_name="confidence_level",
        lookup_expr="lte",
    )

    class Meta:
        model = RiskPrediction
        fields = ["confidence_level"]


class QuestionFilterSet(drf_filters.FilterSet):
    allow_multiple = drf_filters.BooleanFilter(method="filter_allow_multiple")
    qa_type = drf_filters.ChoiceFilter(
        field_name="assessment__assessment_type", choices=Assessment.Type.choices
    )
    question_text = drf_filters.CharFilter(field_name="text", lookup_expr="icontains")

    @staticmethod
    def filter_allow_multiple(queryset, name, allow_multiple):
        q = Q(allow_multiple=False) | Q(allow_multiple__isnull=True)
        if allow_multiple:
            return queryset.exclude(q)
        return queryset.filter(q)
