"""
Django management command for analytics administration.
Provides tools for health checks, data management, configuration validation, and metrics reporting
"""

import json

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils import timezone

from aura.analytics import cleanup_old_data
from aura.analytics import force_health_check
from aura.analytics import get_analytics_config
from aura.analytics import get_backend_status
from aura.analytics import get_events
from aura.analytics import get_live_metrics
from aura.analytics import is_analytics_production_ready


class Command(BaseCommand):
    """
    Analytics administration command.

    Provides comprehensive tools for managing analytics infrastructure:
    - Health monitoring and diagnostics
    - Configuration validation
    - Data management and cleanup
    - Metrics reporting
    - Backend status monitoring
    """

    help = "Analytics administration and monitoring tools"

    def add_arguments(self, parser):
        """Add command line arguments."""
        subparsers = parser.add_subparsers(
            dest="action",
            help="Analytics admin actions",
        )

        # Health check command
        health_parser = subparsers.add_parser(
            "health",
            help="Check analytics system health",
        )
        health_parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Show detailed health information",
        )
        health_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force immediate health check on all backends",
        )

        # Configuration command
        config_parser = subparsers.add_parser(
            "config",
            help="Validate and show configuration",
        )
        config_parser.add_argument(
            "--show",
            "-s",
            action="store_true",
            help="Show current configuration",
        )
        config_parser.add_argument(
            "--validate",
            "-V",
            action="store_true",
            help="Validate configuration for production",
        )

        # Metrics command
        metrics_parser = subparsers.add_parser("metrics", help="Show analytics metrics")
        metrics_parser.add_argument(
            "--window",
            "-w",
            choices=["hour", "day"],
            default="hour",
            help="Time window for metrics",
        )
        metrics_parser.add_argument(
            "--live",
            "-l",
            action="store_true",
            help="Show live metrics",
        )
        metrics_parser.add_argument(
            "--events",
            "-e",
            action="store_true",
            help="Show recent events",
        )

        # Data management command
        data_parser = subparsers.add_parser("data", help="Manage analytics data")
        data_parser.add_argument(
            "--cleanup",
            "-c",
            action="store_true",
            help="Clean up old data",
        )
        data_parser.add_argument(
            "--days",
            "-d",
            type=int,
            default=7,
            help="Days to keep (for cleanup)",
        )

        # Status command
        status_parser = subparsers.add_parser("status", help="Show system status")
        status_parser.add_argument(
            "--json",
            "-j",
            action="store_true",
            help="Output in JSON format",
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        action = options.get("action")

        if not action:
            self.print_help("manage.py", "analytics_admin")
            return

        try:
            if action == "health":
                self.handle_health(options)
            elif action == "config":
                self.handle_config(options)
            elif action == "metrics":
                self.handle_metrics(options)
            elif action == "data":
                self.handle_data(options)
            elif action == "status":
                self.handle_status(options)
            else:
                raise CommandError(f"Unknown action: {action}")

        except Exception as e:
            raise CommandError(f"Command failed: {e}")

    def handle_health(self, options):
        """Handle health check commands."""
        self.stdout.write("🏥 Analytics Health Check")
        self.stdout.write("=" * 50)

        if options.get("force"):
            self.stdout.write("Forcing health check on all backends...")
            results = force_health_check()

            for backend_name, healthy in results.items():
                status = "✅ HEALTHY" if healthy else "❌ UNHEALTHY"
                self.stdout.write(f"  {backend_name}: {status}")

        # Get current status
        status = get_backend_status()

        if isinstance(status, dict) and "status" in status:
            # Single backend
            backend_name = status.get("backend", "Unknown")
            is_healthy = status.get("status") not in ["unhealthy", "error"]
            health_status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"

            self.stdout.write(f"\nBackend: {backend_name}")
            self.stdout.write(f"Status: {health_status}")

            if options.get("verbose"):
                self.stdout.write(
                    f"Details: {json.dumps(status, indent=2, default=str)}",
                )

        elif isinstance(status, dict):
            # Multi-backend
            self.stdout.write("\nMulti-Backend Status:")

            for backend_name, info in status.items():
                is_healthy = info.get("healthy", False)
                is_primary = info.get("is_primary", False)
                last_check = info.get("last_check")

                health_status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
                primary_marker = " (PRIMARY)" if is_primary else ""

                self.stdout.write(f"  {backend_name}{primary_marker}: {health_status}")

                if options.get("verbose") and last_check:
                    self.stdout.write(f"    Last Check: {last_check}")

        # Production readiness check
        self.stdout.write("\n🚀 Production Readiness Check")
        self.stdout.write("-" * 30)

        is_ready = is_analytics_production_ready()
        readiness = "✅ READY" if is_ready else "❌ NOT READY"
        self.stdout.write(f"Status: {readiness}")

        if not is_ready:
            try:
                config = get_analytics_config()
                missing = config.get_missing_requirements()
                if missing:
                    self.stdout.write("Missing requirements:")
                    for req in missing:
                        self.stdout.write(f"  - {req}")
            except Exception as e:
                self.stdout.write(f"Could not check requirements: {e}")

    def handle_config(self, options):
        """Handle configuration commands."""
        self.stdout.write("⚙️ Analytics Configuration")
        self.stdout.write("=" * 50)

        try:
            config = get_analytics_config()

            if options.get("show"):
                self.stdout.write(f"Environment: {config.environment}")
                self.stdout.write(f"Primary Backend: {config.get_primary_backend()}")
                self.stdout.write("\nBackends:")

                for i, backend in enumerate(config.get_backends_list(), 1):
                    self.stdout.write(f"  {i}. {backend['name']} ({backend['class']})")
                    if backend.get("options"):
                        self.stdout.write(
                            f"     Options: {json.dumps(backend['options'], indent=6)}",
                        )

            if options.get("validate"):
                self.stdout.write("\n🔍 Configuration Validation")
                self.stdout.write("-" * 30)

                try:
                    config._validate_configuration()
                    self.stdout.write("✅ Configuration is valid")
                except Exception as e:
                    self.stdout.write(f"❌ Configuration validation failed: {e}")

        except Exception as e:
            self.stdout.write(f"❌ Failed to load configuration: {e}")

    def handle_metrics(self, options):
        """Handle metrics commands."""
        self.stdout.write("📊 Analytics Metrics")
        self.stdout.write("=" * 50)

        if options.get("live"):
            self.stdout.write("Live Metrics:")

            try:
                metrics = get_live_metrics(time_window=options.get("window", "hour"))

                if not metrics:
                    self.stdout.write("  No metrics available")
                else:
                    for source, data in metrics.items():
                        self.stdout.write(f"\n  {source}:")
                        for key, value in data.items():
                            self.stdout.write(f"    {key}: {value}")

            except Exception as e:
                self.stdout.write(f"  Error retrieving metrics: {e}")

        if options.get("events"):
            self.stdout.write(f"\nRecent Events (last {options.get('limit', 10)}):")

            try:
                events = get_events(limit=options.get("limit", 10))

                if not events:
                    self.stdout.write("  No recent events found")
                else:
                    for event in events:
                        timestamp = event.get("timestamp", "Unknown")
                        event_type = event.get("event_type", "Unknown")
                        user_id = event.get("user_id", "N/A")

                        self.stdout.write(
                            f"  {timestamp} - {event_type} (User: {user_id})",
                        )

            except Exception as e:
                self.stdout.write(f"  Error retrieving events: {e}")

    def handle_data(self, options):
        """Handle data management commands."""
        self.stdout.write("💾 Analytics Data Management")
        self.stdout.write("=" * 50)

        if options.get("cleanup"):
            days = options.get("days", 7)
            self.stdout.write(f"Cleaning up data older than {days} days...")

            try:
                result = cleanup_old_data(days_to_keep=days)

                if isinstance(result, dict):
                    # Multi-backend results
                    total_cleaned = 0
                    for backend_name, count in result.items():
                        if count >= 0:
                            self.stdout.write(
                                f"  {backend_name}: {count} entries cleaned",
                            )
                            total_cleaned += count
                        else:
                            self.stdout.write(f"  {backend_name}: cleanup failed")

                    self.stdout.write(f"\n✅ Total cleaned: {total_cleaned} entries")
                else:
                    # Single backend result
                    self.stdout.write(f"✅ Cleaned up {result} entries")

            except Exception as e:
                self.stdout.write(f"❌ Cleanup failed: {e}")

    def handle_status(self, options):
        """Handle status commands."""
        try:
            config = get_analytics_config()
            backend_status = get_backend_status()
            is_ready = is_analytics_production_ready()

            status_info = {
                "timestamp": timezone.now().isoformat(),
                "environment": config.environment,
                "production_ready": is_ready,
                "backend_status": backend_status,
            }

            if options.get("json"):
                self.stdout.write(json.dumps(status_info, indent=2, default=str))
            else:
                self.stdout.write("📋 Analytics System Status")
                self.stdout.write("=" * 50)
                self.stdout.write(f"Environment: {status_info['environment']}")
                self.stdout.write(
                    f"Production Ready: {'✅ Yes' if is_ready else '❌ No'}",
                )

        except Exception as e:
            if options.get("json"):
                self.stdout.write(json.dumps({"error": str(e)}, indent=2))
            else:
                self.stdout.write(f"❌ Failed to get status: {e}")
