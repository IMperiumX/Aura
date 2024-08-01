from rest_framework import serializers

from aura.mentalhealth.models import TherapySession


class TherapySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TherapySession
        fields = [
            "id",
            "status",
            "summary",
            "notes",
            "scheduled_at",
            "started_at",
            "ended_at",
            "created",
            "target_audience",
        ]
        read_only_fields = ["id", "created"]

    def validate(self, data):
        # Custom validation: Ensure started_at and ended_at are not set for pending sessions
        if data.get("status") == TherapySession.SessionStatus.PENDING:
            if data.get("started_at") or data.get("ended_at"):
                raise serializers.ValidationError(
                    "Started and ended times cannot be set for pending sessions."
                )
        return data
