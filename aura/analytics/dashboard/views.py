"""
Django views for analytics dashboard web interface.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Q
from django.http import JsonResponse

from aura.analytics.models import (
    DashboardConfig,
    DashboardWidget,
    AlertRule,
    AlertInstance
)
from aura.analytics import get_analytics_config


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view."""

    template_name = 'analytics/dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's dashboards
        user_dashboards = DashboardConfig.objects.filter(
            Q(created_by=self.request.user) |
            Q(is_public=True) |
            Q(allowed_users=self.request.user)
        ).distinct()[:5]  # Show top 5

        # Get default dashboard or create one
        default_dashboard = user_dashboards.filter(slug='default').first()
        if not default_dashboard and user_dashboards.exists():
            default_dashboard = user_dashboards.first()

        # Get widgets for default dashboard
        widgets = []
        if default_dashboard:
            widgets = DashboardWidget.objects.filter(
                dashboard_id=default_dashboard.slug,
                created_by=self.request.user
            ).order_by('position_y', 'position_x')

        # Get recent alerts
        recent_alerts = AlertInstance.objects.filter(
            rule__created_by=self.request.user,
            status='active'
        ).order_by('-created_at')[:5]

        # Get analytics config
        try:
            config = get_analytics_config()
            analytics_status = {
                'environment': config.environment,
                'production_ready': config.is_production_ready(),
                'backend_count': len(config.get_backends_list())
            }
        except Exception:
            analytics_status = {
                'environment': 'unknown',
                'production_ready': False,
                'backend_count': 0
            }

        context.update({
            'dashboards': user_dashboards,
            'default_dashboard': default_dashboard,
            'widgets': widgets,
            'recent_alerts': recent_alerts,
            'analytics_status': analytics_status,
        })

        return context


class DashboardDetailView(LoginRequiredMixin, TemplateView):
    """Detailed dashboard view for a specific dashboard."""

    template_name = 'analytics/dashboard/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get dashboard
        dashboard = get_object_or_404(
            DashboardConfig,
            slug=kwargs['slug']
        )

        # Check permissions
        if not (dashboard.created_by == self.request.user or
                dashboard.is_public or
                dashboard.allowed_users.filter(id=self.request.user.id).exists()):
            raise PermissionError("Access denied to this dashboard")

        # Get widgets
        widgets = DashboardWidget.objects.filter(
            dashboard_id=dashboard.slug
        ).order_by('position_y', 'position_x')

        context.update({
            'dashboard': dashboard,
            'widgets': widgets,
        })

        return context


class WidgetManagementView(LoginRequiredMixin, TemplateView):
    """Widget management interface."""

    template_name = 'analytics/dashboard/widgets.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's widgets
        widgets = DashboardWidget.objects.filter(
            created_by=self.request.user
        ).order_by('-updated_at')

        # Get available widget types
        widget_types = DashboardWidget.WIDGET_TYPES

        # Get user's dashboards
        dashboards = DashboardConfig.objects.filter(
            Q(created_by=self.request.user) |
            Q(is_public=True) |
            Q(allowed_users=self.request.user)
        ).distinct()

        context.update({
            'widgets': widgets,
            'widget_types': widget_types,
            'dashboards': dashboards,
        })

        return context


class AlertsView(LoginRequiredMixin, TemplateView):
    """Alerts management interface."""

    template_name = 'analytics/dashboard/alerts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's alert rules
        alert_rules = AlertRule.objects.filter(
            created_by=self.request.user
        ).order_by('-created_at')

        # Get recent alert instances
        alert_instances = AlertInstance.objects.filter(
            rule__created_by=self.request.user
        ).order_by('-created_at')[:20]

        # Get alert statistics
        active_alerts = alert_instances.filter(status='active').count()
        total_rules = alert_rules.count()
        active_rules = alert_rules.filter(is_active=True).count()

        context.update({
            'alert_rules': alert_rules,
            'alert_instances': alert_instances,
            'stats': {
                'active_alerts': active_alerts,
                'total_rules': total_rules,
                'active_rules': active_rules,
            },
            'condition_types': AlertRule.CONDITION_TYPES,
            'severity_levels': AlertRule.SEVERITY_LEVELS,
            'notification_channels': AlertRule.NOTIFICATION_CHANNELS,
        })

        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Analytics settings interface."""

    template_name = 'analytics/dashboard/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get analytics configuration
        try:
            config = get_analytics_config()

            config_info = {
                'environment': config.environment,
                'production_ready': config.is_production_ready(),
                'primary_backend': config.get_primary_backend(),
                'backend_count': len(config.get_backends_list()),
                'backends': config.get_backends_list(),
            }

            # Check missing requirements
            missing_requirements = config.get_missing_requirements()

        except Exception as e:
            config_info = {'error': str(e)}
            missing_requirements = []

        # Get user statistics
        user_stats = {
            'dashboards_created': DashboardConfig.objects.filter(created_by=self.request.user).count(),
            'widgets_created': DashboardWidget.objects.filter(created_by=self.request.user).count(),
            'alert_rules': AlertRule.objects.filter(created_by=self.request.user).count(),
        }

        context.update({
            'config_info': config_info,
            'missing_requirements': missing_requirements,
            'user_stats': user_stats,
        })

        return context
