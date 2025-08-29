"""
Intelligent monitoring engine for analytics.
Analyzes metrics, detects anomalies, and triggers alerts automatically.
"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from aura.analytics import get_events
from aura.analytics.models import AlertInstance
from aura.analytics.models import AlertRule
from aura.analytics.models import MetricsSnapshot
from aura.analytics.monitoring.notifications import NotificationManager

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Represents a metric value with metadata."""

    value: float
    timestamp: datetime
    source: str
    context: dict[str, Any] = None


@dataclass
class AnomalyDetection:
    """Represents an anomaly detection result."""

    is_anomaly: bool
    severity: str
    confidence: float
    description: str
    expected_range: tuple[float, float]
    actual_value: float


class MonitoringEngine:
    """
    Intelligent monitoring engine for analytics metrics.

    Features:
    - Real-time metric evaluation
    - Anomaly detection using statistical methods
    - Threshold-based alerting
    - Adaptive baselines
    - Alert fatigue prevention
    """

    def __init__(self):
        self.notification_manager = NotificationManager()
        self.cache_timeout = 300  # 5 minutes
        self.anomaly_sensitivity = 2.0  # Standard deviations for anomaly detection

    def run_monitoring_cycle(self) -> dict[str, Any]:
        """
        Run a complete monitoring cycle.
        Evaluates all active rules and triggers alerts as needed.
        """
        start_time = timezone.now()
        results = {
            "timestamp": start_time,
            "rules_evaluated": 0,
            "alerts_triggered": 0,
            "anomalies_detected": 0,
            "errors": [],
        }

        try:
            # Get all active alert rules
            active_rules = AlertRule.objects.filter(is_active=True)

            for rule in active_rules:
                try:
                    self._evaluate_rule(rule, results)
                    results["rules_evaluated"] += 1
                except Exception as e:
                    logger.error(f"Failed to evaluate rule {rule.id}: {e}")
                    results["errors"].append(f"Rule {rule.id}: {e!s}")

            # Perform anomaly detection on key metrics
            anomalies = self._detect_anomalies()
            results["anomalies_detected"] = len(anomalies)

            # Process detected anomalies
            for anomaly in anomalies:
                self._handle_anomaly(anomaly, results)

            # Update monitoring statistics
            self._update_monitoring_stats(results)

        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")
            results["errors"].append(f"Monitoring cycle: {e!s}")

        duration = (timezone.now() - start_time).total_seconds()
        results["duration_seconds"] = duration

        logger.info(f"Monitoring cycle completed: {results}")
        return results

    def _evaluate_rule(self, rule: AlertRule, results: dict[str, Any]) -> None:
        """Evaluate a single alert rule."""
        if not rule.can_trigger():
            logger.debug(f"Rule {rule.id} is in cooldown, skipping")
            return

        # Get current metric value
        current_value = self._get_metric_value(rule)
        if current_value is None:
            logger.warning(f"No data available for rule {rule.id}")
            return

        # Evaluate condition
        should_trigger = self._evaluate_condition(rule, current_value.value)

        if should_trigger:
            # Trigger alert
            context = {
                "metric_value": current_value.value,
                "threshold": rule.threshold_value,
                "condition": rule.condition_type,
                "time_window": rule.time_window,
                "source": current_value.source,
                "timestamp": current_value.timestamp.isoformat(),
                "context": current_value.context or {},
            }

            success = rule.trigger_alert(current_value.value, context)
            if success:
                results["alerts_triggered"] += 1
                logger.info(
                    f"Alert triggered for rule {rule.id}: {current_value.value}",
                )

                # Send notifications
                self._send_notifications(rule, context)

    def _get_metric_value(self, rule: AlertRule) -> MetricValue | None:
        """Get current metric value for a rule."""
        try:
            if rule.metric == "event_count":
                return self._get_event_count_metric(rule)
            elif rule.metric == "unique_users":
                return self._get_unique_users_metric(rule)
            elif rule.metric == "events_per_minute":
                return self._get_events_per_minute_metric(rule)
            elif rule.metric == "error_rate":
                return self._get_error_rate_metric(rule)
            elif rule.metric == "avg_response_time":
                return self._get_avg_response_time_metric(rule)
            else:
                logger.warning(f"Unknown metric type: {rule.metric}")
                return None
        except Exception as e:
            logger.error(f"Failed to get metric {rule.metric}: {e}")
            return None

    def _get_event_count_metric(self, rule: AlertRule) -> MetricValue:
        """Get event count metric."""
        cache_key = f"monitoring:event_count:{rule.event_type}:{rule.time_window}"
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return MetricValue(
                value=cached_value,
                timestamp=timezone.now(),
                source="cache",
            )

        # Calculate time window
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=rule.time_window)

        # Get events
        events = get_events(
            event_type=rule.event_type if rule.event_type else None,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        count = len(events)
        cache.set(cache_key, count, self.cache_timeout)

        return MetricValue(
            value=float(count),
            timestamp=timezone.now(),
            source="events",
            context={"time_window": rule.time_window, "event_type": rule.event_type},
        )

    def _get_unique_users_metric(self, rule: AlertRule) -> MetricValue:
        """Get unique users metric."""
        cache_key = f"monitoring:unique_users:{rule.time_window}"
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return MetricValue(
                value=cached_value,
                timestamp=timezone.now(),
                source="cache",
            )

        # Calculate time window
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=rule.time_window)

        # Get events and count unique users
        events = get_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        user_ids = set()
        for event in events:
            user_id = event.get("user_id")
            if user_id:
                user_ids.add(user_id)

        count = len(user_ids)
        cache.set(cache_key, count, self.cache_timeout)

        return MetricValue(
            value=float(count),
            timestamp=timezone.now(),
            source="events",
            context={"time_window": rule.time_window},
        )

    def _get_events_per_minute_metric(self, rule: AlertRule) -> MetricValue:
        """Get events per minute metric."""
        # Get event count for the time window
        event_count_metric = self._get_event_count_metric(rule)
        events_per_minute = event_count_metric.value / rule.time_window

        return MetricValue(
            value=events_per_minute,
            timestamp=event_count_metric.timestamp,
            source=event_count_metric.source,
            context=event_count_metric.context,
        )

    def _get_error_rate_metric(self, rule: AlertRule) -> MetricValue:
        """Get error rate metric."""
        # Calculate time window
        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=rule.time_window)

        # Get all events and error events
        all_events = get_events(start_time=start_time, end_time=end_time, limit=10000)
        error_events = [
            e for e in all_events if "error" in e.get("event_type", "").lower()
        ]

        total_count = len(all_events)
        error_count = len(error_events)

        error_rate = (error_count / total_count * 100) if total_count > 0 else 0

        return MetricValue(
            value=error_rate,
            timestamp=timezone.now(),
            source="events",
            context={
                "total_events": total_count,
                "error_events": error_count,
                "time_window": rule.time_window,
            },
        )

    def _get_avg_response_time_metric(self, rule: AlertRule) -> MetricValue:
        """Get average response time metric."""
        # This would typically come from performance monitoring
        # For now, return a placeholder value
        return MetricValue(
            value=150.0,  # milliseconds
            timestamp=timezone.now(),
            source="performance_monitor",
            context={"metric": "avg_response_time"},
        )

    def _evaluate_condition(self, rule: AlertRule, current_value: float) -> bool:
        """Evaluate if the rule condition is met."""
        threshold = rule.threshold_value

        if rule.condition_type == "greater_than":
            return current_value > threshold
        elif rule.condition_type == "less_than":
            return current_value < threshold
        elif rule.condition_type == "equals":
            return abs(current_value - threshold) < 0.001  # Float comparison tolerance
        elif rule.condition_type == "not_equals":
            return abs(current_value - threshold) >= 0.001
        elif rule.condition_type == "percentage_change":
            return self._evaluate_percentage_change(rule, current_value)
        elif rule.condition_type == "anomaly_detection":
            return self._evaluate_anomaly_condition(rule, current_value)
        else:
            logger.warning(f"Unknown condition type: {rule.condition_type}")
            return False

    def _evaluate_percentage_change(
        self,
        rule: AlertRule,
        current_value: float,
    ) -> bool:
        """Evaluate percentage change condition."""
        # Get historical baseline
        baseline = self._get_baseline_value(rule)
        if baseline is None:
            return False

        percentage_change = ((current_value - baseline) / baseline) * 100
        return abs(percentage_change) > rule.threshold_value

    def _evaluate_anomaly_condition(
        self,
        rule: AlertRule,
        current_value: float,
    ) -> bool:
        """Evaluate anomaly detection condition."""
        anomaly = self._detect_metric_anomaly(rule, current_value)
        return anomaly.is_anomaly and anomaly.confidence > (rule.threshold_value / 100)

    def _get_baseline_value(self, rule: AlertRule) -> float | None:
        """Get baseline value for comparison."""
        cache_key = f"monitoring:baseline:{rule.id}"
        cached_baseline = cache.get(cache_key)

        if cached_baseline is not None:
            return cached_baseline

        # Calculate baseline from historical data
        end_time = timezone.now() - timedelta(hours=1)  # 1 hour ago
        start_time = end_time - timedelta(days=7)  # Last 7 days

        # Get historical metric snapshots
        snapshots = MetricsSnapshot.objects.filter(
            aggregation_type="hourly",
            period_start__gte=start_time,
            period_start__lte=end_time,
        ).order_by("period_start")

        if not snapshots.exists():
            return None

        # Extract relevant values based on metric type
        values = []
        for snapshot in snapshots:
            if rule.metric == "event_count":
                event_counts = snapshot.get_event_counts()
                if rule.event_type:
                    value = event_counts.get(rule.event_type, 0)
                else:
                    value = snapshot.total_events
                values.append(value)
            elif rule.metric == "unique_users":
                value = snapshot.unique_users
                values.append(value)

        if not values:
            return None

        # Calculate baseline (median or mean)
        baseline = statistics.median(values)
        cache.set(cache_key, baseline, 3600)  # Cache for 1 hour

        return baseline

    def _detect_anomalies(self) -> list[AnomalyDetection]:
        """Detect anomalies in key metrics."""
        anomalies = []

        # Define key metrics to monitor for anomalies
        key_metrics = [
            ("event_count", None, 60),  # Total events in last hour
            ("unique_users", None, 60),  # Unique users in last hour
            ("events_per_minute", None, 30),  # Events per minute in last 30 minutes
        ]

        for metric_name, event_type, time_window in key_metrics:
            try:
                # Create temporary rule for metric calculation
                temp_rule = AlertRule(
                    metric=metric_name,
                    event_type=event_type,
                    time_window=time_window,
                )

                current_value = self._get_metric_value(temp_rule)
                if current_value:
                    anomaly = self._detect_metric_anomaly(
                        temp_rule,
                        current_value.value,
                    )
                    if anomaly.is_anomaly:
                        anomalies.append(anomaly)

            except Exception as e:
                logger.error(f"Failed to detect anomaly for {metric_name}: {e}")

        return anomalies

    def _detect_metric_anomaly(
        self,
        rule: AlertRule,
        current_value: float,
    ) -> AnomalyDetection:
        """Detect if a metric value is anomalous."""
        # Get historical values for statistical analysis
        historical_values = self._get_historical_values(rule, days=7)

        if len(historical_values) < 10:  # Need minimum data points
            return AnomalyDetection(
                is_anomaly=False,
                severity="info",
                confidence=0.0,
                description="Insufficient historical data for anomaly detection",
                expected_range=(0, 0),
                actual_value=current_value,
            )

        # Calculate statistical properties
        mean_value = statistics.mean(historical_values)
        std_dev = (
            statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        )

        # Define normal range (mean ± sensitivity * std_dev)
        lower_bound = mean_value - (self.anomaly_sensitivity * std_dev)
        upper_bound = mean_value + (self.anomaly_sensitivity * std_dev)

        # Check if current value is outside normal range
        is_anomaly = current_value < lower_bound or current_value > upper_bound

        # Calculate confidence based on distance from mean
        if std_dev > 0:
            z_score = abs(current_value - mean_value) / std_dev
            confidence = min(z_score / self.anomaly_sensitivity, 1.0)
        else:
            confidence = 1.0 if is_anomaly else 0.0

        # Determine severity
        if confidence > 0.8:
            severity = "critical"
        elif confidence > 0.6:
            severity = "warning"
        else:
            severity = "info"

        # Generate description
        direction = "above" if current_value > upper_bound else "below"
        description = f"Metric '{rule.metric}' is {direction} normal range"

        return AnomalyDetection(
            is_anomaly=is_anomaly,
            severity=severity,
            confidence=confidence,
            description=description,
            expected_range=(lower_bound, upper_bound),
            actual_value=current_value,
        )

    def _get_historical_values(self, rule: AlertRule, days: int = 7) -> list[float]:
        """Get historical values for a metric."""
        cache_key = f"monitoring:historical:{rule.metric}:{rule.event_type}:{days}"
        cached_values = cache.get(cache_key)

        if cached_values is not None:
            return cached_values

        # Get historical snapshots
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)

        snapshots = MetricsSnapshot.objects.filter(
            aggregation_type="hourly",
            period_start__gte=start_time,
            period_start__lte=end_time,
        ).order_by("period_start")

        values = []
        for snapshot in snapshots:
            if rule.metric == "event_count":
                if rule.event_type:
                    event_counts = snapshot.get_event_counts()
                    value = event_counts.get(rule.event_type, 0)
                else:
                    value = snapshot.total_events
            elif rule.metric == "unique_users":
                value = snapshot.unique_users
            else:
                continue

            values.append(float(value))

        cache.set(cache_key, values, 1800)  # Cache for 30 minutes
        return values

    def _handle_anomaly(
        self,
        anomaly: AnomalyDetection,
        results: dict[str, Any],
    ) -> None:
        """Handle detected anomaly."""
        if anomaly.severity in ["critical", "warning"]:
            # Create an anomaly alert if it doesn't exist
            self._create_anomaly_alert(anomaly)
            results["alerts_triggered"] += 1

    def _create_anomaly_alert(self, anomaly: AnomalyDetection) -> None:
        """Create an alert instance for an anomaly."""
        # Check if similar anomaly alert already exists recently
        recent_threshold = timezone.now() - timedelta(hours=1)
        existing_alert = AlertInstance.objects.filter(
            rule__metric="anomaly_detection",
            created_at__gte=recent_threshold,
            status="active",
        ).first()

        if existing_alert:
            logger.debug("Similar anomaly alert already exists, skipping")
            return

        # Create or get anomaly detection rule
        anomaly_rule, created = AlertRule.objects.get_or_create(
            name="Automatic Anomaly Detection",
            metric="anomaly_detection",
            condition_type="anomaly_detection",
            defaults={
                "description": "Automatically generated anomaly detection alerts",
                "threshold_value": 80.0,  # 80% confidence
                "time_window": 60,
                "severity": anomaly.severity,
                "notification_channels": ["dashboard"],
                "created_by_id": 1,  # System user
                "is_active": True,
            },
        )

        # Create alert instance
        AlertInstance.objects.create(
            rule=anomaly_rule,
            triggered_value=anomaly.actual_value,
            threshold_value=0.0,  # Not applicable for anomalies
            severity=anomaly.severity,
            context={
                "anomaly_type": "statistical",
                "confidence": anomaly.confidence,
                "description": anomaly.description,
                "expected_range": anomaly.expected_range,
                "detection_method": "z_score",
            },
        )

        logger.info(f"Created anomaly alert: {anomaly.description}")

    def _send_notifications(self, rule: AlertRule, context: dict[str, Any]) -> None:
        """Send notifications for triggered alert."""
        try:
            self.notification_manager.send_alert_notifications(rule, context)
        except Exception as e:
            logger.error(f"Failed to send notifications for rule {rule.id}: {e}")

    def _update_monitoring_stats(self, results: dict[str, Any]) -> None:
        """Update monitoring statistics."""
        stats_key = "monitoring:stats"
        current_stats = cache.get(stats_key, {})

        current_stats.update(
            {
                "last_run": results["timestamp"].isoformat(),
                "last_duration": results["duration_seconds"],
                "total_runs": current_stats.get("total_runs", 0) + 1,
                "total_alerts": current_stats.get("total_alerts", 0)
                + results["alerts_triggered"],
                "total_anomalies": current_stats.get("total_anomalies", 0)
                + results["anomalies_detected"],
            },
        )

        cache.set(stats_key, current_stats, 86400)  # Cache for 24 hours
