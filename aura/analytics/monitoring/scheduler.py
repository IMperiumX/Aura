"""
Monitoring scheduler for automated analytics monitoring.
Uses Celery for background task execution with configurable intervals.
"""

import logging
from datetime import datetime
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from aura.analytics.models import MetricsSnapshot
from aura.analytics.monitoring.engine import MonitoringEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="analytics.monitoring.run_monitoring_cycle")
def run_monitoring_cycle_task(self):
    """
    Celery task to run monitoring cycle.
    """
    try:
        logger.info("Starting analytics monitoring cycle")

        engine = MonitoringEngine()
        results = engine.run_monitoring_cycle()

        # Store results in cache for status reporting
        cache.set("monitoring:last_results", results, 3600)

        logger.info(f"Monitoring cycle completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Monitoring cycle failed: {e}")
        # Store error in cache
        error_results = {
            "timestamp": timezone.now(),
            "error": str(e),
            "status": "failed",
        }
        cache.set("monitoring:last_results", error_results, 3600)
        raise


@shared_task(bind=True, name="analytics.monitoring.generate_metrics_snapshot")
def generate_metrics_snapshot_task(self, aggregation_type="hourly"):
    """
    Celery task to generate metrics snapshots for historical analysis.
    """
    try:
        logger.info(f"Generating {aggregation_type} metrics snapshot")

        # Calculate time period
        now = timezone.now()

        if aggregation_type == "hourly":
            # Previous hour
            period_end = now.replace(minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(hours=1)
        elif aggregation_type == "daily":
            # Previous day
            period_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_start = period_end - timedelta(days=1)
        elif aggregation_type == "weekly":
            # Previous week (Monday to Sunday)
            days_since_monday = now.weekday()
            period_end = now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            ) - timedelta(days=days_since_monday)
            period_start = period_end - timedelta(weeks=1)
        elif aggregation_type == "monthly":
            # Previous month
            period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_start = (period_end - timedelta(days=1)).replace(day=1)
        else:
            raise ValueError(f"Unknown aggregation type: {aggregation_type}")

        # Check if snapshot already exists
        existing = MetricsSnapshot.objects.filter(
            aggregation_type=aggregation_type,
            period_start=period_start,
        ).first()

        if existing:
            logger.info(
                f"Snapshot for {aggregation_type} {period_start} already exists",
            )
            return {
                "status": "exists",
                "snapshot_id": existing.id,
                "period_start": period_start,
                "period_end": period_end,
            }

        # Generate snapshot
        snapshot = create_metrics_snapshot(period_start, period_end, aggregation_type)

        logger.info(
            f"Generated {aggregation_type} snapshot {snapshot.id} for period {period_start} to {period_end}",
        )

        return {
            "status": "created",
            "snapshot_id": snapshot.id,
            "period_start": period_start,
            "period_end": period_end,
            "total_events": snapshot.total_events,
            "unique_users": snapshot.unique_users,
        }

    except Exception as e:
        logger.error(f"Failed to generate {aggregation_type} metrics snapshot: {e}")
        raise


