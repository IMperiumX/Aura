"""
URL patterns for analytics dashboard web interface.
"""

from django.urls import path

from aura.analytics.dashboard.views import AlertsView
from aura.analytics.dashboard.views import DashboardDetailView
from aura.analytics.dashboard.views import DashboardView
from aura.analytics.dashboard.views import SettingsView
from aura.analytics.dashboard.views import WidgetManagementView

app_name = "dashboard"

urlpatterns = [
    # Main dashboard
    path("", DashboardView.as_view(), name="home"),
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="detail"),
    # Management views
    path("widgets/", WidgetManagementView.as_view(), name="widgets"),
    path("alerts/", AlertsView.as_view(), name="alerts"),
    path("settings/", SettingsView.as_view(), name="settings"),
]
