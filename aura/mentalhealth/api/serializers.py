from django.contrib.auth import get_user_model
from rest_framework import serializers

from aura.mentalhealth.models import ChatbotInteraction
from aura.mentalhealth.models import TherapyApproach
from aura.mentalhealth.models import TherapySession

User = get_user_model()


class TherapySessionSerializer(serializers.HyperlinkedModelSerializer):
    # TODO: update to profile related detials
    therapist = serializers.HyperlinkedRelatedField(
        view_name="api:users-detail",
        read_only=True,
    )
    patient = serializers.HyperlinkedRelatedField(
        view_name="api:users-detail",
        read_only=True,
    )

    recurrences_humanized = serializers.SerializerMethodField()
    recurrences_dates = serializers.SerializerMethodField()

    class Meta:
        model = TherapySession
        fields = [
            "url",
            "id",
            "session_type",
            "status",
            "summary",
            "notes",
            "scheduled_at",
            "started_at",
            "ended_at",
            "created",
            "recurrences",  # custom serialzier
            "recurrences_humanized",
            "recurrences_dates",
            "therapist",
            "patient",
            "target_audience",
        ]
        read_only_fields = [
            "id",
            "created",
        ]  # XXX: add `status` and make sure that test passes
        extra_kwargs = {
            "url": {"view_name": "api:sessions-detail", "lookup_field": "pk"},
        }

    def validate(self, data):
        # Custom validation: Ensure started_at and ended_at are not set for pending sessions
        if data.get("status") == TherapySession.SessionStatus.PENDING:
            if data.get("started_at") or data.get("ended_at"):
                msg = "Started and ended times cannot be set for pending sessions."
                raise serializers.ValidationError(msg)
        return data

    def get_recurrences_humanized(self, obj):
        return [rule.to_text() for rule in obj.recurrences.rrules]

    def get_recurrences_dates(self, obj):
        return list(obj.recurrences.occurrences())


class TherapyApproachSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TherapyApproach
        fields = ["url", "id", "name", "description"]

        extra_kwargs = {
            "url": {"view_name": "api:approaches-detail", "lookup_field": "pk"},
        }


class ChatbotInteractionSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.HyperlinkedRelatedField(view_name="users-detail", read_only=True)

    class Meta:
        model = ChatbotInteraction
        fields = [
            "url",
            "id",
            "message",
            "response",
            "conversation_log",
            "interaction_date",
            "created",
            "user",
        ]
        extra_kwargs = {
            "url": {
                "view_name": "api:chatbot-interactions-detail",
                "lookup_field": "pk",
            },
        }
