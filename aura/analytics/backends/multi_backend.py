"""
Multi-backend analytics system with fallback support.
Writes to multiple backends simultaneously for redundancy and different use cases.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from typing import Any

from django.utils import timezone

from aura.analytics.base import Analytics
from aura.analytics.event import Event

logger = logging.getLogger(__name__)


class MultiBackendAnalytics(Analytics):
    """
    Multi-backend analytics system.

    Features:
    - Write to multiple backends simultaneously
    - Fallback chain for reliability
    - Parallel execution for performance
    - Individual backend health monitoring
    - Configurable retry strategies
    """

    def __init__(
        self,
        backends: list[dict[str, Any]],
        primary_backend: str = None,
        enable_parallel: bool = True,
        max_workers: int = 3,
        fallback_enabled: bool = True,
        health_check_interval: int = 300,
    ):  # 5 minutes
        self.backends = {}
        self.backend_configs = backends
        self.primary_backend_name = primary_backend
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.fallback_enabled = fallback_enabled
        self.health_check_interval = health_check_interval

        self._backend_health = {}
        self._last_health_check = {}

        self._initialize_backends()

    def _initialize_backends(self):
        """Initialize all configured backends."""
        for config in self.backend_configs:
            name = config["name"]
            backend_class = config["class"]
            options = config.get("options", {})

            try:
                # Import and instantiate backend
                if isinstance(backend_class, str):
                    module_path, class_name = backend_class.rsplit(".", 1)
                    module = __import__(module_path, fromlist=[class_name])
                    backend_class = getattr(module, class_name)

                backend_instance = backend_class(**options)
                self.backends[name] = backend_instance
                self._backend_health[name] = True
                self._last_health_check[name] = timezone.now()

                logger.info(f"Initialized analytics backend: {name}")

            except Exception as e:
                logger.error(f"Failed to initialize backend {name}: {e}")
                self._backend_health[name] = False

    def record_event(self, event: Event) -> None:
        """Record event to all healthy backends."""
        if self.enable_parallel:
            self._record_event_parallel(event)
        else:
            self._record_event_sequential(event)

    def _record_event_parallel(self, event: Event) -> None:
        """Record event to all backends in parallel."""
        healthy_backends = self._get_healthy_backends()

        if not healthy_backends:
            logger.error("No healthy backends available for event recording")
            return

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks for all healthy backends
            future_to_backend = {
                executor.submit(self._safe_record_event, name, backend, event): name
                for name, backend in healthy_backends.items()
            }

            # Collect results
            success_count = 0
            for future in as_completed(future_to_backend):
                backend_name = future_to_backend[future]
                try:
                    success = future.result(timeout=5.0)  # 5 second timeout
                    if success:
                        success_count += 1
                    else:
                        self._mark_backend_unhealthy(backend_name)
                except Exception as e:
                    logger.error(f"Backend {backend_name} failed: {e}")
                    self._mark_backend_unhealthy(backend_name)

            if success_count == 0:
                logger.error("All backends failed to record event")
            else:
                logger.debug(
                    f"Event recorded to {success_count}/{len(healthy_backends)} backends",
                )

    def _record_event_sequential(self, event: Event) -> None:
        """Record event to backends sequentially with fallback."""
        if self.primary_backend_name and self.primary_backend_name in self.backends:
            # Try primary backend first
            if self._safe_record_event(
                self.primary_backend_name,
                self.backends[self.primary_backend_name],
                event,
            ):
                return  # Success, we're done

        # Try all other backends if primary failed or not configured
        for name, backend in self._get_healthy_backends().items():
            if name == self.primary_backend_name:
                continue  # Already tried

            if self._safe_record_event(name, backend, event):
                return  # Success

        logger.error("All backends failed to record event")

    def _safe_record_event(self, name: str, backend: Analytics, event: Event) -> bool:
        """Safely record event to a single backend."""
        try:
            backend.record_event(event)
            self._mark_backend_healthy(name)
            return True
        except Exception as e:
            logger.warning(f"Backend {name} failed to record event: {e}")
            self._mark_backend_unhealthy(name)
            return False

    def _get_healthy_backends(self) -> dict[str, Analytics]:
        """Get dictionary of currently healthy backends."""
        self._check_backend_health()
        return {
            name: backend
            for name, backend in self.backends.items()
            if self._backend_health.get(name, False)
        }

    def _check_backend_health(self) -> None:
        """Check health of all backends periodically."""
        now = timezone.now()

        for name, backend in self.backends.items():
            last_check = self._last_health_check.get(name, now)

            # Skip if recently checked
            if (now - last_check).total_seconds() < self.health_check_interval:
                continue

            self._perform_health_check(name, backend)
            self._last_health_check[name] = now

    def _perform_health_check(self, name: str, backend: Analytics) -> None:
        """Perform health check on a specific backend."""
        try:
            # Try to call a simple method to test connectivity
            if hasattr(backend, "health_check"):
                healthy = backend.health_check()
            elif hasattr(backend, "redis") and backend.redis:
                # Redis backend
                backend.redis.ping()
                healthy = True
            elif hasattr(backend, "publisher") and backend.publisher:
                # PubSub backend
                healthy = True  # Assume healthy if publisher exists
            else:
                # Database or other backends
                healthy = True  # Assume healthy

            if healthy:
                self._mark_backend_healthy(name)
            else:
                self._mark_backend_unhealthy(name)

        except Exception as e:
            logger.warning(f"Health check failed for backend {name}: {e}")
            self._mark_backend_unhealthy(name)

    def _mark_backend_healthy(self, name: str) -> None:
        """Mark a backend as healthy."""
        if not self._backend_health.get(name, False):
            logger.info(f"Backend {name} is now healthy")
        self._backend_health[name] = True

    def _mark_backend_unhealthy(self, name: str) -> None:
        """Mark a backend as unhealthy."""
        if self._backend_health.get(name, True):
            logger.warning(f"Backend {name} is now unhealthy")
        self._backend_health[name] = False

    def get_backend_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all backends."""
        self._check_backend_health()

        status = {}
        for name in self.backends:
            status[name] = {
                "healthy": self._backend_health.get(name, False),
                "last_check": self._last_health_check.get(name),
                "is_primary": name == self.primary_backend_name,
            }

        return status

    def get_events(self, **kwargs) -> list[dict[str, Any]]:
        """Get events from the primary backend or first healthy backend."""
        # Try primary backend first
        if self.primary_backend_name and self.primary_backend_name in self.backends:
            backend = self.backends[self.primary_backend_name]
            if self._backend_health.get(self.primary_backend_name, False):
                try:
                    if hasattr(backend, "get_events"):
                        return backend.get_events(**kwargs)
                except Exception as e:
                    logger.warning(f"Primary backend failed to get events: {e}")

        # Try other backends
        for name, backend in self._get_healthy_backends().items():
            if name == self.primary_backend_name:
                continue

            try:
                if hasattr(backend, "get_events"):
                    return backend.get_events(**kwargs)
            except Exception as e:
                logger.warning(f"Backend {name} failed to get events: {e}")

        logger.error("No backends available for event retrieval")
        return []

    def get_metrics(self, **kwargs) -> dict[str, Any]:
        """Get metrics from backends that support it."""
        all_metrics = {}

        for name, backend in self._get_healthy_backends().items():
            try:
                if hasattr(backend, "get_live_metrics"):
                    metrics = backend.get_live_metrics(**kwargs)
                    if metrics:
                        all_metrics[name] = metrics
                elif hasattr(backend, "get_event_counts"):
                    metrics = backend.get_event_counts(**kwargs)
                    if metrics:
                        all_metrics[name] = metrics
            except Exception as e:
                logger.warning(f"Failed to get metrics from backend {name}: {e}")

        return all_metrics

    def cleanup_old_data(self, days_to_keep: int = 7) -> dict[str, int]:
        """Clean up old data from all backends."""
        cleanup_results = {}

        for name, backend in self.backends.items():
            try:
                if hasattr(backend, "cleanup_old_data"):
                    result = backend.cleanup_old_data(days_to_keep)
                    cleanup_results[name] = result
                elif hasattr(backend, "cleanup_old_events"):
                    result = backend.cleanup_old_events(days_to_keep)
                    cleanup_results[name] = result
            except Exception as e:
                logger.error(f"Failed to cleanup data from backend {name}: {e}")
                cleanup_results[name] = -1

        return cleanup_results

    def force_health_check(self) -> dict[str, bool]:
        """Force immediate health check on all backends."""
        results = {}

        for name, backend in self.backends.items():
            self._perform_health_check(name, backend)
            results[name] = self._backend_health.get(name, False)

        return results
