"""
Cache instrumentation for performance monitoring.
Provides instrumented cache operations that track hits/misses per request.

This module provides a safe alternative to monkey-patching Django's cache system.
Cache operations are tracked per-request and integrated with the performance monitoring middleware.

Usage:
------

1. Automatic instrumentation (recommended):
   The cache is automatically instrumented when the Django app loads.
   Use the get_cache() function instead of Django's default cache:

   ```python
   from aura.core.cache_instrumentation import get_cache

   # Instead of: from django.core.cache import cache
   cache = get_cache()

   # All cache operations will be tracked:
   cache.set('user:123', user_data, timeout=300)
   result = cache.get('user:123')  # This hit/miss will be tracked
   ```

2. Manual instrumentation:
   ```python
   from django.core.cache import cache as django_cache
   from aura.core.cache_instrumentation import InstrumentedCacheProxy

   # Create instrumented version
   cache = InstrumentedCacheProxy(django_cache)
   cache.get('key')  # Tracked
   ```

3. View hit/miss metrics in logs:
   When using PerformanceMonitoringMiddleware, you'll see output like:
   ```
   Request completed: GET /api/users/ [200] in 0.145s (3 queries, 15/2 cache hit/miss)
   ```

Features:
---------
- ✅ Thread-safe request-scoped tracking
- ✅ Zero configuration required
- ✅ No monkey-patching (avoids recursion issues)
- ✅ Tracks get(), get_many(), has_key() operations
- ✅ Integrates with performance middleware
- ✅ Robust error handling (cache operations never fail due to tracking)
"""

import logging
from typing import Any, List, Optional, Union

from django.core.cache import cache
from django.core.cache.backends.base import BaseCache
from django.http import HttpRequest

from aura.core.request_middleware import get_request

logger = logging.getLogger("aura.cache")


class InstrumentedCacheProxy:
    """
    Proxy for Django cache that tracks hits/misses on the current request.
    """

    def __init__(self, cache_backend: BaseCache):
        self.cache_backend = cache_backend

    def _increment_hit(self):
        """Increment cache hit counter for current request."""
        try:
            request = get_request()
            if request and hasattr(request, "_cache_hits"):
                request._cache_hits += 1
        except:
            pass  # Don't break cache operations if request tracking fails

    def _increment_miss(self):
        """Increment cache miss counter for current request."""
        try:
            request = get_request()
            if request and hasattr(request, "_cache_misses"):
                request._cache_misses += 1
        except:
            pass  # Don't break cache operations if request tracking fails

    def get(self, key: str, default: Any = None, version: Optional[int] = None) -> Any:
        """Get value from cache with hit/miss tracking."""
        value = self.cache_backend.get(key, default, version)

        if value is default:
            self._increment_miss()
            logger.debug(f"Cache MISS: {key}")
        else:
            self._increment_hit()
            logger.debug(f"Cache HIT: {key}")

        return value

    def get_many(self, keys: List[str], version: Optional[int] = None) -> dict:
        """Get multiple values from cache with hit/miss tracking."""
        result = self.cache_backend.get_many(keys, version)

        hits = len(result)
        misses = len(keys) - hits

        # Update counters
        try:
            request = get_request()
            if request:
                if hasattr(request, "_cache_hits"):
                    request._cache_hits += hits
                if hasattr(request, "_cache_misses"):
                    request._cache_misses += misses
        except:
            pass

        logger.debug(
            f"Cache get_many: {hits} hits, {misses} misses for {len(keys)} keys"
        )
        return result

    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        version: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        return self.cache_backend.set(key, value, timeout, version)

    def add(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        version: Optional[int] = None,
    ) -> bool:
        """Add value to cache."""
        return self.cache_backend.add(key, value, timeout, version)

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """Delete value from cache."""
        return self.cache_backend.delete(key, version)

    def delete_many(self, keys: List[str], version: Optional[int] = None) -> None:
        """Delete multiple values from cache."""
        return self.cache_backend.delete_many(keys, version)

    def clear(self) -> None:
        """Clear all cache."""
        return self.cache_backend.clear()

    def has_key(self, key: str, version: Optional[int] = None) -> bool:
        """Check if key exists in cache with hit/miss tracking."""
        result = self.cache_backend.has_key(key, version)

        if result:
            self._increment_hit()
            logger.debug(f"Cache HAS_KEY HIT: {key}")
        else:
            self._increment_miss()
            logger.debug(f"Cache HAS_KEY MISS: {key}")

        return result

    def incr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """Increment value in cache."""
        return self.cache_backend.incr(key, delta, version)

    def decr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """Decrement value in cache."""
        return self.cache_backend.decr(key, delta, version)

    def __getattr__(self, name: str) -> Any:
        """Delegate any other attributes to the underlying cache backend."""
        # Avoid infinite recursion and common problematic attributes
        if name.startswith("_") or name in ("cache_backend",):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        try:
            cache_backend = object.__getattribute__(self, "cache_backend")
            return getattr(cache_backend, name)
        except (AttributeError, RecursionError):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )


# Global instrumented cache instance
_instrumented_cache = None


def get_instrumented_cache() -> InstrumentedCacheProxy:
    """Get the instrumented cache instance."""
    global _instrumented_cache
    if _instrumented_cache is None:
        _instrumented_cache = InstrumentedCacheProxy(cache)
    return _instrumented_cache


def get_cache():
    """
    Get cache instance with performance tracking.
    Use this instead of django.core.cache.cache to enable hit/miss tracking.

    Example:
        from aura.core.cache_instrumentation import get_cache

        cache = get_cache()
        cache.set('key', 'value')
        result = cache.get('key')  # This will be tracked
    """
    return get_instrumented_cache()


def patch_django_cache():
    """
    Enable cache instrumentation by creating a global instrumented cache instance.
    This approach avoids monkey-patching Django's cache system to prevent recursion issues.
    """
    global _instrumented_cache

    try:
        from django.core.cache import cache

        if _instrumented_cache is None:
            _instrumented_cache = InstrumentedCacheProxy(cache)
            logger.info("Cache instrumentation enabled")
        else:
            logger.debug("Cache instrumentation already enabled")
    except Exception as e:
        logger.warning(f"Failed to enable cache instrumentation: {e}")


def unpatch_django_cache():
    """Disable cache instrumentation."""
    global _instrumented_cache

    try:
        _instrumented_cache = None
        logger.info("Cache instrumentation disabled")
    except Exception as e:
        logger.warning(f"Failed to disable cache instrumentation: {e}")
