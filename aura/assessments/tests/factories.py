import factory

from aura.assessments.models import HealthAssessment
from aura.assessments.models import HealthRiskPrediction


class HealthAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HealthAssessment

    assessment_type = factory.Faker(
        "random_element",
        elements=list(HealthAssessment.AssessmentType),
    )
    risk_level = factory.Faker("random_element", elements=["low", "moderate", "high"])
    recommendations = factory.Faker("paragraph")
    responses = factory.Faker("json")
    result = factory.Faker("paragraph")
    patient = factory.SubFactory("aura.users.tests.factories.PatientFactory")


class HealthRiskPredictionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HealthRiskPrediction

    health_issue = factory.Faker("sentence")
    preventive_measures = factory.Faker("paragraph")
    confidence_level = factory.Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        min_value=0,
        max_value=100,
    )
    source = factory.Faker("word")
    assessment = factory.SubFactory(
        "aura.assessments.tests.factories.HealthAssessmentFactory",
    )
    patient = factory.SubFactory("aura.users.tests.factories.PatientFactory")
