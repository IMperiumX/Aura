import factory
from django.conf import settings
from factory.django import DjangoModelFactory

from aura.assessments.models import Assessment
from aura.assessments.models import PatientAssessment
from aura.assessments.models import Question
from aura.assessments.models import Response
from aura.assessments.models import RiskPrediction


class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assessment

    assessment_type = factory.Faker(
        "random_element",
        elements=[c[0] for c in Assessment.Type.choices],
    )
    risk_level = factory.Faker(
        "random_element",
        elements=[c[0] for c in Assessment.RiskLevel.choices],
    )
    status = factory.Faker(
        "random_element",
        elements=[c[0] for c in Assessment.Status.choices],
    )


class QuestionFactory(DjangoModelFactory):
    class Meta:
        model = Question

    text = factory.Faker("sentence")
    allow_multiple = factory.Faker("boolean")
    assessment = factory.SubFactory(
        AssessmentFactory,
    )  # Each Question belongs to an Assessment


class ResponseFactory(DjangoModelFactory):
    class Meta:
        model = Response

    text = factory.Faker("paragraph")
    question = factory.SubFactory(
        QuestionFactory,
    )  # Each Response belongs to a Question


class PatientAssessmentFactory(DjangoModelFactory):
    class Meta:
        model = PatientAssessment

    patient = factory.SubFactory("aura.users.tests.factories.PatientFactory")
    assessment = factory.SubFactory(AssessmentFactory)
    result = factory.Faker("text")
    recommendations = factory.Faker("text")
    # Placeholder for embedding. Replace with your actual embedding logic.
    embedding = factory.List(
        [
            factory.Faker("pyfloat", left_digits=1, right_digits=10, positive=True)
            for _ in range(settings.EMBEDDING_MODEL_DIMENSIONS)
        ],
    )


class RiskPredictionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskPrediction

    assessment = factory.SubFactory(PatientAssessmentFactory)
    health_issue = factory.Faker("sentence", nb_words=4)
    preventive_measures = factory.Faker("paragraph")
    confidence_level = factory.Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=1,
        max_value=100,
    )
    source = factory.Faker("word")
