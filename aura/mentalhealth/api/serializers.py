from django.contrib.auth import get_user_model
from rest_framework import serializers

from aura.mentalhealth.models import ChatbotInteraction, TherapyApproach, TherapySession

User = get_user_model()


class TherapySessionSerializer(serializers.HyperlinkedModelSerializer):
    # TODO: update to profile related detials
    therapist = serializers.HyperlinkedRelatedField(
        view_name="user-detail", read_only=True
    )
    patient = serializers.HyperlinkedRelatedField(
        view_name="user-detail", read_only=True
    )

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
            "therapist",
            "patient",
            "target_audience",
        ]
        read_only_fields = [
            "id",
            "created",
        ]  # XXX: add `status` and make sure that test passes

    def validate(self, data):
        # Custom validation: Ensure started_at and ended_at are not set for pending sessions
        if data.get("status") == TherapySession.SessionStatus.PENDING:
            if data.get("started_at") or data.get("ended_at"):
                raise serializers.ValidationError(
                    "Started and ended times cannot be set for pending sessions."
                )
        return data


class TherapyApproachSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TherapyApproach
        fields = ["url", "id", "name", "description"]


class ChatbotInteractionSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.HyperlinkedRelatedField(view_name="user-detail", read_only=True)

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
