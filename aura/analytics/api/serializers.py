"""
Django REST Framework serializers for analytics dashboard API.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, Any

from aura.analytics.models import (
    DashboardWidget,
    AlertRule,
    AlertInstance,
    MetricsSnapshot,
    DashboardConfig
)

User = get_user_model()


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for dashboard widgets with layout and configuration."""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    last_accessed_relative = serializers.SerializerMethodField()

    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'name', 'widget_type', 'dashboard_id',
            'position_x', 'position_y', 'width', 'height',
            'title', 'description', 'refresh_interval', 'auto_refresh',
            'filters', 'settings', 'is_public',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'last_accessed', 'last_accessed_relative'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_last_accessed_relative(self, obj) -> str:
        """Get human-readable last access time."""
        if not obj.last_accessed:
            return "Never"

        now = timezone.now()
        diff = now - obj.last_accessed

        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() // 60)} minutes ago"
        elif diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() // 3600)} hours ago"
        else:
            return f"{diff.days} days ago"

    def validate_filters(self, value):
        """Validate widget filters."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filters must be a valid JSON object")

        # Add filter validation logic here
        allowed_filter_keys = [
            'event_type', 'user_id', 'start_date', 'end_date',
            'time_range', 'aggregation', 'group_by'
        ]

        for key in value.keys():
            if key not in allowed_filter_keys:
                raise serializers.ValidationError(f"Invalid filter key: {key}")

        return value

    def validate_settings(self, value):
        """Validate widget settings."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a valid JSON object")

        return value

    def validate(self, data):
        """Validate widget layout constraints."""
        # Check grid boundaries
        if data.get('position_x', 0) + data.get('width', 1) > 12:
            raise serializers.ValidationError("Widget extends beyond grid boundaries")

        # Validate refresh interval for widget type
        widget_type = data.get('widget_type')
        refresh_interval = data.get('refresh_interval', 30)

        if widget_type == 'real_time_feed' and refresh_interval > 30:
            raise serializers.ValidationError("Real-time widgets should refresh every 30 seconds or less")

        return data


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for alert rules with validation."""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    can_trigger = serializers.SerializerMethodField()
    recent_triggers = serializers.SerializerMethodField()

    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'event_type', 'metric',
            'condition_type', 'threshold_value', 'time_window',
            'severity', 'notification_channels', 'cooldown_minutes',
            'is_active', 'last_triggered', 'trigger_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'can_trigger', 'recent_triggers'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'last_triggered', 'trigger_count']

    def get_can_trigger(self, obj) -> bool:
        """Check if alert can currently trigger."""
        return obj.can_trigger()

    def get_recent_triggers(self, obj) -> int:
        """Get count of recent triggers (last 24 hours)."""
        cutoff = timezone.now() - timezone.timedelta(days=1)
        return obj.instances.filter(created_at__gte=cutoff).count()

    def validate_notification_channels(self, value):
        """Validate notification channels."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Notification channels must be a list")

        valid_channels = dict(AlertRule.NOTIFICATION_CHANNELS).keys()
        for channel in value:
            if channel not in valid_channels:
                raise serializers.ValidationError(f"Invalid notification channel: {channel}")

        return value

    def validate_threshold_value(self, value):
        """Validate threshold value based on condition type."""
        if value < 0 and self.initial_data.get('condition_type') in ['greater_than', 'less_than']:
            raise serializers.ValidationError("Threshold value cannot be negative for comparison conditions")

        return value

    def validate_time_window(self, value):
        """Validate time window."""
        if value < 1:
            raise serializers.ValidationError("Time window must be at least 1 minute")

        if value > 10080:  # 7 days
            raise serializers.ValidationError("Time window cannot exceed 7 days")

        return value


