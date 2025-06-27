from django.urls import path
from .api.views import AnalyticsQueryAPIView
from .api.views import LiveMetricsAPIView
from .api.views import SystemStatusAPIView
from .api.views import AlertInstanceViewSet
from .api.views import AlertRuleViewSet
from .api.views import DashboardConfigViewSet
from .api.views import DashboardWidgetViewSet

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"alert-instances", AlertInstanceViewSet, basename="alert-instances")
router.register(r"alert-rules", AlertRuleViewSet, basename="alert-rules")
router.register(r"dashboard-configs", DashboardConfigViewSet, basename="dashboard-configs")
router.register(r"dashboard-widgets", DashboardWidgetViewSet, basename="dashboard-widgets")

urlpatterns = [
    path("live-metrics/", LiveMetricsAPIView.as_view(), name="live-metrics"),
    path("analytics-query/", AnalyticsQueryAPIView.as_view(), name="analytics-query"),
    path("system-status/", SystemStatusAPIView.as_view(), name="system-status"),
]
urlpatterns += router.urls
