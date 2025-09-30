from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from aura.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    """Serializer for User objects"""

    class Meta:
        model = User
        fields = ("id", "email", "url", "first_name", "last_name", "user_type", "is_verified", "profile_completed")
        read_only_fields = ("id", "is_verified", "profile_completed")
        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})
    terms_accepted = serializers.BooleanField(write_only=True)
    privacy_policy_accepted = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "password_confirm",
            "user_type",
            "first_name",
            "last_name",
            "terms_accepted",
            "privacy_policy_accepted",
        )

    def validate_password(self, value):
        """Validate password using Django's password validators"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate_terms_accepted(self, value):
        """Ensure terms are accepted"""
        if not value:
            raise serializers.ValidationError("Terms of service must be accepted.")
        return value

    def validate_privacy_policy_accepted(self, value):
        """Ensure privacy policy is accepted"""
        if not value:
            raise serializers.ValidationError("Privacy policy must be accepted.")
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Password confirmation does not match.")
        return attrs

    def create(self, validated_data):
        """Create new user"""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        """Validate user credentials"""
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                attrs["user"] = user
            else:
                raise serializers.ValidationError("Invalid email or password.")
        else:
            raise serializers.ValidationError("Email and password are required.")

        return attrs
