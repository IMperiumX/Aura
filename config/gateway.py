"""
API Gateway for modular monolith architecture.
Handles routing and communication between modules.
"""

import importlib
from typing import Any

from django.conf import settings


class ModuleRegistry:
    """Registry for managing modules in the modular monolith."""

    def __init__(self):
        self._modules: dict[str, dict[str, Any]] = {}
        self._api_routes: dict[str, str] = {}

    def register_module(self, module_name: str, module_config: dict[str, Any]):
        """Register a module with its configuration."""
        self._modules[module_name] = module_config

        # Register API routes if available
        if "api_prefix" in module_config:
            self._api_routes[module_config["api_prefix"]] = module_name

    def get_module_config(self, module_name: str) -> dict[str, Any] | None:
        """Get configuration for a specific module."""
        return self._modules.get(module_name)

    def get_all_modules(self) -> dict[str, dict[str, Any]]:
        """Get all registered modules."""
        return self._modules.copy()

    def resolve_api_route(self, path: str) -> str | None:
        """Resolve API path to module name."""
        for prefix, module_name in self._api_routes.items():
            if path.startswith(f"/api/0/{prefix}/"):
                return module_name
        return None


class APIGateway:
    """
    API Gateway for routing requests between modules.
    Provides centralized routing and inter-module communication.
    """

    def __init__(self):
        self.registry = ModuleRegistry()
        self.router = None  # Will be set from api_router.py
        self._service_cache: dict[str, Any] = {}
        self._initialized = False

    def initialize_modules(self):
        """Initialize and register all modules. Called after Django setup."""
        if self._initialized:
            return

        # Get module configurations from settings
        modules = getattr(settings, "AURA_MODULES", {})

        for module_name, config in modules.items():
            self.register_module(module_name, config)

        self._initialized = True

    def register_module(self, module_name: str, config: dict[str, Any]):
        """Register a module and its configuration."""
        self.registry.register_module(module_name, config)

        # Clear service cache when modules are registered
        self._service_cache.clear()

    def get_module_service(self, module_name: str, service_name: str) -> Any | None:
        """Get a service instance from a specific module."""
        cache_key = f"{module_name}.{service_name}"

        # Check cache first
        if cache_key in self._service_cache:
            return self._service_cache[cache_key]

        config = self.registry.get_module_config(module_name)
        if not config:
            return None

        try:
            services_module_path = config.get("services_module")
            if not services_module_path:
                return None

            services_module = importlib.import_module(services_module_path)
            service_class = getattr(services_module, service_name, None)

            if service_class:
                # Try to get from dependency injection container first
                try:
                    from .dependency_injection import get_container

                    container = get_container()
                    service_instance = container.resolve(cache_key.lower().replace(".", "_"))
                    self._service_cache[cache_key] = service_instance
                    return service_instance
                except (ImportError, ValueError):
                    # Fallback to direct instantiation
                    service_instance = service_class()
                    self._service_cache[cache_key] = service_instance
                    return service_instance

        except (ImportError, AttributeError) as e:
            print(f"Warning: Could not import service {service_name} from {module_name}: {e}")

        return None

    def inter_module_call(
        self,
        source_module: str,
        target_module: str,
        service: str,
        method: str,
        *args,
        **kwargs,
    ) -> Any | None:
        """Enable inter-module communication through the gateway."""
        # Validate that source module is allowed to call target module
        if not self._validate_module_dependency(source_module, target_module):
            raise ValueError(f"Module {source_module} is not allowed to call {target_module}")

        service_instance = self.get_module_service(target_module, service)
        if service_instance and hasattr(service_instance, method):
            return getattr(service_instance, method)(*args, **kwargs)
        return None

    def _validate_module_dependency(self, source_module: str, target_module: str) -> bool:
        """Validate that source module can depend on target module."""
        source_config = self.registry.get_module_config(source_module)
        if not source_config:
            return False

        allowed_dependencies = source_config.get("dependencies", [])
        return target_module in allowed_dependencies

    def get_module_health(self, module_name: str) -> dict[str, Any]:
        """Get health status of a module."""
        config = self.registry.get_module_config(module_name)
        if not config:
            return {"status": "unknown", "message": "Module not found"}

        try:
            # Try to import the module to check if it's healthy
            services_module_path = config.get("services_module")
            if services_module_path:
                importlib.import_module(services_module_path)

            return {
                "status": "healthy",
                "module": module_name,
                "services": config.get("provides", []),
                "dependencies": config.get("dependencies", []),
            }
        except ImportError as e:
            return {
                "status": "unhealthy",
                "message": f"Import error: {e!s}",
                "module": module_name,
            }

    def list_modules(self) -> dict[str, dict[str, Any]]:
        """List all registered modules with their health status."""
        modules = {}
        for module_name in self.registry.get_all_modules():
            modules[module_name] = self.get_module_health(module_name)
        return modules


# Global gateway instance
gateway = APIGateway()
