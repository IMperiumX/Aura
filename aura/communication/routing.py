from django.urls import re_path

from aura.communication.consumers import ChatConsumer
from aura.communication.consumers import VideoCallConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/video_call/(?P<room_name>\w+)/$", VideoCallConsumer.as_asgi()),
]
