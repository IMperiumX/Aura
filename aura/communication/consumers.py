import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import Message
from .models import Thread

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        user_id = text_data_json["user_id"]

        # Save message to database
        await self.save_message(user_id, self.room_name, message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": message, "user_id": user_id},
        )

    async def chat_message(self, event):
        message = event["message"]
        user_id = event["user_id"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message, "user_id": user_id}))

    @sync_to_async
    def save_message(self, user_id, thread_id, message):
        user = User.objects.get(id=user_id)
        thread = Thread.objects.get(id=thread_id)
        Message.objects.create(sender=user, thread=thread, text=message)
