from decimal import Decimal
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group
from django.db.models import SET_NULL
from django.db.models import CharField
from django.db.models import DateField
from django.db.models import DecimalField
from django.db.models import EmailField
from django.db.models import FloatField
from django.db.models import ForeignKey
from django.db.models import JSONField
from django.db.models import ManyToManyField
from django.db.models import Model
from django.db.models import PositiveIntegerField
from django.db.models import TextChoices
from django.db.models import TextField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_lifecycle import AFTER_CREATE
from django_lifecycle import LifecycleModelMixin
from django_lifecycle import hook
from taggit.managers import TaggableManager

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for aura.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class AbstractProfile(LifecycleModelMixin, Model):
    """An abstract model to represent a user's profile."""

    class GenderType(TextChoices):
        """Choices for the type of user gender."""

        MALE = "m", _(" Male")
        FEMALE = "f", _("Female")

    avatar_url = CharField(_("avatar url"), max_length=120)
    bio = TextField(blank=True, verbose_name=_("Biography"))
    date_of_birth = DateField(null=True)
    gender = CharField(
        max_length=1,
        choices=GenderType.choices,
    )
    # embedding = VectorField(
    #     dimensions=settings.EMBEDDING_MODEL_DIMENSIONS,
    #     null=True,
    # )

    user = ForeignKey(
        "users.User",
        on_delete=SET_NULL,
        related_name="%(class)s_profile",
        null=True,
    )

    class Meta:
        """ """

        abstract = True

    def __str__(self):
        return f"{self.user}"

    @hook(AFTER_CREATE)
    def add_to_group(self):
        if hasattr(self, "patient_profile"):
            group, _ = Group.objects.get_or_create(name="Patients")
            self.groups.add(group)
        elif hasattr(self, "therapist_profile"):
            group, _ = Group.objects.get_or_create(name="Therapists")
            self.groups.add(group)
        elif hasattr(self, "coach_profile"):
            group, _ = Group.objects.get_or_create(name="Coaches")
            self.groups.add(group)


class Patient(AbstractProfile):
    """A model to represent a patient"""

    medical_record_number = CharField(max_length=50)
    insurance_provider = CharField(max_length=100)
    insurance_policy_number = CharField(max_length=50)
    emergency_contact_name = CharField(max_length=100)
    emergency_contact_phone = CharField(max_length=30)
    allergies = TextField()
    medical_conditions = TextField()
    medical_history = JSONField(null=True, blank=True)
    current_medications = JSONField(null=True, blank=True)
    health_data = JSONField(null=True, blank=True)
    preferences = JSONField(null=True, blank=True)
    weight = FloatField(null=True, blank=True, verbose_name="Weight (kg)")
    height = FloatField(null=True, blank=True, verbose_name="Height (cm)")

    # relations
    disorders = ManyToManyField(
        "mentalhealth.Disorder",
        related_name="patients",
        verbose_name="Disorders",
    )

    class Meta:
        """ """

        verbose_name_plural = "Patients"

    def get_audit_log_data(self):
        return {
            "email": self.user.email,
            "medical_record_number": self.medical_record_number,
            "insurance_provider": self.insurance_provider,
            "insurance_policy_number": self.insurance_policy_number,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "allergies": self.allergies,
            "medical_conditions": self.medical_conditions,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "health_data": self.health_data,
            "preferences": self.preferences,
            "weight": self.weight,
            "height": self.height,
            "disorders": [disorder.name for disorder in self.disorders.all()],
        }


class Therapist(AbstractProfile):
    """A model to represent a therapist"""

    license_number = CharField(max_length=50)
    years_of_experience = PositiveIntegerField(
        default=0,
        verbose_name="Years of Experience",
    )
    specialties = TaggableManager()
    availability = JSONField(
        null=True,
        blank=True,
        verbose_name=_("Availability Schedule"),
    )

    class Meta:
        """ """

        verbose_name_plural = "Therapists"
        # indexes = [
        #     HnswIndex(
        #         name="th_27072024_embedding_index",
        #         fields=["embedding"],
        #         m=16,
        #         ef_construction=64,
        #         opclasses=["vector_cosine_ops"],
        #     ),
        # ]


class Coach(AbstractProfile):
    """A model to represent a coach"""

    certification = CharField(max_length=100)
    areas_of_expertise = CharField(max_length=25)
    coaching_philosophy = TextField(blank=True)
    availability = JSONField(
        null=True,
        blank=True,
        verbose_name=_("Availability Schedule"),
    )
    rating = DecimalField(
        max_digits=3,
        decimal_places=2,
        verbose_name="Rating",
        default=Decimal(0),
    )
    specialization = CharField(max_length=100)
    weight = FloatField(null=True, blank=True, verbose_name="Weight (kg)")
    height = FloatField(null=True, blank=True, verbose_name="Height (cm)")

    class Meta:
        """ """

        order_with_respect_to = "rating"
        verbose_name_plural = "Coaches"