def create_metrics_snapshot(
    period_start: datetime,
    period_end: datetime,
    aggregation_type: str,
) -> MetricsSnapshot:
    """Create a metrics snapshot for the given period."""
    from aura.analytics import get_events

    # Get events for the period
    events = get_events(
        start_time=period_start,
        end_time=period_end,
        limit=50000,  # Increased limit for aggregation
    )

    # Aggregate event counts by type
    event_counts = {}
    user_ids = set()

    for event in events:
        event_type = event.get("event_type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

        user_id = event.get("user_id")
        if user_id:
            user_ids.add(user_id)

    # Calculate top event type
    top_event_type = ""
    if event_counts:
        top_event_type = max(event_counts.items(), key=lambda x: x[1])[0]

    # Create user metrics
    user_metrics = {
        "unique_users": len(user_ids),
        "avg_events_per_user": len(events) / len(user_ids) if user_ids else 0,
        "total_sessions": len(user_ids),  # Simplified - would need session tracking
    }

    # Create system metrics
    system_metrics = {
        "events_per_hour": len(events)
        / max(1, (period_end - period_start).total_seconds() / 3600),
        "peak_hour": "N/A",  # Would need hourly breakdown
        "data_quality_score": 1.0,  # Simplified calculation
    }

    # Custom business metrics
    custom_metrics = {
        "patient_events": sum(
            1 for event in events if "patient" in event.get("event_type", "").lower()
        ),
        "therapy_events": sum(
            1 for event in events if "therapy" in event.get("event_type", "").lower()
        ),
        "communication_events": sum(
            1 for event in events if "message" in event.get("event_type", "").lower()
        ),
        "error_events": sum(
            1 for event in events if "error" in event.get("event_type", "").lower()
        ),
    }

    # Create snapshot
    snapshot = MetricsSnapshot.objects.create(
        aggregation_type=aggregation_type,
        period_start=period_start,
        period_end=period_end,
        event_counts=event_counts,
        user_metrics=user_metrics,
        system_metrics=system_metrics,
        custom_metrics=custom_metrics,
        total_events=len(events),
        unique_users=len(user_ids),
        top_event_type=top_event_type,
        data_quality_score=1.0,
    )

    return snapshot


@shared_task(bind=True, name="analytics.monitoring.cleanup_old_data")
def cleanup_old_data_task(self, days_to_keep=90):
    """
    Celery task to clean up old monitoring data.
    """
    try:
        logger.info(f"Cleaning up monitoring data older than {days_to_keep} days")

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Clean up old alert instances
        old_alerts = AlertInstance.objects.filter(
            created_at__lt=cutoff_date,
            status__in=["resolved", "dismissed"],
        )
        alert_count = old_alerts.count()
        old_alerts.delete()

        # Clean up old metrics snapshots (keep daily and weekly longer)
        old_hourly_snapshots = MetricsSnapshot.objects.filter(
            aggregation_type="hourly",
            processed_at__lt=cutoff_date,
        )
        hourly_count = old_hourly_snapshots.count()
        old_hourly_snapshots.delete()

        # Keep daily snapshots for longer (1 year)
        old_daily_snapshots = MetricsSnapshot.objects.filter(
            aggregation_type="daily",
            processed_at__lt=timezone.now() - timedelta(days=365),
        )
        daily_count = old_daily_snapshots.count()
        old_daily_snapshots.delete()

        results = {
            "alert_instances_deleted": alert_count,
            "hourly_snapshots_deleted": hourly_count,
            "daily_snapshots_deleted": daily_count,
            "cleanup_date": cutoff_date,
        }

        logger.info(f"Cleanup completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        raise


class MonitoringScheduler:
    """
    Manages scheduling of monitoring tasks.
    """

    @staticmethod
    def start_monitoring():
        """Start monitoring with default schedule."""
        from django_celery_beat.models import IntervalSchedule
        from django_celery_beat.models import PeriodicTask

        # Create schedules
        monitoring_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,  # Every 5 minutes
            period=IntervalSchedule.MINUTES,
        )

        hourly_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.HOURS,
        )

        daily_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.DAYS,
        )

        # Create or update monitoring task
        PeriodicTask.objects.update_or_create(
            name="analytics-monitoring-cycle",
            defaults={
                "task": "analytics.monitoring.run_monitoring_cycle",
                "interval": monitoring_schedule,
                "enabled": True,
            },
        )

        # Create or update hourly metrics task
        PeriodicTask.objects.update_or_create(
            name="analytics-hourly-metrics",
            defaults={
                "task": "analytics.monitoring.generate_metrics_snapshot",
                "interval": hourly_schedule,
                "kwargs": '{"aggregation_type": "hourly"}',
                "enabled": True,
            },
        )

        # Create or update daily metrics task
        PeriodicTask.objects.update_or_create(
            name="analytics-daily-metrics",
            defaults={
                "task": "analytics.monitoring.generate_metrics_snapshot",
                "interval": daily_schedule,
                "kwargs": '{"aggregation_type": "daily"}',
                "enabled": True,
            },
        )

        # Create or update cleanup task (weekly)
        weekly_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=7,
            period=IntervalSchedule.DAYS,
        )

        PeriodicTask.objects.update_or_create(
            name="analytics-data-cleanup",
            defaults={
                "task": "analytics.monitoring.cleanup_old_data",
                "interval": weekly_schedule,
                "kwargs": '{"days_to_keep": 90}',
                "enabled": True,
            },
        )

        logger.info("Monitoring scheduler started with default tasks")

    @staticmethod
    def stop_monitoring():
        """Stop all monitoring tasks."""
        from django_celery_beat.models import PeriodicTask

        task_names = [
            "analytics-monitoring-cycle",
            "analytics-hourly-metrics",
            "analytics-daily-metrics",
            "analytics-data-cleanup",
        ]

        for task_name in task_names:
            try:
                task = PeriodicTask.objects.get(name=task_name)
                task.enabled = False
                task.save()
                logger.info(f"Disabled monitoring task: {task_name}")
            except PeriodicTask.DoesNotExist:
                logger.warning(f"Monitoring task not found: {task_name}")

        logger.info("Monitoring scheduler stopped")

    @staticmethod
    def get_monitoring_status():
        """Get status of all monitoring tasks."""
        from django_celery_beat.models import PeriodicTask

        status = {
            "tasks": {},
            "last_results": cache.get("monitoring:last_results"),
            "monitoring_stats": cache.get("monitoring:stats", {}),
        }

        task_names = [
            "analytics-monitoring-cycle",
            "analytics-hourly-metrics",
            "analytics-daily-metrics",
            "analytics-data-cleanup",
        ]

        for task_name in task_names:
            try:
                task = PeriodicTask.objects.get(name=task_name)
                status["tasks"][task_name] = {
                    "enabled": task.enabled,
                    "last_run_at": task.last_run_at,
                    "total_run_count": task.total_run_count,
                    "interval": str(task.interval) if task.interval else None,
                }
            except PeriodicTask.DoesNotExist:
                status["tasks"][task_name] = {"enabled": False, "exists": False}

        return status
