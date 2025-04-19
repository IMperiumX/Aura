from django.contrib.auth import get_user_model
from django.core.files import File
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from aura.communication import THREAD_MIN_PARTICIPANTS
from aura.communication.models import Attachment
from aura.communication.models import Folder
from aura.communication.models import Message
from aura.communication.models import TherapySessionThread
from aura.communication.models import Thread
from aura.users.api.serializers import UserSerializer

User = get_user_model()


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ThreadSerializer(DynamicFieldsModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = [
            "id",
            "subject",
            "is_group",
            "is_active",
            "participants",
            "last_message",
            "unread_count",
        ]

    def create(self, validated_data):
        participant_ids = validated_data.pop("participant_ids")
        request_user = self.context["request"].user

        # Add the request user to participants if not already included
        if request_user.id not in participant_ids:
            participant_ids.append(request_user.id)

        participants = User.objects.filter(id__in=participant_ids).distinct()

        if len(participants) < THREAD_MIN_PARTICIPANTS:
            msg = f"A thread must have at least {THREAD_MIN_PARTICIPANTS} participants"
            raise serializers.ValidationError(msg)

        thread = Thread.objects.create(**validated_data)
        thread.participants.set(participants)

        return thread

    @extend_schema_field(serializers.DictField)
    def get_last_message(self, obj):
        if obj.last_message:
            return {
                "id": obj.last_message.id,
                "text": obj.last_message.text[:50],  # Preview of the message
                "sender": obj.last_message.sender.username,
                "created": obj.last_message.created,
            }
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_unread_count(self, obj):
        user = self.context["request"].user
        return obj.messages.filter(read_at__isnull=True).exclude(sender=user).count()


class MessageSerializer(DynamicFieldsModelSerializer):
    sender = UserSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "text",
            "read_at",
            "thread",
            "sender",
            "created",
            "modified",
            "attachments",
        ]
        read_only_fields = ["created", "modified"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_attachments(self, obj):
        return [
            {"id": att.id, "name": att.name, "size": att.size}
            for att in obj.attachments.all()
        ]

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "name",
            "file",
            "content_type",
            "size",
            "created",
            "download_url",
        ]

    @extend_schema_field(serializers.FileField)
    def get_file(self, obj):
        if obj.file:
            return File(obj.file).name
        return None

    @extend_schema_field(serializers.URLField)
    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return None


class FolderSerializer(serializers.ModelSerializer):
    threads = ThreadSerializer(many=True, read_only=True)

    class Meta:
        model = Folder
        fields = ["id", "name", "user", "threads"]


class TherapySessionThreadSerializer(ThreadSerializer):
    class Meta(ThreadSerializer.Meta):
        model = TherapySessionThread
        fields = [*ThreadSerializer.Meta.fields, "session"]
