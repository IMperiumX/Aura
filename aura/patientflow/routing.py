from django.urls import path

from . import consumers

websocket_urlpatterns = [
    # Patient flow WebSocket for clinic-specific updates
    path(
        "ws/patientflow/clinic/<int:clinic_id>/",
        consumers.PatientFlowConsumer.as_asgi(),
    ),
    # User notifications WebSocket
    path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),
]
