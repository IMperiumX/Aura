from collections.abc import Sequence
from typing import Any

from django.utils import timezone
from factory import Faker
from factory import SubFactory
from factory import post_generation
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    email = Faker("email")
    name = Faker("name")
    last_password_change = Faker(
        "date_time_this_month",
        tzinfo=timezone.get_current_timezone(),
    )

    class Meta:
        model = "users.User"
        django_get_or_create = ["email"]

    @post_generation
    def password(
        self,
        extracted: Sequence[Any],
        **kwargs,
    ):
        password = (
            extracted
            if extracted
            else Faker(
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


class PatientFactory(DjangoModelFactory):
    """Factory for Patient model."""

    class Meta:
        """Meta class for Patient"""

        model = "users.Patient"

    avatar_url = Faker("image_url")
    bio = Faker("text")
    date_of_birth = Faker("date_of_birth", minimum_age=18)
    medical_record_number = Faker("ssn")
    insurance_provider = Faker("company")
    insurance_policy_number = Faker("ssn")
    emergency_contact_name = Faker("name")

    # set to EGY and USA number
    emergency_contact_phone = Faker("phone_number")
    allergies = Faker("text")
    medical_conditions = Faker("text")
    medical_history = Faker("json")
    current_medications = Faker("json")
    health_data = Faker("json")
    preferences = Faker("json")
    weight = Faker("random_int", min=50, max=100)
    height = Faker("random_int", min=150, max=200)

    user = SubFactory("aura.users.users_factory.UserFactory")
