from rest_framework import serializers

from aura.communication.models import Attachment
from aura.communication.models import Folder
from aura.communication.models import Message
from aura.communication.models import TherapySessionThread
from aura.communication.models import Thread


class ThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = [
            "id",
            "subject",
            "is_group",
            "is_active",
            "participants",
            "last_message",
        ]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "text", "read_at", "thread", "sender", "created", "modified"]


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "file", "message"]


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "name", "user", "threads"]


class TherapySessionThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TherapySessionThread
        fields = [
            "id",
            "session",
            "thread",
        ]
