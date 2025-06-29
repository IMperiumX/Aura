# Generated by Django 5.1.1 on 2025-06-26 23:17

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AlertRule",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "event_type",
                    models.CharField(
                        blank=True,
                        help_text="Event type to monitor (empty for all)",
                        max_length=100,
                    ),
                ),
                (
                    "metric",
                    models.CharField(
                        help_text="Metric to monitor (e.g., 'count', 'avg_duration')",
                        max_length=100,
                    ),
                ),
                (
                    "condition_type",
                    models.CharField(
                        choices=[
                            ("greater_than", "Greater Than"),
                            ("less_than", "Less Than"),
                            ("equals", "Equals"),
                            ("not_equals", "Not Equals"),
                            ("percentage_change", "Percentage Change"),
                            ("anomaly_detection", "Anomaly Detection"),
                            ("missing_data", "Missing Data"),
                        ],
                        max_length=50,
                    ),
                ),
                ("threshold_value", models.FloatField()),
                (
                    "time_window",
                    models.PositiveIntegerField(help_text="Time window in minutes"),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("critical", "Critical"),
                        ],
                        default="warning",
                        max_length=20,
                    ),
                ),
                ("notification_channels", models.JSONField(default=list)),
                (
                    "cooldown_minutes",
                    models.PositiveIntegerField(
                        default=60, help_text="Minutes between alerts"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("last_triggered", models.DateTimeField(blank=True, null=True)),
                ("trigger_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alert_rules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "analytics_alert_rules",
                "ordering": ["severity", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AlertInstance",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("triggered_value", models.FloatField()),
                ("threshold_value", models.FloatField()),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("critical", "Critical"),
                        ],
                        max_length=20,
                    ),
                ),
                ("context", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("acknowledged", "Acknowledged"),
                            ("resolved", "Resolved"),
                            ("dismissed", "Dismissed"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "acknowledged_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "rule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="instances",
                        to="analytics.alertrule",
                    ),
                ),
            ],
            options={
                "db_table": "analytics_alert_instances",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DashboardConfig",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "theme",
                    models.CharField(
                        choices=[
                            ("light", "Light"),
                            ("dark", "Dark"),
                            ("auto", "Auto"),
                        ],
                        default="light",
                        max_length=20,
                    ),
                ),
                (
                    "grid_columns",
                    models.PositiveIntegerField(
                        default=12,
                        validators=[
                            django.core.validators.MinValueValidator(6),
                            django.core.validators.MaxValueValidator(24),
                        ],
                    ),
                ),
                ("auto_refresh_enabled", models.BooleanField(default=True)),
                ("default_refresh_interval", models.PositiveIntegerField(default=30)),
                ("layout_config", models.JSONField(blank=True, default=dict)),
                ("global_filters", models.JSONField(blank=True, default=dict)),
                ("is_public", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "allowed_users",
                    models.ManyToManyField(
                        blank=True,
                        related_name="accessible_dashboards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dashboards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "analytics_dashboard_configs",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="DashboardWidget",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                (
                    "widget_type",
                    models.CharField(
                        choices=[
                            ("event_count", "Event Count"),
                            ("event_timeline", "Event Timeline"),
                            ("user_activity", "User Activity"),
                            ("system_health", "System Health"),
                            ("real_time_feed", "Real-time Event Feed"),
                            ("top_events", "Top Events"),
                            ("geographic_map", "Geographic Distribution"),
                            ("funnel_analysis", "Conversion Funnel"),
                            ("retention_chart", "User Retention"),
                            ("performance_metrics", "Performance Metrics"),
                        ],
                        max_length=50,
                    ),
                ),
                ("dashboard_id", models.CharField(default="default", max_length=100)),
                ("position_x", models.PositiveIntegerField(default=0)),
                ("position_y", models.PositiveIntegerField(default=0)),
                (
                    "width",
                    models.PositiveIntegerField(
                        default=4,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ],
                    ),
                ),
                (
                    "height",
                    models.PositiveIntegerField(
                        default=3,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(10),
                        ],
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "refresh_interval",
                    models.PositiveIntegerField(
                        choices=[
                            (5, "5 seconds"),
                            (10, "10 seconds"),
                            (30, "30 seconds"),
                            (60, "1 minute"),
                            (300, "5 minutes"),
                            (900, "15 minutes"),
                            (1800, "30 minutes"),
                        ],
                        default=30,
                    ),
                ),
                ("auto_refresh", models.BooleanField(default=True)),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("settings", models.JSONField(blank=True, default=dict)),
                ("is_public", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_accessed", models.DateTimeField(blank=True, null=True)),
                (
                    "allowed_users",
                    models.ManyToManyField(
                        blank=True,
                        related_name="accessible_widgets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dashboard_widgets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "analytics_dashboard_widgets",
                "ordering": ["position_y", "position_x"],
            },
        ),
        migrations.CreateModel(
            name="MetricsSnapshot",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "aggregation_type",
                    models.CharField(
                        choices=[
                            ("hourly", "Hourly"),
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                        ],
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateTimeField()),
                ("period_end", models.DateTimeField()),
                (
                    "event_counts",
                    models.JSONField(default=dict, help_text="Event type counts"),
                ),
                (
                    "user_metrics",
                    models.JSONField(default=dict, help_text="User activity metrics"),
                ),
                (
                    "system_metrics",
                    models.JSONField(
                        default=dict, help_text="System performance metrics"
                    ),
                ),
                (
                    "custom_metrics",
                    models.JSONField(default=dict, help_text="Custom business metrics"),
                ),
                ("total_events", models.PositiveIntegerField(default=0)),
                ("unique_users", models.PositiveIntegerField(default=0)),
                ("top_event_type", models.CharField(blank=True, max_length=100)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "data_quality_score",
                    models.FloatField(
                        default=1.0,
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(1.0),
                        ],
                    ),
                ),
            ],
            options={
                "db_table": "analytics_metrics_snapshots",
                "ordering": ["-period_start"],
                "indexes": [
                    models.Index(
                        fields=["aggregation_type", "period_start"],
                        name="analytics_m_aggrega_c09b35_idx",
                    ),
                    models.Index(
                        fields=["processed_at"], name="analytics_m_process_befaf8_idx"
                    ),
                    models.Index(
                        fields=["total_events"], name="analytics_m_total_e_3d18c4_idx"
                    ),
                ],
                "unique_together": {("aggregation_type", "period_start")},
            },
        ),
        migrations.AddIndex(
            model_name="alertrule",
            index=models.Index(
                fields=["event_type", "is_active"],
                name="analytics_a_event_t_3a40fe_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="alertrule",
            index=models.Index(
                fields=["severity", "last_triggered"],
                name="analytics_a_severit_96c31f_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="alertrule",
            index=models.Index(
                fields=["created_by"], name="analytics_a_created_765189_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="alertinstance",
            index=models.Index(
                fields=["rule", "status", "-created_at"],
                name="analytics_a_rule_id_096ee0_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="alertinstance",
            index=models.Index(
                fields=["severity", "status"], name="analytics_a_severit_ada8b2_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="alertinstance",
            index=models.Index(
                fields=["created_at"], name="analytics_a_created_5fb432_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dashboardconfig",
            index=models.Index(fields=["slug"], name="analytics_d_slug_28e1dd_idx"),
        ),
        migrations.AddIndex(
            model_name="dashboardconfig",
            index=models.Index(
                fields=["created_by", "is_public"],
                name="analytics_d_created_0ec7b9_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dashboardwidget",
            index=models.Index(
                fields=["dashboard_id", "position_y", "position_x"],
                name="analytics_d_dashboa_21bdd7_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dashboardwidget",
            index=models.Index(
                fields=["widget_type"], name="analytics_d_widget__13737a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dashboardwidget",
            index=models.Index(
                fields=["created_by"], name="analytics_d_created_658155_idx"
            ),
        ),
    ]
