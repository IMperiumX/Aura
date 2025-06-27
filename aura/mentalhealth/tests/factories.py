import datetime

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from aura.mentalhealth import models
from aura.users.tests.factories import PatientFactory, TherapistFactory, UserFactory

fake = Faker()


class TherapyApproachFactory(DjangoModelFactory):
    """Factory for TherapyApproach model."""

    name = factory.Sequence(lambda n: f"Therapy Approach {n}")
    description = factory.Faker("text")

    class Meta:
        model = models.TherapyApproach
        django_get_or_create = ["name"]


class DisorderFactory(DjangoModelFactory):
    """Factory for Disorder model."""

    name = factory.Sequence(lambda n: f"Disorder {n}")
    type = factory.Faker("random_element", elements=models.Disorder.DisorderType.values)
    signs_and_symptoms = factory.Faker("text")
    description = factory.Faker("text")
    treatment = factory.Faker("text")
    symptoms = factory.LazyFunction(lambda: [fake.word() for _ in range(5)])
    causes = factory.LazyFunction(lambda: [fake.word() for _ in range(5)])
    prevention = factory.Faker("text")

    class Meta:
        model = models.Disorder
        django_get_or_create = ["name"]


class TherapySessionFactory(DjangoModelFactory):
    """Factory for TherapySession model."""

    session_type = factory.Faker(
        "random_element", elements=models.TherapySession.SessionType.values
    )
    status = factory.Faker(
        "random_element", elements=models.TherapySession.SessionStatus.values
    )
    summary = factory.Faker("text")
    notes = factory.Faker("text")
    scheduled_at = factory.Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )
    target_audience = factory.Faker(
        "random_element",
        elements=models.TherapySession.TargetAudienceType.values,
    )
    therapist = factory.SubFactory(TherapistFactory)
    patient = factory.SubFactory(PatientFactory)

    @factory.lazy_attribute
    def started_at(self):
        if self.status in [
            models.TherapySession.SessionStatus.COMPLETED,
            models.TherapySession.SessionStatus.ACCEPTED,
        ]:
            return self.scheduled_at + datetime.timedelta(minutes=5)
        return None

    @factory.lazy_attribute
    def ended_at(self):
        if (
            self.status == models.TherapySession.SessionStatus.COMPLETED
            and self.started_at
        ):
            return self.started_at + datetime.timedelta(hours=1)
        return None

    class Meta:
        model = models.TherapySession


class ChatbotInteractionFactory(DjangoModelFactory):
    """Factory for ChatbotInteraction model."""

    message = factory.Faker("text")
    response = factory.Faker("text")
    conversation_log = factory.LazyFunction(list)
    interaction_date = factory.Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = models.ChatbotInteraction
        django_get_or_create = ["message"]
        django_get_or_create = ["message"]
