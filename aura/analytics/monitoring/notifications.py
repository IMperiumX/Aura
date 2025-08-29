"""
Notification management system for analytics alerts.
Supports multiple channels: email, Slack, webhooks, SMS, dashboard.
"""

import logging
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from aura.analytics.models import AlertRule

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationChannel:
    """Base class for notification channels."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def send(self, rule: AlertRule, context: dict[str, Any]) -> bool:
        """Send notification. Return True if successful."""
        raise NotImplementedError

    def is_configured(self) -> bool:
        """Check if channel is properly configured."""
        return True


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""

    def send(self, rule: AlertRule, context: dict[str, Any]) -> bool:
        """Send email notification."""
        try:
            # Get recipients
            recipients = self._get_recipients(rule)
            if not recipients:
                logger.warning(f"No email recipients for rule {rule.id}")
                return False

            # Render email content
            email_context = {
                "rule": rule,
                "context": context,
                "alert_url": self._get_alert_url(rule),
            }

            subject = f"Analytics Alert: {rule.name}"
            html_message = render_to_string(
                "analytics/emails/alert_notification.html",
                email_context,
            )
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    "alerts@yourapp.com",
                ),
                recipient_list=recipients,
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(
                f"Email alert sent for rule {rule.id} to {len(recipients)} recipients",
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send email for rule {rule.id}: {e}")
            return False

    def _get_recipients(self, rule: AlertRule) -> list[str]:
        """Get email recipients for the rule."""
        recipients = []

        # Add rule creator
        if rule.created_by and rule.created_by.email:
            recipients.append(rule.created_by.email)

        # Add configured recipients from settings
        alert_emails = getattr(settings, "ANALYTICS_ALERT_EMAILS", [])
        recipients.extend(alert_emails)

        # Add recipients from rule configuration if available
        rule_emails = self.config.get("recipients", [])
        recipients.extend(rule_emails)

        return list(set(recipients))  # Remove duplicates

    def _get_alert_url(self, rule: AlertRule) -> str:
        """Get URL to view the alert."""
        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")
        return f"{base_url}/analytics/alerts/"

    def is_configured(self) -> bool:
        """Check if email is configured."""
        return bool(getattr(settings, "EMAIL_HOST", None))


class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel."""

    def send(self, rule: AlertRule, context: dict[str, Any]) -> bool:
        """Send Slack notification."""
        try:
            webhook_url = self._get_webhook_url()
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return False

            # Create Slack message
            message = self._create_slack_message(rule, context)

            # Send to Slack
            response = requests.post(
                webhook_url,
                json=message,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f"Slack alert sent for rule {rule.id}")
                return True
            else:
                logger.error(f"Slack API error {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification for rule {rule.id}: {e}")
            return False

    def _get_webhook_url(self) -> str | None:
        """Get Slack webhook URL."""
        return self.config.get("webhook_url") or getattr(
            settings,
            "SLACK_WEBHOOK_URL",
            None,
        )

    def _create_slack_message(
        self,
        rule: AlertRule,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create Slack message payload."""
        # Color based on severity
        color_map = {
            "critical": "#ff0000",
            "error": "#ff6600",
            "warning": "#ffcc00",
            "info": "#0066cc",
        }

        color = color_map.get(rule.severity, "#808080")

        # Create rich message
        message = {
            "text": f"Analytics Alert: {rule.name}",
            "attachments": [
                {
                    "color": color,
                    "title": rule.name,
                    "text": rule.description,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": rule.severity.title(),
                            "short": True,
                        },
                        {
                            "title": "Metric",
                            "value": rule.metric,
                            "short": True,
                        },
                        {
                            "title": "Current Value",
                            "value": str(context.get("metric_value", "N/A")),
                            "short": True,
                        },
                        {
                            "title": "Threshold",
                            "value": str(rule.threshold_value),
                            "short": True,
                        },
                    ],
                    "footer": "Analytics Monitoring",
                    "ts": int(context.get("timestamp", "0")),
                },
            ],
        }

        # Add event type if applicable
        if rule.event_type:
            message["attachments"][0]["fields"].append(
                {
                    "title": "Event Type",
                    "value": rule.event_type,
                    "short": True,
                },
            )

        return message

    def is_configured(self) -> bool:
        """Check if Slack is configured."""
        return bool(self._get_webhook_url())


class WebhookNotificationChannel(NotificationChannel):
    """Generic webhook notification channel."""

    def send(self, rule: AlertRule, context: dict[str, Any]) -> bool:
        """Send webhook notification."""
        try:
            webhook_url = self._get_webhook_url()
            if not webhook_url:
                logger.warning("Webhook URL not configured")
                return False

            # Create webhook payload
            payload = {
                "alert_type": "analytics_alert",
                "rule": {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "severity": rule.severity,
                    "metric": rule.metric,
                    "event_type": rule.event_type,
                    "condition_type": rule.condition_type,
                    "threshold_value": rule.threshold_value,
                    "time_window": rule.time_window,
                },
                "context": context,
                "timestamp": context.get("timestamp"),
            }

            # Send webhook
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Analytics-Monitor/1.0",
            }

            # Add authentication if configured
            auth_token = self.config.get("auth_token")
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=15,
            )

            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook alert sent for rule {rule.id}")
                return True
            else:
                logger.error(f"Webhook error {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send webhook notification for rule {rule.id}: {e}")
            return False

    def _get_webhook_url(self) -> str | None:
        """Get webhook URL."""
        return self.config.get("webhook_url") or getattr(
            settings,
            "ANALYTICS_WEBHOOK_URL",
            None,
        )

    def is_configured(self) -> bool:
        """Check if webhook is configured."""
        return bool(self._get_webhook_url())


class SMSNotificationChannel(NotificationChannel):
    """SMS notification channel (using Twilio)."""

    def send(self, rule: AlertRule, context: dict[str, Any]) -> bool:
        """Send SMS notification."""
        try:
            # Check if Twilio is configured
            if not self.is_configured():
                logger.warning("SMS not configured")
                return False

            from twilio.rest import Client

            # Get Twilio credentials
            account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
            auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
            from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

            client = Client(account_sid, auth_token)

            # Get recipients
            recipients = self._get_sms_recipients(rule)
            if not recipients:
                logger.warning(f"No SMS recipients for rule {rule.id}")
                return False

            # Create message
            message_text = self._create_sms_message(rule, context)

            # Send SMS to each recipient
            success_count = 0
            for recipient in recipients:
                try:
                    message = client.messages.create(
                        body=message_text,
                        from_=from_number,
                        to=recipient,
                    )
                    success_count += 1
                    logger.debug(f"SMS sent to {recipient}: {message.sid}")
                except Exception as e:
                    logger.error(f"Failed to send SMS to {recipient}: {e}")

            if success_count > 0:
                logger.info(
                    f"SMS alerts sent for rule {rule.id} to {success_count} recipients",
                )
                return True
            else:
                return False

        except ImportError:
            logger.error("Twilio library not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS for rule {rule.id}: {e}")
            return False

    def _get_sms_recipients(self, rule: AlertRule) -> list[str]:
        """Get SMS recipients."""
        recipients = []

        # Get from rule configuration
        rule_numbers = self.config.get("recipients", [])
        recipients.extend(rule_numbers)

        # Get from settings
        alert_numbers = getattr(settings, "ANALYTICS_ALERT_SMS", [])
        recipients.extend(alert_numbers)

        return list(set(recipients))

    def _create_sms_message(self, rule: AlertRule, context: dict[str, Any]) -> str:
        """Create SMS message text."""
        metric_value = context.get("metric_value", "N/A")
        threshold = rule.threshold_value

        message = (
            f"ALERT: {rule.name}\n"
            f"Severity: {rule.severity.upper()}\n"
            f"Metric: {rule.metric} = {metric_value}\n"
            f"Threshold: {threshold}\n"
            f"Time: {context.get('timestamp', 'Unknown')}"
        )

        # Limit SMS length
        if len(message) > 160:
            message = message[:157] + "..."

        return message

    def is_configured(self) -> bool:
        """Check if SMS/Twilio is configured."""
        return all(
            [
                getattr(settings, "TWILIO_ACCOUNT_SID", None),
                getattr(settings, "TWILIO_AUTH_TOKEN", None),
                getattr(settings, "TWILIO_FROM_NUMBER", None),
            ],
        )


class DashboardNotificationChannel(NotificationChannel):
    """Dashboard notification channel (in-app notifications)."""

    def send(self, rule: AlertRule, context: dict[str, Any]) -> bool:
        """Send dashboard notification."""
        try:
            # Dashboard notifications are handled through AlertInstance creation
            # This channel just logs the notification
            logger.info(f"Dashboard notification created for rule {rule.id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to create dashboard notification for rule {rule.id}: {e}",
            )
            return False

    def is_configured(self) -> bool:
        """Dashboard notifications are always available."""
        return True


class NotificationManager:
    """
    Manages all notification channels and routing.
    """

    def __init__(self):
        self.channels = {
            "email": EmailNotificationChannel(),
            "slack": SlackNotificationChannel(),
            "webhook": WebhookNotificationChannel(),
            "sms": SMSNotificationChannel(),
            "dashboard": DashboardNotificationChannel(),
        }

    def send_alert_notifications(
        self,
        rule: AlertRule,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        """
        Send notifications for an alert rule through configured channels.
        Returns dict of channel: success status.
        """
        results = {}

        # Get notification channels for this rule
        channels = rule.notification_channels or ["dashboard"]

        for channel_name in channels:
            if channel_name not in self.channels:
                logger.warning(f"Unknown notification channel: {channel_name}")
                results[channel_name] = False
                continue

            channel = self.channels[channel_name]

            # Check if channel is configured
            if not channel.is_configured():
                logger.warning(f"Channel {channel_name} is not configured")
                results[channel_name] = False
                continue

            # Send notification
            try:
                success = channel.send(rule, context)
                results[channel_name] = success

                if success:
                    logger.info(f"Alert sent via {channel_name} for rule {rule.id}")
                else:
                    logger.warning(
                        f"Failed to send alert via {channel_name} for rule {rule.id}",
                    )

            except Exception as e:
                logger.error(
                    f"Error sending alert via {channel_name} for rule {rule.id}: {e}",
                )
                results[channel_name] = False

        return results

    def get_channel_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all notification channels."""
        status = {}

        for name, channel in self.channels.items():
            status[name] = {
                "configured": channel.is_configured(),
                "type": channel.__class__.__name__,
            }

        return status

    def test_channel(self, channel_name: str, test_rule: AlertRule = None) -> bool:
        """Test a specific notification channel."""
        if channel_name not in self.channels:
            logger.error(f"Unknown channel: {channel_name}")
            return False

        channel = self.channels[channel_name]

        if not channel.is_configured():
            logger.error(f"Channel {channel_name} is not configured")
            return False

        # Create test rule if not provided
        if test_rule is None:
            test_rule = AlertRule(
                name="Test Alert",
                description="This is a test alert to verify notification channels",
                severity="info",
                metric="test_metric",
                threshold_value=100,
                notification_channels=[channel_name],
            )

        # Create test context
        test_context = {
            "metric_value": 150,
            "threshold": 100,
            "condition": "greater_than",
            "timestamp": "2024-01-01T12:00:00Z",
            "source": "test",
        }

        try:
            return channel.send(test_rule, test_context)
        except Exception as e:
            logger.error(f"Test failed for channel {channel_name}: {e}")
            return False
