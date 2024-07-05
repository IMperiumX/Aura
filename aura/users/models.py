from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for aura.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
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


class UserProfile(models.Model):
    """
    A model to represent a user's profile.
    """

    class GenderType(models.TextChoices):
        """
        Choices for the type of user gender.
        """

        MALE = "m", _(" Male")
        FEMALE = "f", _("Female")

    bio = models.TextField(
        verbose_name="Bio",
    )
    date_of_birth = models.DateField(
        verbose_name="Date of Birth",
    )
    health_data = models.JSONField(null=True, blank=True)
    preferences = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    gender = models.CharField(
        max_length=1,
        choices=GenderType.choices,
    )
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="User",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user} - {self.created_at}"
