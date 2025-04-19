import json

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone

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



class ChatConsumer2(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.thread_group_name = f"thread_{self.thread_id}"
        self.user = self.scope["user"]

        # Verify user is a participant
        if not await self.is_participant():
            await self.close(code=4001)  # Custom close code for permission denied
            return

        await self.channel_layer.group_add(self.thread_group_name, self.channel_name)
        await self.accept()

        # Notify others about new connection
        await self.channel_layer.group_send(
            self.thread_group_name,
            {
                "type": "user_status",
                "user_id": self.user.id,
                "status": "online",
                "timestamp": str(timezone.now()),
            },
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.thread_group_name, self.channel_name
        )

        # Notify others about disconnection
        await self.channel_layer.group_send(
            self.thread_group_name,
            {
                "type": "user_status",
                "user_id": self.user.id,
                "status": "offline",
                "timestamp": str(timezone.now()),
            },
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "message")

            if message_type == "message":
                await self.handle_message(data)
            elif message_type == "typing":
                await self.handle_typing(data)
            elif message_type == "read_receipt":
                await self.handle_read_receipt(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))

    async def handle_message(self, data):
        message = data["message"]
        message_obj = await self.save_message(message)

        await self.channel_layer.group_send(
            self.thread_group_name,
            {
                "type": "chat_message",
                "message_id": message_obj.id,
                "sender_id": self.user.id,
                "text": message_obj.text,
                "timestamp": str(message_obj.created),
                "message_type": message_obj.message_type,
            },
        )

    async def handle_typing(self, data):
        await self.channel_layer.group_send(
            self.thread_group_name,
            {
                "type": "typing_indicator",
                "user_id": self.user.id,
                "is_typing": data.get("is_typing", False),
            },
        )

    async def handle_read_receipt(self, data):
        message_id = data["message_id"]
        await self.mark_message_read(message_id)

        await self.channel_layer.group_send(
            self.thread_group_name,
            {
                "type": "read_receipt",
                "message_id": message_id,
                "user_id": self.user.id,
                "timestamp": str(timezone.now()),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", **event}))

    async def typing_indicator(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "user_id": event["user_id"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    async def read_receipt(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "read_receipt",
                    "message_id": event["message_id"],
                    "user_id": event["user_id"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_status",
                    "user_id": event["user_id"],
                    "status": event["status"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    @database_sync_to_async
    def is_participant(self):
        return Thread.objects.filter(id=self.thread_id, participants=self.user).exists()

    @database_sync_to_async
    def save_message(self, text):
        thread = Thread.objects.get(id=self.thread_id)
        message = Message.objects.create(
            thread=thread, sender=self.user, text=text, message_type="text"
        )
        thread.last_message = message
        thread.save()
        return message

    @database_sync_to_async
    def mark_message_read(self, message_id):
        message = Message.objects.get(id=message_id)
        if not message.read_at:
            message.read_at = timezone.now()
            message.save()


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"video_call_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "video_call_message",
                "message": data,
            },
        )

    async def video_call_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))
