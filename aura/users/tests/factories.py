from collections.abc import Sequence
from typing import Any

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    email = factory.Faker("email")
    name = factory.Faker("name")
    last_password_change = factory.Faker(
        "date_time_this_month",
        tzinfo=timezone.get_current_timezone(),
    )

    @factory.post_generation
    def password(
        self,
        create,
        extracted: Sequence[Any],
        **kwargs,
    ):
        password = (
            extracted
            if extracted
            else factory.Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = "users.User"
        django_get_or_create = ["email"]


class PatientFactory(DjangoModelFactory):
    """Factory for Patient model."""

    class Meta:
        """Meta class for Patient"""

        model = "users.Patient"

    avatar_url = factory.Faker("image_url")
    bio = factory.Faker("text")
    date_of_birth = factory.Faker("date_of_birth", minimum_age=18)
    medical_record_number = factory.Faker("ssn")
    # medical_record_number = factory.factory.Faker('uuid4')
    insurance_provider = factory.Faker("company")
    insurance_policy_number = factory.Faker("ssn")
    # insurance_policy_number = factory.factory.Faker('random_number', digits=10)
    emergency_contact_name = factory.Faker("name")

    # set to EGY and USA number
    emergency_contact_phone = factory.Faker("phone_number")
    allergies = factory.Faker("text", max_nb_chars=100)
    medical_conditions = factory.Faker("text")
    medical_history = factory.Faker("json")
    current_medications = factory.Faker("json")
    health_data = factory.Faker("json")
    preferences = factory.Faker("json")
    weight = factory.Faker("random_int", min=50, max=150)
    height = factory.Faker("random_int", min=120, max=200)

    user = factory.SubFactory("aura.users.tests.factories.UserFactory")


class TherapistFactory(DjangoModelFactory):
    """Factory for Therapist model."""

    class Meta:
        """Meta class for Therapist"""

        model = "users.Therapist"

    avatar_url = factory.Faker("image_url")
    bio = factory.Faker("text")
    license_number = factory.Faker("ssn")
