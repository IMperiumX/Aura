from django.urls import path

from .views import video_call

app_name = "communication"

urlpatterns = [
    path("video_call/<str:room_name>/", video_call, name="video_call"),
]
