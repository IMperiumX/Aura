import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from aura.mentalhealth.models import ChatbotInteraction
from aura.mentalhealth.models import TherapyApproach
from aura.mentalhealth.models import TherapySession


class TherapySessionFactory(DjangoModelFactory):
    class Meta:
        model = TherapySession

    session_type = TherapySession.SessionType.CHAT
    status = TherapySession.SessionStatus.PENDING
    summary = factory.Faker("text")
    notes = factory.Faker("text")
    scheduled_at = factory.Faker(
        "future_datetime",
        end_date="+30d",
        tzinfo=timezone.get_current_timezone(),
    )
    target_audience = TherapySession.TargetAudienceType.INDIVIDUAL
    therapist = factory.SubFactory("aura.users.tests.factories.TherapistFactory")
    patient = factory.SubFactory("aura.users.tests.factories.PatientFactory")
    recurrences = "RRULE:FREQ=WEEKLY;COUNT=10"


class TherapyApproachFactory(DjangoModelFactory):
    class Meta:
        model = TherapyApproach

    name = factory.Faker("word")
    description = factory.Faker("text")


class ChatbotInteractionFactory(DjangoModelFactory):
    class Meta:
        model = ChatbotInteraction

    message = factory.Faker("text")
    response = factory.Faker("text")
    conversation_log = factory.Faker("text")
    interaction_date = factory.Faker("past_datetime", start_date="-30d", end_date="now")
    created = factory.Faker("past_datetime", start_date="-30d", end_date="now")
    user = factory.SubFactory("aura.users.tests.factories.UserFactory")
