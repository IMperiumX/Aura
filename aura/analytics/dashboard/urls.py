"""
URL patterns for analytics dashboard web interface.
"""
from django.urls import path
from aura.analytics.dashboard.views import (
    DashboardView,
    DashboardDetailView,
    WidgetManagementView,
    AlertsView,
    SettingsView
)

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', DashboardView.as_view(), name='home'),
    path('dashboard/<slug:slug>/', DashboardDetailView.as_view(), name='detail'),

    # Management views
    path('widgets/', WidgetManagementView.as_view(), name='widgets'),
    path('alerts/', AlertsView.as_view(), name='alerts'),
    path('settings/', SettingsView.as_view(), name='settings'),
]
