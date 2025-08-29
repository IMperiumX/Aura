"""
Management command to test analytics event recording.
This command verifies that all analytics events are properly registered and can be recorded.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from aura import analytics

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Test analytics event recording system"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list-events",
            action="store_true",
            help="List all registered event types",
        )
        parser.add_argument(
            "--test-event",
            type=str,
            help="Test recording a specific event type",
        )
        parser.add_argument(
            "--test-all",
            action="store_true",
            help="Test recording all event types",
        )

    def handle(self, *args, **options):
        """Handle the management command."""

        if options["list_events"]:
            self.list_registered_events()
        elif options["test_event"]:
            self.test_specific_event(options["test_event"])
        elif options["test_all"]:
            self.test_all_events()
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please specify an action: --list-events, --test-event <event_type>, or --test-all",
                ),
            )

    def list_registered_events(self):
        """List all registered analytics events."""
        self.stdout.write(self.style.SUCCESS("Registered Analytics Events:"))
        self.stdout.write("=" * 50)

        # Access the event manager to get registered events
        event_manager = analytics.default_manager
        event_types = event_manager._event_types

        if not event_types:
            self.stdout.write(self.style.WARNING("No events registered!"))
            return

        # Group events by category
        categories = {}
        for event_type, event_class in event_types.items():
            category = event_type.split(".")[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(
                {
                    "type": event_type,
                    "class": event_class.__name__,
                    "attributes": [attr.name for attr in event_class.attributes],
                },
            )

        for category, events in sorted(categories.items()):
            self.stdout.write(
                self.style.SUCCESS(f"\n{category.upper()} Events:"),
            )
            for event in events:
                self.stdout.write(f"  • {event['type']} ({event['class']})")
                self.stdout.write(f"    Attributes: {', '.join(event['attributes'])}")

    def test_specific_event(self, event_type):
        """Test recording a specific event type."""
        self.stdout.write(f"Testing event: {event_type}")

        try:
            # Get the event class
            event_manager = analytics.default_manager
            event_class = event_manager.get(event_type)

            # Generate test data based on event attributes
            test_data = self.generate_test_data(event_class)

            # Record the event
            analytics.record(event_type, **test_data)

            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully recorded {event_type}"),
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to record {event_type}: {e}"),
            )

    def test_all_events(self):
        """Test recording all registered event types."""
        self.stdout.write("Testing all registered events...")

        event_manager = analytics.default_manager
        event_types = event_manager._event_types

        success_count = 0
        fail_count = 0

        for event_type in event_types:
            try:
                event_class = event_manager.get(event_type)
                test_data = self.generate_test_data(event_class)
                analytics.record(event_type, **test_data)

                self.stdout.write(f"  ✓ {event_type}")
                success_count += 1

            except Exception as e:
                self.stdout.write(f"  ✗ {event_type}: {e}")
                fail_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"Success: {success_count}")
            + " | "
            + (
                self.style.ERROR(f"Failed: {fail_count}")
                if fail_count > 0
                else f"Failed: {fail_count}"
            ),
        )

    def generate_test_data(self, event_class):
        """Generate test data for an event class based on its attributes."""
        test_data = {}

        for attr in event_class.attributes:
            if attr.name.endswith("_id"):
                # For ID fields, use a test ID
                test_data[attr.name] = 1
            elif attr.name in ["email", "username"]:
                test_data[attr.name] = "test@example.com"
            elif attr.name in ["first_name", "last_name"]:
                test_data[attr.name] = "Test"
            elif attr.name in ["ip_address"]:
                test_data[attr.name] = "127.0.0.1"
            elif attr.name in ["user_agent"]:
                test_data[attr.name] = "Test User Agent"
            elif attr.name.endswith("_time") or attr.name.endswith("_at"):
                test_data[attr.name] = timezone.now().isoformat()
            elif attr.name in ["session_type", "target_audience"]:
                test_data[attr.name] = "test"
            elif attr.name in ["assessment_type", "risk_level"]:
                test_data[attr.name] = "low"
            elif attr.name in ["delivery_method", "notification_type"]:
                test_data[attr.name] = "email"
            elif attr.name in ["sender_type", "thread_type"]:
                test_data[attr.name] = "patient"
            elif attr.name in ["file_type", "export_format"]:
                test_data[attr.name] = "pdf"
            elif attr.name in ["login_method"]:
                test_data[attr.name] = "password"
            elif attr.name in ["failure_reason", "error_type"]:
                test_data[attr.name] = "test_failure"
            elif attr.name in ["cancelled_by", "logout_type"]:
                test_data[attr.name] = "user"
            elif attr.name in ["reason", "notes"]:
                test_data[attr.name] = "Test reason"
            elif attr.name in ["updated_fields", "risk_factors", "date_range"]:
                test_data[attr.name] = '["test_field"]'
            elif attr.name in [
                "success",
                "has_notes",
                "has_summary",
                "has_attachments",
                "includes_pii",
            ]:
                test_data[attr.name] = True
            elif attr.type == int:
                # For integer fields
                if (
                    "count" in attr.name
                    or "minutes" in attr.name
                    or "seconds" in attr.name
                ):
                    test_data[attr.name] = 10
                elif "bytes" in attr.name:
                    test_data[attr.name] = 1024
                elif "hours" in attr.name:
                    test_data[attr.name] = 2
                elif "rating" in attr.name or "score" in attr.name:
                    test_data[attr.name] = 5
                else:
                    test_data[attr.name] = 1
            elif attr.type == float:
                test_data[attr.name] = 0.85
            elif attr.type == bool:
                test_data[attr.name] = True
            else:
                # Default string value
                test_data[attr.name] = f"test_{attr.name}"

            # Skip required=False fields sometimes
            if not attr.required and attr.name.endswith("_id"):
                # Skip some optional ID fields to test the system
                if attr.name in ["provider_id", "external_id", "therapy_session_id"]:
                    test_data.pop(attr.name, None)

        return test_data

    def verify_backend_configuration(self):
        """Verify that the analytics backend is properly configured."""
        try:
            # Try to access the backend
            backend = analytics.backend
            self.stdout.write(f"Backend: {backend.__class__.__name__}")

            # Check if it's properly configured
            if hasattr(backend, "publisher"):
                self.stdout.write("PubSub publisher configured")

            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Backend configuration error: {e}"),
            )
            return False
