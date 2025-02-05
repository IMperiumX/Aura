from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_lifecycle import AFTER_CREATE
from django_lifecycle import LifecycleModelMixin
from django_lifecycle import hook
from pgvector.django import HnswIndex
from pgvector.django import VectorField
from taggit.managers import TaggableManager

from aura.core.utils import sane_repr
from aura.users.mixins import AuditModel

from .fields import AutoOneToOneField
from .managers import UserManager


class User(AbstractUser):
    """Default custom user model for aura.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.


    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True, max_length=100)
    username = None  # type: ignore[assignment]

    is_password_expired = models.BooleanField(
        _("password expired"),
        default=False,
        help_text=_(
            "If set to true then the user needs to change the "
            "password on next sign in.",
        ),
    )
    last_password_change = models.DateTimeField(
        _("date of last password change"),
        null=True,
        help_text=_("The date the password was changed last."),
    )

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    last_active = models.DateTimeField(
        _("last active"),
        default=timezone.now,
        null=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    # Having the user's id in the repr will help diagnosing which user is
    # not being serialized properly and is causing API requests to fail.
    __repr__ = sane_repr("id", "email")

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.


        :returns: URL for user detail.

        :rtype: str

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    def set_password(self, raw_password):
        """

        :param raw_password:

        """
        super().set_password(raw_password)
        self.last_password_change = timezone.now()
        self.is_password_expired = False


class AbstractProfile(LifecycleModelMixin, AuditModel):
    """An abstract model to represent a user's profile."""

    class GenderType(models.TextChoices):
        """Choices for the type of user gender."""

        MALE = "m", _(" Male")
        FEMALE = "f", _("Female")

    avatar_url = models.CharField(_("avatar url"), max_length=120)
    bio = models.TextField(blank=True, verbose_name=_("Biography"))
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(
        max_length=1,
        choices=GenderType.choices,
    )
    embedding = VectorField(
        dimensions=settings.EMBEDDING_MODEL_DIMENSIONS,
        null=True,
    )

    user = AutoOneToOneField(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="%(class)s_profile",
        null=True,
    )

    class Meta:
        """ """

        abstract = True

    __repr__ = sane_repr("id", "user")

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

    medical_record_number = models.CharField(max_length=50)
    insurance_provider = models.CharField(max_length=100)
    insurance_policy_number = models.CharField(max_length=50)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=30)
    allergies = models.TextField()
    medical_conditions = models.TextField()
    medical_history = models.JSONField(null=True, blank=True)
    current_medications = models.JSONField(null=True, blank=True)
    health_data = models.JSONField(null=True, blank=True)
    preferences = models.JSONField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True, verbose_name="Weight (kg)")
    height = models.FloatField(null=True, blank=True, verbose_name="Height (cm)")

    # relations
    disorders = models.ManyToManyField(
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

    license_number = models.CharField(max_length=50)
    years_of_experience = models.PositiveIntegerField(
        default=0,
        verbose_name="Years of Experience",
    )
    specialties = TaggableManager()
    availability = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Availability Schedule"),
    )

    class Meta:
        """ """

        verbose_name_plural = "Therapists"
        indexes = [
            HnswIndex(
                name="th_27072024_embedding_index",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class Coach(AbstractProfile):
    """A model to represent a coach"""

    certification = models.CharField(max_length=100)
    areas_of_expertise = models.CharField(max_length=25)
    coaching_philosophy = models.TextField(blank=True)
    availability = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Availability Schedule"),
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        verbose_name="Rating",
        default=Decimal(0.0),
    )
    specialization = models.CharField(max_length=100)
    weight = models.FloatField(null=True, blank=True, verbose_name="Weight (kg)")
    height = models.FloatField(null=True, blank=True, verbose_name="Height (cm)")

    class Meta:
        """ """

        order_with_respect_to = "rating"
        verbose_name_plural = "Coaches"


# physician
class Physician(AbstractProfile):
    """A model to represent a physician"""

    license_number = models.CharField(max_length=50)
    specialties = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField(
        default=0,
        verbose_name="Years of Experience",
    )
    availability = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Availability Schedule"),
    )

    class Meta:
        """ """

        verbose_name_plural = "Physicians"
