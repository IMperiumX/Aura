from rest_framework import serializers

from aura.users.models import Therapist
from aura.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }


class TherapistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Therapist
        exclude = ["embedding"]