class AlertInstanceSerializer(serializers.ModelSerializer):
    """Serializer for alert instances."""

    rule_name = serializers.CharField(source='rule.name', read_only=True)
    rule_severity = serializers.CharField(source='rule.severity', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    time_since_triggered = serializers.SerializerMethodField()

    class Meta:
        model = AlertInstance
        fields = [
            'id', 'rule', 'rule_name', 'rule_severity',
            'triggered_value', 'threshold_value', 'severity', 'context',
            'status', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'resolved_at', 'created_at', 'updated_at',
            'time_since_triggered'
        ]
        read_only_fields = [
            'rule', 'triggered_value', 'threshold_value', 'severity',
            'created_at', 'updated_at'
        ]

    def get_time_since_triggered(self, obj) -> str:
        """Get human-readable time since triggered."""
        diff = timezone.now() - obj.created_at

        if diff.total_seconds() < 60:
            return f"{int(diff.total_seconds())} seconds ago"
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() // 60)} minutes ago"
        elif diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() // 3600)} hours ago"
        else:
            return f"{diff.days} days ago"


class MetricsSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for metrics snapshots."""

    period_duration = serializers.SerializerMethodField()
    top_events = serializers.SerializerMethodField()

    class Meta:
        model = MetricsSnapshot
        fields = [
            'id', 'aggregation_type', 'period_start', 'period_end',
            'event_counts', 'user_metrics', 'system_metrics', 'custom_metrics',
            'total_events', 'unique_users', 'top_event_type',
            'processed_at', 'data_quality_score',
            'period_duration', 'top_events'
        ]
        read_only_fields = ['processed_at']

    def get_period_duration(self, obj) -> str:
        """Get human-readable period duration."""
        duration = obj.period_end - obj.period_start

        if duration.total_seconds() < 3600:
            return f"{int(duration.total_seconds() // 60)} minutes"
        elif duration.total_seconds() < 86400:
            return f"{int(duration.total_seconds() // 3600)} hours"
        else:
            return f"{duration.days} days"

    def get_top_events(self, obj) -> list:
        """Get top 5 events by count."""
        event_counts = obj.get_event_counts()
        return sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:5]


class DashboardConfigSerializer(serializers.ModelSerializer):
    """Serializer for dashboard configurations."""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    widget_count = serializers.SerializerMethodField()

    class Meta:
        model = DashboardConfig
        fields = [
            'id', 'name', 'slug', 'description', 'theme',
            'grid_columns', 'auto_refresh_enabled', 'default_refresh_interval',
            'layout_config', 'global_filters', 'is_public',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'widget_count'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_widget_count(self, obj) -> int:
        """Get count of widgets in this dashboard."""
        return obj.get_widgets().count()

    def validate_slug(self, value):
        """Validate dashboard slug."""
        # Check for reserved slugs
        reserved_slugs = ['admin', 'api', 'health', 'status', 'metrics']
        if value.lower() in reserved_slugs:
            raise serializers.ValidationError(f"'{value}' is a reserved slug")

        return value

    def validate_grid_columns(self, value):
        """Validate grid columns."""
        if value not in [6, 8, 10, 12, 16, 20, 24]:
            raise serializers.ValidationError("Grid columns must be one of: 6, 8, 10, 12, 16, 20, 24")

        return value


class LiveMetricsSerializer(serializers.Serializer):
    """Serializer for live metrics data."""

    timestamp = serializers.DateTimeField()
    total_events = serializers.IntegerField()
    events_per_minute = serializers.FloatField()
    unique_users = serializers.IntegerField()
    top_event_types = serializers.ListField(child=serializers.DictField())
    system_health = serializers.DictField()
    backend_status = serializers.DictField()

    class Meta:
        fields = [
            'timestamp', 'total_events', 'events_per_minute',
            'unique_users', 'top_event_types', 'system_health',
            'backend_status'
        ]


class AnalyticsQuerySerializer(serializers.Serializer):
    """Serializer for analytics query parameters."""

    event_type = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    limit = serializers.IntegerField(default=100, min_value=1, max_value=1000)
    offset = serializers.IntegerField(default=0, min_value=0)
    aggregation = serializers.ChoiceField(
        choices=['hour', 'day', 'week', 'month'],
        required=False,
        allow_blank=True
    )
    group_by = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate query parameters."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Start date must be before end date")

        # Limit time range to prevent excessive queries
        if start_date and end_date:
            max_range = timezone.timedelta(days=90)  # 90 days max
            if end_date - start_date > max_range:
                raise serializers.ValidationError("Date range cannot exceed 90 days")

        return data


class SystemStatusSerializer(serializers.Serializer):
    """Serializer for system status and health information."""

    timestamp = serializers.DateTimeField()
    environment = serializers.CharField()
    production_ready = serializers.BooleanField()
    backend_status = serializers.DictField()
    active_alerts = serializers.IntegerField()
    widget_count = serializers.IntegerField()
    system_health = serializers.DictField()

    class Meta:
        fields = [
            'timestamp', 'environment', 'production_ready',
            'backend_status', 'active_alerts', 'widget_count',
            'system_health'
        ]
