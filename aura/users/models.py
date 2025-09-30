# ruff: noqa: ERA001

from decimal import Decimal
from typing import ClassVar

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import SET_NULL
from django.db.models import CharField
from django.db.models import DateField
from django.db.models import DecimalField
from django.db.models import EmailField
from django.db.models import FloatField
from django.db.models import ForeignKey
from django.db.models import JSONField
from django.db.models import Model
from django.db.models import TextChoices
from django.db.models import TextField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_lifecycle import AFTER_CREATE
from django_lifecycle import LifecycleModelMixin
from django_lifecycle import hook

from aura.core.fields import EncryptedCharField
from aura.core.fields import EncryptedJSONField


def default_languages():
    return ["english"]


def default_session_duration():
    return [45, 60]


class UserManager(DjangoUserManager["User"]):
    """Custom manager for the User model."""

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            msg = "The given email must be set"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Default custom user model for aura.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class UserType(TextChoices):
        PATIENT = "patient", _("Patient")
        THERAPIST = "therapist", _("Therapist")

    # First and last name do not cover name patterns around the globe
    first_name = CharField(_("First Name"), max_length=150)
    last_name = CharField(_("Last Name"), max_length=150)
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]
    user_type = CharField(_("User Type"), max_length=20, choices=UserType.choices, default=UserType.PATIENT)
    is_verified = models.BooleanField(
        _("Verified"), default=False, help_text=_("Designates whether this user has been verified.")
    )
    terms_accepted = models.BooleanField(
        _("Terms Accepted"), default=False, help_text=_("Designates whether this user has accepted terms of service.")
    )
    privacy_policy_accepted = models.BooleanField(
        _("Privacy Policy Accepted"),
        default=False,
        help_text=_("Designates whether this user has accepted privacy policy."),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "user_type"]

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    @property
    def profile_completed(self) -> bool:
        """Check if user profile is completed."""
        if self.user_type == self.UserType.PATIENT:
            return hasattr(self, "patient_profile") and self.patient_profile is not None
        if self.user_type == self.UserType.THERAPIST:
            return hasattr(self, "therapist_profile") and self.therapist_profile is not None
        return False


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


