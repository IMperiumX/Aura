from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Patient flow WebSocket for clinic-specific updates
    re_path(r'ws/patientflow/clinic/(?P<clinic_id>\d+)/$', consumers.PatientFlowConsumer.as_asgi()),

    # User notifications WebSocket
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
