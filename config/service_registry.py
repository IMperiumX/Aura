"""
Service Registry for inter-module communication.
Provides a way for modules to discover and communicate with each other.
"""

import importlib
from typing import Any

from django.conf import settings


class ServiceRegistry:
    """
    Registry for managing services across modules.
    Enables inter-module communication while maintaining boundaries.
    """

    def __init__(self):
        self._services: dict[str, dict[str, Any]] = {}
        self._service_instances: dict[str, Any] = {}

    def register_service(
        self,
        module_name: str,
        service_name: str,
        service_class: type,
        dependencies: list | None = None,
    ):
        """Register a service for a module."""
        if module_name not in self._services:
            self._services[module_name] = {}

        self._services[module_name][service_name] = {
            "class": service_class,
            "dependencies": dependencies or [],
            "instance": None,
        }

    def get_service(self, module_name: str, service_name: str):
        """Get a service instance."""
        key = f"{module_name}.{service_name}"

        # Return cached instance if available
        if key in self._service_instances:
            return self._service_instances[key]

        # Check if service is registered
        if module_name not in self._services or service_name not in self._services[module_name]:
            return None

        service_config = self._services[module_name][service_name]
        service_class = service_config["class"]
        dependencies = service_config["dependencies"]

        # Resolve dependencies
        resolved_deps = []
        for dep in dependencies:
            if isinstance(dep, str):
                # Dependency format: "module_name.service_name"
                dep_module, dep_service = dep.split(".")
                dep_instance = self.get_service(dep_module, dep_service)
                if dep_instance:
                    resolved_deps.append(dep_instance)
            else:
                resolved_deps.append(dep)

        # Create service instance
        try:
            service_instance = service_class(*resolved_deps)
            self._service_instances[key] = service_instance
            return service_instance
        except Exception as e:
            print(f"Failed to create service {key}: {e}")
            return None

    def get_all_services(self, module_name: str) -> dict[str, Any]:
        """Get all services for a module."""
        if module_name not in self._services:
            return {}

        return {
            name: self.get_service(module_name, name) for name in self._services[module_name].keys()
        }

    def list_services(self) -> dict[str, list]:
        """List all registered services by module."""
        return {module: list(services.keys()) for module, services in self._services.items()}


class InterModuleEventBus:
    """
    Event bus for inter-module communication.
    Allows modules to publish and subscribe to events.
    """

    def __init__(self):
        self._subscribers: dict[str, list] = {}

    def subscribe(self, event_type: str, handler, module_name: str):
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(
            {
                "handler": handler,
                "module": module_name,
            },
        )

    def publish(self, event_type: str, data: dict[str, Any], source_module: str):
        """Publish an event."""
        if event_type not in self._subscribers:
            return

        for subscriber in self._subscribers[event_type]:
            # Don't send events back to the source module
            if subscriber["module"] != source_module:
                try:
                    subscriber["handler"](data)
                except Exception as e:
                    print(f"Error handling event {event_type} in {subscriber['module']}: {e}")

    def unsubscribe(self, event_type: str, handler, module_name: str):
        """Unsubscribe from an event type."""
        if event_type not in self._subscribers:
            return

        self._subscribers[event_type] = [
            sub
            for sub in self._subscribers[event_type]
            if not (sub["handler"] == handler and sub["module"] == module_name)
        ]


# Global instances
service_registry = ServiceRegistry()
event_bus = InterModuleEventBus()


def register_module_services():
    """Register services from all modules."""
    modules_config = getattr(settings, "AURA_MODULES", {})

    for module_name, config in modules_config.items():
        services_module_path = config.get("services_module")
        if not services_module_path:
            continue

        try:
            services_module = importlib.import_module(services_module_path)

            # Register services defined in the module
            if hasattr(services_module, "register_services"):
                services_module.register_services(service_registry)

            # Subscribe to events if handler exists
            if hasattr(services_module, "subscribe_to_events"):
                services_module.subscribe_to_events(event_bus, module_name)

        except ImportError:
            continue  # Module services not yet implemented


# Example usage functions for mental health module
def notify_session_scheduled(session_data: dict[str, Any]):
    """Notify other modules that a therapy session was scheduled."""
    event_bus.publish(
        "therapy_session.scheduled",
        session_data,
        "mentalhealth",
    )


def notify_session_completed(session_data: dict[str, Any]):
    """Notify other modules that a therapy session was completed."""
    event_bus.publish(
        "therapy_session.completed",
        session_data,
        "mentalhealth",
    )


def get_user_service():
    """Get the user service from the users module."""
    return service_registry.get_service("users", "UserService")


def get_notification_service():
    """Get the notification service."""
    return service_registry.get_service("notifications", "NotificationService")
