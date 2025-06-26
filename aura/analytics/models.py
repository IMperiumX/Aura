"""
Analytics dashboard models for configuration, alerts, and aggregated data.
"""
import json
from typing import Dict, Any, List, Optional
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class DashboardWidget(models.Model):
    """
    Dashboard widget configuration.
    Stores widget layout, settings, and filters for customizable dashboards.
    """

    WIDGET_TYPES = [
        ('event_count', 'Event Count'),
        ('event_timeline', 'Event Timeline'),
        ('user_activity', 'User Activity'),
        ('system_health', 'System Health'),
        ('real_time_feed', 'Real-time Event Feed'),
        ('top_events', 'Top Events'),
        ('geographic_map', 'Geographic Distribution'),
        ('funnel_analysis', 'Conversion Funnel'),
        ('retention_chart', 'User Retention'),
        ('performance_metrics', 'Performance Metrics'),
    ]

    REFRESH_INTERVALS = [
        (5, '5 seconds'),
        (10, '10 seconds'),
        (30, '30 seconds'),
        (60, '1 minute'),
        (300, '5 minutes'),
        (900, '15 minutes'),
        (1800, '30 minutes'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    widget_type = models.CharField(max_length=50, choices=WIDGET_TYPES)

    # Layout and positioning
    dashboard_id = models.CharField(max_length=100, default='default')
    position_x = models.PositiveIntegerField(default=0)
    position_y = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(12)])
    height = models.PositiveIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(10)])

    # Widget configuration
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    refresh_interval = models.PositiveIntegerField(choices=REFRESH_INTERVALS, default=30)
    auto_refresh = models.BooleanField(default=True)

    # Filters and settings (JSON)
    filters = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)

    # Access control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_widgets')
    is_public = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_widgets')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'analytics_dashboard_widgets'
        ordering = ['position_y', 'position_x']
        indexes = [
            models.Index(fields=['dashboard_id', 'position_y', 'position_x']),
            models.Index(fields=['widget_type']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.name} ({self.widget_type})"

    def get_filters(self) -> Dict[str, Any]:
        """Get widget filters as dictionary."""
        return self.filters or {}

    def get_settings(self) -> Dict[str, Any]:
        """Get widget settings as dictionary."""
        return self.settings or {}

    def update_last_accessed(self):
        """Update last accessed timestamp."""
        self.last_accessed = timezone.now()
        self.save(update_fields=['last_accessed'])


class AlertRule(models.Model):
    """
    Analytics alert rules for monitoring thresholds and anomalies.
    """

    CONDITION_TYPES = [
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('percentage_change', 'Percentage Change'),
        ('anomaly_detection', 'Anomaly Detection'),
        ('missing_data', 'Missing Data'),
    ]

    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    NOTIFICATION_CHANNELS = [
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('webhook', 'Webhook'),
        ('sms', 'SMS'),
        ('dashboard', 'Dashboard Only'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Rule configuration
    event_type = models.CharField(max_length=100, blank=True, help_text="Event type to monitor (empty for all)")
    metric = models.CharField(max_length=100, help_text="Metric to monitor (e.g., 'count', 'avg_duration')")
    condition_type = models.CharField(max_length=50, choices=CONDITION_TYPES)
    threshold_value = models.FloatField()
    time_window = models.PositiveIntegerField(help_text="Time window in minutes")

    # Alert settings
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='warning')
    notification_channels = models.JSONField(default=list)
    cooldown_minutes = models.PositiveIntegerField(default=60, help_text="Minutes between alerts")

    # State tracking
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    trigger_count = models.PositiveIntegerField(default=0)

    # Access control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alert_rules')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_alert_rules'
        ordering = ['severity', '-created_at']
        indexes = [
            models.Index(fields=['event_type', 'is_active']),
            models.Index(fields=['severity', 'last_triggered']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.name} ({self.severity})"

    def can_trigger(self) -> bool:
        """Check if alert can trigger based on cooldown."""
        if not self.is_active:
            return False

        if not self.last_triggered:
            return True

        cooldown_delta = timezone.timedelta(minutes=self.cooldown_minutes)
        return timezone.now() - self.last_triggered > cooldown_delta

    def trigger_alert(self, current_value: float, context: Dict[str, Any] = None):
        """Trigger the alert and update state."""
        if not self.can_trigger():
            return False

        self.last_triggered = timezone.now()
        self.trigger_count += 1
        self.save(update_fields=['last_triggered', 'trigger_count'])

        # Create alert instance
        AlertInstance.objects.create(
            rule=self,
            triggered_value=current_value,
            context=context or {},
            severity=self.severity
        )

        return True


class AlertInstance(models.Model):
    """
    Individual alert instances when rules are triggered.
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    id = models.AutoField(primary_key=True)
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='instances')

    # Alert data
    triggered_value = models.FloatField()
    threshold_value = models.FloatField()
    severity = models.CharField(max_length=20, choices=AlertRule.SEVERITY_LEVELS)
    context = models.JSONField(default=dict, blank=True)

    # State management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_alert_instances'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', 'status', '-created_at']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.rule.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def acknowledge(self, user: User):
        """Acknowledge the alert."""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at'])

    def resolve(self):
        """Mark alert as resolved."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])


class MetricsSnapshot(models.Model):
    """
    Periodic snapshots of analytics metrics for historical analysis.
    """

    AGGREGATION_TYPES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    id = models.AutoField(primary_key=True)
    aggregation_type = models.CharField(max_length=20, choices=AGGREGATION_TYPES)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    # Metrics data (JSON)
    event_counts = models.JSONField(default=dict, help_text="Event type counts")
    user_metrics = models.JSONField(default=dict, help_text="User activity metrics")
    system_metrics = models.JSONField(default=dict, help_text="System performance metrics")
    custom_metrics = models.JSONField(default=dict, help_text="Custom business metrics")

    # Summary statistics
    total_events = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    top_event_type = models.CharField(max_length=100, blank=True)

    # Processing metadata
    processed_at = models.DateTimeField(auto_now_add=True)
    data_quality_score = models.FloatField(default=1.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    class Meta:
        db_table = 'analytics_metrics_snapshots'
        ordering = ['-period_start']
        unique_together = ['aggregation_type', 'period_start']
        indexes = [
            models.Index(fields=['aggregation_type', 'period_start']),
            models.Index(fields=['processed_at']),
            models.Index(fields=['total_events']),
        ]

    def __str__(self):
        return f"{self.aggregation_type} snapshot - {self.period_start.strftime('%Y-%m-%d %H:%M')}"

    def get_event_counts(self) -> Dict[str, int]:
        """Get event counts as dictionary."""
        return self.event_counts or {}

    def get_user_metrics(self) -> Dict[str, Any]:
        """Get user metrics as dictionary."""
        return self.user_metrics or {}

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics as dictionary."""
        return self.system_metrics or {}


class DashboardConfig(models.Model):
    """
    Dashboard configuration and layout settings.
    """

    THEMES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    # Layout settings
    theme = models.CharField(max_length=20, choices=THEMES, default='light')
    grid_columns = models.PositiveIntegerField(default=12, validators=[MinValueValidator(6), MaxValueValidator(24)])
    auto_refresh_enabled = models.BooleanField(default=True)
    default_refresh_interval = models.PositiveIntegerField(default=30)

    # Configuration (JSON)
    layout_config = models.JSONField(default=dict, blank=True)
    global_filters = models.JSONField(default=dict, blank=True)

    # Access control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboards')
    is_public = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_dashboards')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_dashboard_configs'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['created_by', 'is_public']),
        ]

    def __str__(self):
        return self.name

    def get_widgets(self):
        """Get all widgets for this dashboard."""
        return DashboardWidget.objects.filter(dashboard_id=self.slug)

    def get_layout_config(self) -> Dict[str, Any]:
        """Get layout configuration as dictionary."""
        return self.layout_config or {}

    def get_global_filters(self) -> Dict[str, Any]:
        """Get global filters as dictionary."""
        return self.global_filters or {}
