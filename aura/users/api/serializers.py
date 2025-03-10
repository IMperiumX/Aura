import contextlib

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from django.urls import exceptions as url_exceptions
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authtoken.models import Token
from rest_framework.serializers import CharField
from rest_framework.serializers import DateTimeField
from rest_framework.serializers import EmailField
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Serializer
from rest_framework.serializers import SerializerMethodField
from rest_framework.serializers import StringRelatedField
from rest_framework.serializers import ValidationError

from aura.core.models import PhysicianReferral
from aura.core.models import Review
from aura.mentalhealth.api.serializers import DisorderSerializer
from aura.users.models import Patient
from aura.users.models import Therapist
from aura.users.models import User


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


class TherapistSerializer(HyperlinkedModelSerializer[Therapist]):
    user = UserSerializer()
    specialties = StringRelatedField(many=True)

    class Meta:
        model = Therapist
        fields = [
            "url",
            "id",
            "user",
            "license_number",
            "years_of_experience",
            "specialties",
            "availability",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "url": {"view_name": "api:therapists-detail", "lookup_field": "pk"},
            "created_by": {"view_name": "api:users-detail"},
            "updated_by": {"view_name": "api:users-detail"},
        }


class PatientSerializer(HyperlinkedModelSerializer[Patient]):
    user = UserSerializer()
    disorders = DisorderSerializer(many=True)

    class Meta:
        model = Patient
        fields = [
            "url",
            "id",
            "user",
            "medical_record_number",
            "insurance_provider",
            "insurance_policy_number",
            "emergency_contact_name",
            "emergency_contact_phone",
            "allergies",
            "medical_conditions",
            "medical_history",
            "current_medications",
            "health_data",
            "preferences",
            "weight",
            "height",
            "disorders",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "url": {"view_name": "api:patients-detail", "lookup_field": "pk"},
            "created_by": {"view_name": "api:users-detail"},
            "updated_by": {"view_name": "api:users-detail"},
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
            except url_exceptions.NoReverseMatch as exc:
                msg = _("Unable to log in with provided credentials.")
                raise exceptions.ValidationError(msg) from exc
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
            msg = _("E-mail is not verified.")
            raise ValidationError(msg)

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


class TokenSerializer(ModelSerializer):
    """
    Serializer for Token model.
    """

    class Meta:
        model = Token
        fields = ("key",)


class UserDetailsSerializer(ModelSerializer):
    """
    User model w/o password
    """

    @staticmethod
    def validate_username(username):
        if "allauth.account" not in settings.INSTALLED_APPS:
            # We don't need to call the all-auth
            # username validator unless its installed
            return username

        from allauth.account.adapter import get_adapter

        return get_adapter().clean_username(username)

    class Meta:
        extra_fields = []
        if hasattr(User, "USERNAME_FIELD"):
            extra_fields.append(User.USERNAME_FIELD)
        if hasattr(User, "EMAIL_FIELD"):
            extra_fields.append(User.EMAIL_FIELD)
        if hasattr(User, "first_name"):
            extra_fields.append("first_name")
        if hasattr(User, "last_name"):
            extra_fields.append("last_name")
        model = User
        fields = ("pk", *extra_fields)
        read_only_fields = ("email",)


class JWTSerializer(Serializer):
    """
    Serializer for JWT authentication.
    """

    access = CharField()
    refresh = CharField()
    user = SerializerMethodField()

    def get_user(self, obj):
        """
        Required to allow using custom USER_DETAILS_SERIALIZER in
        JWTSerializer. Defining it here to avoid circular imports
        """
        return UserDetailsSerializer(obj["user"], context=self.context).data


class JWTSerializerWithExpiration(JWTSerializer):
    """
    Serializer for JWT authentication with expiration times.
    """

    access_expiration = DateTimeField()
    refresh_expiration = DateTimeField()


class PhysicianReferralSerializer(ModelSerializer):
    class Meta:
        model = PhysicianReferral
        fields = (
            "id",  # good practice to include the ID
            "first_name",
            "last_name",
            "work_email",
            "work_phone_number",
            "practice_name",
            "state_of_practice",
            "medical_group_aco",
            "practice_size",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "created_at",
            "updated_at",
        )  # important to make these fields read only

    def validate_work_phone_number(self, value):
        """
        Custom validation for the phone number.
        """
        phone_regex = RegexValidator(
            regex=r"^\+?1?\d{9,15}$",
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
        )
        phone_regex(value)  # This will raise a ValidationError if it fails
        return value

    def validate_state_of_practice(self, value):
        """
        Validate the state code (basic example).
        """
        # In a real application, you'd likely use a library or a comprehensive list.
        valid_states = [
            "WI",
            "WY",
            "DC",
        ]
        if value.upper() not in valid_states:
            msg = "Invalid state code."
            raise ValidationError(msg)
        return value.upper()  # Store in uppercase for consistency

    def validate(self, data):
        """
        Object-level validation (optional).  You can perform cross-field validation here.
        For instance, you might want to check if the email domain is allowed for the
        given medical group.  This is just a placeholder example.
        """
        # Example:  (This is highly simplified and would need a database lookup in reality)
        # if "example.com" not in data['work_email'] and data['medical_group_aco'] == "Example Medical Group":
        #     raise serializers.ValidationError("Email domain not allowed for this medical group.")
        return data
