# ruff: noqa: PLC0415
"""
Dependency Injection Container for the modular monolith.
Manages service creation and dependency resolution.
"""

import inspect
from collections.abc import Callable
from typing import Any


class DIContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._singletons: dict[str, Any] = {}

    def register(self, service_name: str, service_class: type, singleton: bool = True):
        """Register a service class."""
        self._services[service_name] = service_class
        if singleton and service_name not in self._singletons:
            self._singletons[service_name] = None

    def register_factory(self, service_name: str, factory: Callable):
        """Register a factory function for creating a service."""
        self._factories[service_name] = factory

    def register_instance(self, service_name: str, instance: Any):
        """Register a specific instance."""
        self._singletons[service_name] = instance

    def resolve(self, service_name: str) -> Any:
        """Resolve a service by name."""
        # Check for registered instance first
        if service_name in self._singletons:
            if self._singletons[service_name] is not None:
                return self._singletons[service_name]

        # Check for factory
        if service_name in self._factories:
            instance = self._factories[service_name](self)
            if service_name in self._singletons:
                self._singletons[service_name] = instance
            return instance

        # Check for registered service class
        if service_name in self._services:
            service_class = self._services[service_name]
            instance = self._create_instance(service_class)
            if service_name in self._singletons:
                self._singletons[service_name] = instance
            return instance

        raise ValueError(f"Service '{service_name}' not registered")

    def _create_instance(self, service_class: type) -> Any:
        """Create an instance of a service class with dependency injection."""
        # Get constructor signature
        sig = inspect.signature(service_class.__init__)

        # Resolve dependencies
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Try to resolve parameter by type annotation
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependency = self._resolve_by_type(param.annotation)
                    if dependency is not None:
                        kwargs[param_name] = dependency
                except:
                    pass

            # Try to resolve parameter by name
            if param_name not in kwargs:
                try:
                    kwargs[param_name] = self.resolve(param_name)
                except:
                    # If we can't resolve and there's no default, raise error
                    if param.default == inspect.Parameter.empty:
                        raise ValueError(
                            f"Cannot resolve dependency '{param_name}' for {service_class}",
                        )

        return service_class(**kwargs)

    def _resolve_by_type(self, type_annotation: type) -> Any | None:
        """Try to resolve a dependency by its type."""
        # Look for services that are instances of this type
        for service_name in self._services:
            service_class = self._services[service_name]
            if issubclass(service_class, type_annotation):
                return self.resolve(service_name)
        return None


# Global DI container
container = DIContainer()


def setup_mental_health_dependencies():
    """Set up dependency injection for mental health module."""
    from aura.mentalhealth.application.use_cases.manage_therapy_session import (
        CancelTherapySessionUseCase,
    )
    from aura.mentalhealth.application.use_cases.manage_therapy_session import (
        EndTherapySessionUseCase,
    )
    from aura.mentalhealth.application.use_cases.manage_therapy_session import (
        StartTherapySessionUseCase,
    )
    from aura.mentalhealth.application.use_cases.schedule_therapy_session import (
        ScheduleTherapySessionUseCase,
    )
    from aura.mentalhealth.domain.services.therapy_session_service import (
        TherapySessionDomainService,
    )
    from aura.mentalhealth.infrastructure.repositories.django_chatbot_repository import (
        DjangoChatbotRepository,
    )
    from aura.mentalhealth.infrastructure.repositories.django_therapy_session_repository import (
        DjangoTherapySessionRepository,
    )

    # Register repositories
    container.register("therapy_session_repository", DjangoTherapySessionRepository)
    container.register("chatbot_repository", DjangoChatbotRepository)

    # Register domain services
    container.register_factory(
        "therapy_session_service",
        lambda c: TherapySessionDomainService(c.resolve("therapy_session_repository")),
    )

    # Register use cases
    container.register_factory(
        "schedule_therapy_session_use_case",
        lambda c: ScheduleTherapySessionUseCase(
            c.resolve("therapy_session_repository"),
            c.resolve("therapy_session_service"),
        ),
    )

    container.register_factory(
        "start_therapy_session_use_case",
        lambda c: StartTherapySessionUseCase(c.resolve("therapy_session_repository")),
    )

    container.register_factory(
        "end_therapy_session_use_case",
        lambda c: EndTherapySessionUseCase(c.resolve("therapy_session_repository")),
    )

    container.register_factory(
        "cancel_therapy_session_use_case",
        lambda c: CancelTherapySessionUseCase(c.resolve("therapy_session_repository")),
    )


def setup_user_dependencies():
    """Set up dependency injection for user module."""
    from aura.users.services import AuthenticationService
    from aura.users.services import UserService

    container.register("user_service", UserService)
    container.register("authentication_service", AuthenticationService)


def get_container() -> DIContainer:
    """Get the global DI container."""
    return container


# Initialize dependencies
try:
    setup_mental_health_dependencies()
    setup_user_dependencies()
except ImportError:
    # Modules might not be fully set up yet
    pass
