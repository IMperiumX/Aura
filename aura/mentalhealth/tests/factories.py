import factory
from django.db import models
from factory.django import DjangoModelFactory
from aura.mentalhealth import models
from django.utils import timezone


class TherapySessionFactory(DjangoModelFactory):
    class Meta:
        model = models.TherapySession

    session_type = models.TherapySession.SessionType.CHAT
    status = models.TherapySession.SessionStatus.PENDING
    summary = factory.Faker("text")
    notes = factory.Faker("text")
    scheduled_at = factory.Faker(
        "future_datetime",
        end_date="+30d",
        tzinfo=timezone.get_current_timezone(),
    )
    target_audience = models.TherapySession.TargetAudienceType.INDIVIDUAL
    therapist = factory.SubFactory("aura.users.tests.factories.TherapistFactory")
    patient = factory.SubFactory("aura.users.tests.factories.PatientFactory")
    recurrences = "RRULE:FREQ=WEEKLY;COUNT=10"


class TherapyApproachFactory(DjangoModelFactory):
    class Meta:
        model = models.TherapyApproach

    name = factory.Faker("word")
    description = factory.Faker("text")


class ChatbotInteractionFactory(DjangoModelFactory):
    class Meta:
        model = models.ChatbotInteraction

    message = factory.Faker("text")
    response = factory.Faker("text")
    conversation_log = factory.Faker("text")
    interaction_date = factory.Faker("past_datetime", start_date="-30d", end_date="now")
    created = factory.Faker("past_datetime", start_date="-30d", end_date="now")
    user = factory.SubFactory("aura.users.tests.factories.UserFactory")
