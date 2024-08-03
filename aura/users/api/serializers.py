import contextlib

from django.conf import settings
from django.contrib.auth import authenticate
from django.urls import exceptions as url_exceptions
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.serializers import CharField
from rest_framework.serializers import EmailField
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Serializer
from rest_framework.serializers import ValidationError
from rest_framework.serializers import SerializerMethodField
from rest_framework.serializers import DateTimeField

from aura.users.models import Patient
from aura.users.models import Review
from aura.users.models import Therapist
from aura.users.models import User
from rest_framework.authtoken.models import Token


class ReviewSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Review
        fields = [
            "url",
            "id",
            "reviewer",
            "content",
            "rating",
            "topic",
            "created",
        ]


class UserSerializer(HyperlinkedModelSerializer[User]):
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "url",
            "id",
            "name",
            "email",
            "reviews",
        ]

        extra_kwargs = {
            "url": {"view_name": "api:users-detail", "lookup_field": "pk"},
        }


class TherapistSerializer(ModelSerializer):
    class Meta:
        model = Therapist
        exclude = ["embedding"]


class PatientSerializer(HyperlinkedModelSerializer[Patient]):
    user = UserSerializer()
    class Meta:
        model = Patient
        exclude = ["embedding"]
        # fields = ['url', 'id', 'name', 'email']
        extra_kwargs = {
            "url": {"view_name": "api:patients-detail", "lookup_field": "pk"},
        }


class LoginSerializer(Serializer):
    username = CharField(required=False, allow_blank=True)
    email = EmailField(required=False, allow_blank=True)
    password = CharField(style={"input_type": "password"})

    def authenticate(self, **kwargs):
        return authenticate(self.context["request"], **kwargs)

    def _validate_email(self, email, password):
        if email and password:
            user = self.authenticate(email=email, password=password)
        else:
            msg = _('Must include "email" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def _validate_username(self, username, password):
        if username and password:
            user = self.authenticate(username=username, password=password)
        else:
            msg = _('Must include "username" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def _validate_username_email(self, username, email, password):
        if email and password:
            user = self.authenticate(email=email, password=password)
        elif username and password:
            user = self.authenticate(username=username, password=password)
        else:
            msg = _('Must include either "username" or "email" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def get_auth_user_using_allauth(self, username, email, password):
        from allauth.account import app_settings as allauth_account_settings

        # Authentication through email
        if (
            allauth_account_settings.AUTHENTICATION_METHOD
            == allauth_account_settings.AuthenticationMethod.EMAIL
        ):
            return self._validate_email(email, password)

        # Authentication through username
        if (
            allauth_account_settings.AUTHENTICATION_METHOD
            == allauth_account_settings.AuthenticationMethod.USERNAME
        ):
            return self._validate_username(username, password)

        # Authentication through either username or email
        return self._validate_username_email(username, email, password)

    def get_auth_user_using_orm(self, username, email, password):
        if email:
            with contextlib.suppress(User.DoesNotExist):
                username = User.objects.get(email__iexact=email).get_username()

        if username:
            return self._validate_username_email(username, "", password)

        return None

    def get_auth_user(self, username, email, password):
        """
        Retrieve the auth user from given POST payload by using
        either `allauth` auth scheme or bare Django auth scheme.

        Returns the authenticated user instance if credentials are correct,
        else `None` will be returned
        """
        if "allauth" in settings.INSTALLED_APPS:
            # When `is_active` of a user is set to False, allauth tries to return template html
            # which does not exist. This is the solution for it. See issue #264.
            try:
                return self.get_auth_user_using_allauth(username, email, password)
            except url_exceptions.NoReverseMatch:
                msg = _("Unable to log in with provided credentials.")
                raise exceptions.ValidationError(msg)
        return self.get_auth_user_using_orm(username, email, password)

    @staticmethod
    def validate_auth_user_status(user):
        if not user.is_active:
            msg = _("User account is disabled.")
            raise exceptions.ValidationError(msg)

    @staticmethod
    def validate_email_verification_status(user, email=None):
        from allauth.account import app_settings as allauth_account_settings

        if (
            allauth_account_settings.EMAIL_VERIFICATION
            == allauth_account_settings.EmailVerificationMethod.MANDATORY
            and not user.emailaddress_set.filter(
                email=user.email,
                verified=True,
            ).exists()
        ):
            raise ValidationError(_("E-mail is not verified."))

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")
        password = attrs.get("password")
        user = self.get_auth_user(username, email, password)

        if not user:
            msg = _("Unable to log in with provided credentials.")
            raise exceptions.ValidationError(msg)

        # Did we get back an active user?
        self.validate_auth_user_status(user)

        # # If required, is the email verified?
        if "aura.registration" in settings.INSTALLED_APPS:
            self.validate_email_verification_status(user, email=email)

        attrs["user"] = user
        return attrs
