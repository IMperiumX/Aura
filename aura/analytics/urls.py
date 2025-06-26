from django.urls import path
from .api.views import AnalyticsQueryAPIView
from .api.views import LiveMetricsAPIView
from .api.views import SystemStatusAPIView


urlpatterns = [
    path("live-metrics/", LiveMetricsAPIView.as_view(), name="live-metrics"),
    path("analytics-query/", AnalyticsQueryAPIView.as_view(), name="analytics-query"),
    path("system-status/", SystemStatusAPIView.as_view(), name="system-status"),
]
