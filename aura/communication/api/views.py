from rest_framework import viewsets

from aura.communication.api.serializers import MessageSerializer
from aura.communication.api.serializers import ThreadSerializer
from aura.communication.models import Message
from aura.communication.models import Thread


class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
