"""
Django management command for gateway operations.
"""

import json

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils import timezone

from config.gateway import gateway


class Command(BaseCommand):
    help = "Manage and inspect API Gateway status"

    def add_arguments(self, parser):
        parser.add_argument(
            "--action",
            type=str,
            choices=["status", "health", "modules", "dependencies", "services"],
            default="status",
            help="Action to perform (default: status)",
        )

        parser.add_argument(
            "--module",
            type=str,
            help="Specific module to check (for health action)",
        )

        parser.add_argument(
            "--format",
            type=str,
            choices=["table", "json"],
            default="table",
            help="Output format (default: table)",
        )

    def handle(self, *args, **options):
        action = options["action"]
        module_name = options.get("module")
        output_format = options["format"]

        try:
            if action == "status":
                self.show_gateway_status(output_format)
            elif action == "health":
                self.show_health_status(module_name, output_format)
            elif action == "modules":
                self.show_modules(output_format)
            elif action == "dependencies":
                self.show_dependencies(output_format)
            elif action == "services":
                self.show_services(output_format)

        except Exception as e:
            raise CommandError(f"Gateway operation failed: {e!s}")

    def show_gateway_status(self, output_format):
        """Show overall gateway status."""
        try:
            # Force initialization if not done
            if not gateway._initialized:
                gateway.initialize_modules()

            modules = gateway.registry.get_all_modules()
            health_data = gateway.list_modules()

            healthy_count = sum(
                1 for health in health_data.values() if health["status"] == "healthy"
            )

            status_data = {
                "gateway_initialized": gateway._initialized,
                "total_modules": len(modules),
                "healthy_modules": healthy_count,
                "unhealthy_modules": len(modules) - healthy_count,
                "router_attached": gateway.router is not None,
                "timestamp": timezone.now().isoformat(),
            }

            if output_format == "json":
                self.stdout.write(json.dumps(status_data, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("=== Gateway Status ==="))
                self.stdout.write(f"Initialized: {status_data['gateway_initialized']}")
                self.stdout.write(f"Router Attached: {status_data['router_attached']}")
                self.stdout.write(f"Total Modules: {status_data['total_modules']}")
                self.stdout.write(f"Healthy Modules: {status_data['healthy_modules']}")
                if status_data["unhealthy_modules"] > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Unhealthy Modules: {status_data['unhealthy_modules']}",
                        ),
                    )
                self.stdout.write(f"Timestamp: {status_data['timestamp']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get gateway status: {e!s}"))

    def show_health_status(self, module_name, output_format):
        """Show health status for all modules or a specific module."""
        try:
            if module_name:
                health_data = {module_name: gateway.get_module_health(module_name)}
            else:
                health_data = gateway.list_modules()

            if output_format == "json":
                self.stdout.write(json.dumps(health_data, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("=== Module Health Status ==="))
                for module, health in health_data.items():
                    status = health["status"]
                    if status == "healthy":
                        self.stdout.write(f"✅ {module}: {self.style.SUCCESS(status.upper())}")
                        if "services" in health:
                            self.stdout.write(f"   Services: {', '.join(health['services'])}")
                        if "dependencies" in health:
                            deps = health["dependencies"]
                            if deps:
                                self.stdout.write(f"   Dependencies: {', '.join(deps)}")
                    else:
                        self.stdout.write(f"❌ {module}: {self.style.ERROR(status.upper())}")
                        if "message" in health:
                            self.stdout.write(f"   Error: {health['message']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get health status: {e!s}"))

    def show_modules(self, output_format):
        """Show all registered modules."""
        try:
            modules = gateway.registry.get_all_modules()

            if output_format == "json":
                self.stdout.write(json.dumps(modules, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("=== Registered Modules ==="))
                for module_name, config in modules.items():
                    self.stdout.write(f"\n📦 {module_name}")
                    self.stdout.write(f"   Name: {config.get('name', 'N/A')}")
                    self.stdout.write(f"   Description: {config.get('description', 'N/A')}")
                    self.stdout.write(f"   Architecture: {config.get('architecture', 'N/A')}")
                    self.stdout.write(f"   API Prefix: {config.get('api_prefix', 'N/A')}")

                    dependencies = config.get("dependencies", [])
                    if dependencies:
                        self.stdout.write(f"   Dependencies: {', '.join(dependencies)}")
                    else:
                        self.stdout.write("   Dependencies: None")

                    provides = config.get("provides", [])
                    if provides:
                        self.stdout.write(f"   Provides: {', '.join(provides)}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get modules: {e!s}"))

    def show_dependencies(self, output_format):
        """Show module dependency graph."""
        try:
            modules = gateway.registry.get_all_modules()
            dependencies = {}

            for module_name, config in modules.items():
                dependencies[module_name] = config.get("dependencies", [])

            if output_format == "json":
                self.stdout.write(json.dumps(dependencies, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("=== Module Dependencies ==="))

                # Show modules with no dependencies first
                independent_modules = [name for name, deps in dependencies.items() if not deps]
                if independent_modules:
                    self.stdout.write("\n🏛️  Independent Modules:")
                    for module in independent_modules:
                        self.stdout.write(f"   • {module}")

                # Show modules with dependencies
                dependent_modules = {name: deps for name, deps in dependencies.items() if deps}
                if dependent_modules:
                    self.stdout.write("\n🔗 Dependent Modules:")
                    for module, deps in dependent_modules.items():
                        self.stdout.write(f"   • {module} → {', '.join(deps)}")

                # Check for circular dependencies
                self._check_circular_dependencies(dependencies)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get dependencies: {e!s}"))

    def show_services(self, output_format):
        """Show all available services."""
        try:
            modules = gateway.registry.get_all_modules()
            services_data = {}

            for module_name, config in modules.items():
                provides = config.get("provides", [])
                services_data[module_name] = []

                for service_name in provides:
                    # Try to get the service to check if it's available
                    try:
                        service_instance = gateway.get_module_service(module_name, service_name)
                        status = "available" if service_instance else "unavailable"
                    except Exception:
                        status = "error"

                    services_data[module_name].append(
                        {
                            "name": service_name,
                            "status": status,
                        },
                    )

            if output_format == "json":
                self.stdout.write(json.dumps(services_data, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("=== Available Services ==="))
                for module_name, services in services_data.items():
                    if services:
                        self.stdout.write(f"\n📦 {module_name}")
                        for service in services:
                            status_icon = {
                                "available": "✅",
                                "unavailable": "❌",
                                "error": "⚠️",
                            }.get(service["status"], "❓")

                            status_style = {
                                "available": self.style.SUCCESS,
                                "unavailable": self.style.ERROR,
                                "error": self.style.WARNING,
                            }.get(service["status"], self.style.NOTICE)

                            self.stdout.write(
                                f"   {status_icon} {service['name']}: "
                                f"{status_style(service['status'].upper())}",
                            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get services: {e!s}"))

    def _check_circular_dependencies(self, dependencies):
        """Check for circular dependencies."""

        def has_circular_dep(module, visited, path):
            if module in path:
                return path[path.index(module) :] + [module]
            if module in visited:
                return None

            visited.add(module)
            path.append(module)

            for dep in dependencies.get(module, []):
                cycle = has_circular_dep(dep, visited, path)
                if cycle:
                    return cycle

            path.pop()
            return None

        circular_deps = []
        for module_name in dependencies:
            visited = set()
            cycle = has_circular_dep(module_name, visited, [])
            if cycle and cycle not in circular_deps:
                circular_deps.append(cycle)

        if circular_deps:
            self.stdout.write("\n🔄 Circular Dependencies Detected:")
            for cycle in circular_deps:
                cycle_str = " → ".join(cycle)
                self.stdout.write(self.style.WARNING(f"   ⚠️  {cycle_str}"))
        else:
            self.stdout.write("\n✅ No circular dependencies detected")
