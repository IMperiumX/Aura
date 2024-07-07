from collections.abc import Callable
from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ForeignKey
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


def sane_repr(*attrs: str) -> Callable[[object], str]:
    """

    :param *attrs: str:

    """
    if "id" not in attrs and "pk" not in attrs:
        attrs = ("id", *attrs)

    def _repr(self: object) -> str:
        """

        :param self: object:
        :param self: object:
        :param self: object:

        """
        cls = type(self).__name__

        pairs = (f"{a}={getattr(self, a, None)!r}" for a in attrs)

        return "<{} at 0x{:x}: {}>".format(cls, id(self), ", ".join(pairs))

    return _repr


class FlexibleForeignKey(ForeignKey):
    """ """

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("on_delete", models.CASCADE)
        super().__init__(*args, **kwargs)


class User(AbstractUser):
    """Default custom user model for aura.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.


    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True, max_length=75)
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


class AbstractProfile(models.Model):
    """An abstract model to represent a user's profile."""

    class GenderType(models.TextChoices):
        """Choices for the type of user gender."""

        MALE = "m", _(" Male")
        FEMALE = "f", _("Female")

    avatar_url = models.CharField(_("avatar url"), max_length=120)
    bio = models.TextField(blank=True, verbose_name="Biography")
    date_of_birth = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    gender = models.CharField(
        max_length=1,
        choices=GenderType.choices,
    )

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
    )

    class Meta:
        """ """

        abstract = True

    def __str__(self):
        return f"{self.user} - {self.created_at}"


class UserProfile(AbstractProfile):
    """A model to represent a user's profile."""

    class Meta:
        """ """

        verbose_name_plural = "User Profiles"


class PatientProfile(AbstractProfile):
    """A model to represent a patient"""

    medical_record_number = models.CharField(max_length=20)
    insurance_provider = models.CharField(max_length=100)
    insurance_policy_number = models.CharField(max_length=20)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    allergies = models.TextField()
    medical_conditions = models.TextField()
    medical_history = models.JSONField(null=True, blank=True)
    current_medications = models.JSONField(null=True, blank=True)
    health_data = models.JSONField(null=True, blank=True)
    preferences = models.JSONField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True, verbose_name="Weight (kg)")
    height = models.FloatField(null=True, blank=True, verbose_name="Height (cm)")

    class Meta:
        """ """

        verbose_name_plural = "Patients"


class TherapistProfile(AbstractProfile):
    """A model to represent a therapist"""

    license_number = models.CharField(max_length=50)
    specialties = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField(
        verbose_name="Years of Experience",
    )
    availability = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Availability Schedule"),
    )

    class Meta:
        """ """

        verbose_name_plural = "Therapists"


class CoachProfile(AbstractProfile):
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
    )
    specialization = models.CharField(max_length=100)
    weight = models.FloatField(null=True, blank=True, verbose_name="Weight (kg)")
    height = models.FloatField(null=True, blank=True, verbose_name="Height (cm)")

    class Meta:
        """ """

        order_with_respect_to = "rating"
        verbose_name_plural = "Coaches"