class PatientProfile(models.Model):
    """Patient profile model with encrypted sensitive fields"""

    AGE_RANGE_CHOICES = [
        ("18-25", "18-25"),
        ("26-35", "26-35"),
        ("36-45", "36-45"),
        ("46-55", "46-55"),
        ("56-65", "56-65"),
        ("65+", "65+"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("non-binary", "Non-binary"),
        ("prefer-not-to-say", "Prefer not to say"),
    ]

    SESSION_FORMAT_CHOICES = [
        ("video", "Video"),
        ("audio", "Audio"),
        ("text", "Text"),
    ]

    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("bi-weekly", "Bi-weekly"),
        ("monthly", "Monthly"),
    ]

    THERAPIST_PREFERENCE_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("no_preference", "No Preference"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")

    # Personal Information (encrypted)
    age_range = EncryptedCharField(max_length=20, choices=AGE_RANGE_CHOICES, help_text="Patient's age range")
    gender = EncryptedCharField(max_length=20, choices=GENDER_CHOICES, help_text="Patient's gender")
    location = EncryptedCharField(max_length=200, help_text="Patient's location (city, state)")
    timezone = CharField(max_length=50, default="America/New_York", help_text="Patient's timezone")

    # Therapy Preferences (encrypted)
    session_format = EncryptedJSONField(default=list, help_text="Preferred session formats")
    frequency = EncryptedCharField(max_length=20, choices=FREQUENCY_CHOICES, default="weekly")
    session_duration = models.IntegerField(default=60, help_text="Preferred session duration in minutes")
    budget_range = EncryptedCharField(max_length=50, help_text="Budget range (e.g., '100-150')")

    # Therapeutic Needs (encrypted)
    primary_concerns = EncryptedJSONField(default=list, help_text="Primary mental health concerns")
    therapy_types = EncryptedJSONField(default=list, help_text="Preferred therapy types (CBT, DBT, etc.)")
    previous_therapy = models.BooleanField(default=False, help_text="Has previous therapy experience")
    crisis_support_needed = models.BooleanField(default=False, help_text="Needs crisis support")

    # Therapist Preferences (encrypted)
    therapist_gender_preference = EncryptedCharField(
        max_length=20, choices=THERAPIST_PREFERENCE_CHOICES, default="no_preference"
    )
    therapist_age_preference = EncryptedCharField(
        max_length=20, choices=THERAPIST_PREFERENCE_CHOICES, default="no_preference"
    )
    cultural_background = EncryptedJSONField(default=list, help_text="Preferred cultural backgrounds")
    languages = EncryptedJSONField(default=default_languages, help_text="Preferred languages")

    # Profile Status
    profile_completed = models.BooleanField(default=False)
    matching_enabled = models.BooleanField(default=False)
    embeddings_generated = models.BooleanField(default=False)

    # Vector embedding for matching (will be populated by AI service)
    profile_embeddings = models.JSONField(null=True, blank=True, help_text="Vector embeddings for matching algorithm")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_profiles"
        indexes = [
            models.Index(fields=["user", "profile_completed"]),
            models.Index(fields=["matching_enabled", "created_at"]),
        ]

    def __str__(self):
        return f"Patient Profile - {self.user.email}"

    def get_audit_log_data(self):
        """Return non-sensitive data for audit logging"""
        return {
            "user_id": str(self.user.id),
            "profile_completed": self.profile_completed,
            "matching_enabled": self.matching_enabled,
            "embeddings_generated": self.embeddings_generated,
        }


class TherapistProfile(models.Model):
    """Therapist profile model with verification and encrypted fields"""

    VERIFICATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    CREDENTIALS_CHOICES = [
        ("LMFT", "Licensed Marriage and Family Therapist"),
        ("LCSW", "Licensed Clinical Social Worker"),
        ("LPC", "Licensed Professional Counselor"),
        ("PhD", "Doctor of Philosophy"),
        ("PsyD", "Doctor of Psychology"),
        ("MD", "Medical Doctor"),
    ]

    SESSION_FORMAT_CHOICES = [
        ("video", "Video"),
        ("audio", "Audio"),
        ("in_person", "In-Person"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="therapist_profile")

    # Professional Information (encrypted)
    license_number = EncryptedCharField(max_length=100, help_text="Professional license number")
    license_state = EncryptedCharField(max_length=5, help_text="State where licensed")
    years_experience = models.IntegerField(help_text="Years of professional experience")
    credentials = EncryptedJSONField(default=list, help_text="Professional credentials")
    specializations = EncryptedJSONField(default=list, help_text="Areas of specialization")

    # Practice Details (encrypted)
    therapeutic_approaches = EncryptedJSONField(default=list, help_text="Therapeutic approaches used")
    session_formats = EncryptedJSONField(default=list, help_text="Available session formats")
    languages = EncryptedJSONField(default=default_languages, help_text="Languages spoken")
    age_groups = EncryptedJSONField(default=list, help_text="Age groups served")

    # Availability
    timezone = CharField(max_length=50, default="America/New_York", help_text="Therapist's timezone")
    session_duration = EncryptedJSONField(default=default_session_duration, help_text="Available session durations")
    weekly_hours = models.IntegerField(default=40, help_text="Hours available per week")
    evening_availability = models.BooleanField(default=False, help_text="Available during evening hours")
    weekend_availability = models.BooleanField(default=False, help_text="Available during weekends")

    # Rates (encrypted)
    base_rate = EncryptedCharField(max_length=10, help_text="Base rate per session")
    sliding_scale_available = models.BooleanField(default=False, help_text="Offers sliding scale pricing")
    insurance_accepted = EncryptedJSONField(default=list, help_text="Insurance providers accepted")

    # Verification Status
    verification_status = CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default="pending")
    verification_documents = EncryptedJSONField(default=dict, blank=True, help_text="Uploaded verification documents")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="Date when verification was completed")
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_therapists",
        help_text="Admin who verified the therapist",
    )

    # Profile Status
    profile_completed = models.BooleanField(default=False)
    available_for_matching = models.BooleanField(default=False)
    embeddings_generated = models.BooleanField(default=False)

    # Vector embedding for matching (will be populated by AI service)
    profile_embeddings = models.JSONField(null=True, blank=True, help_text="Vector embeddings for matching algorithm")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "therapist_profiles"
        indexes = [
            models.Index(fields=["user", "verification_status"]),
            models.Index(fields=["available_for_matching", "created_at"]),
            models.Index(fields=["verification_status", "profile_completed"]),
        ]

    def __str__(self):
        return f"Therapist Profile - {self.user.email}"

    @property
    def is_verified(self):
        return self.verification_status == "approved"

    def get_audit_log_data(self):
        """Return non-sensitive data for audit logging"""
        return {
            "user_id": str(self.user.id),
            "verification_status": self.verification_status,
            "profile_completed": self.profile_completed,
            "available_for_matching": self.available_for_matching,
            "embeddings_generated": self.embeddings_generated,
        }


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
