"""
Tests for cache instrumentation and hit/miss tracking.
"""

import time
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase

from aura.core.cache_instrumentation import (
    InstrumentedCacheProxy,
    get_instrumented_cache,
    patch_django_cache,
    unpatch_django_cache,
)
from aura.core.performance_middleware import PerformanceMonitoringMiddleware


class CacheInstrumentationTestCase(TestCase):
    """Test cases for cache instrumentation."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PerformanceMonitoringMiddleware()

        # Clear cache before each test
        cache.clear()

    def test_instrumented_cache_proxy_hit(self):
        """Test that cache hits are properly tracked."""
        # Create a request and initialize cache counters
        request = self.factory.get("/test/")
        self.middleware.process_request(request)

        # Mock get_request to return our test request
        with patch("aura.core.cache_instrumentation.get_request", return_value=request):
            instrumented_cache = InstrumentedCacheProxy(cache)

            # Set a value in cache
            instrumented_cache.set("test_key", "test_value")

            # Reset counters to test hits
            request._cache_hits = 0
            request._cache_misses = 0

            # Get the value (should be a hit)
            value = instrumented_cache.get("test_key")

            # Verify hit was tracked
            self.assertEqual(value, "test_value")
            self.assertEqual(request._cache_hits, 1)
            self.assertEqual(request._cache_misses, 0)

    def test_instrumented_cache_proxy_miss(self):
        """Test that cache misses are properly tracked."""
        # Create a request and initialize cache counters
        request = self.factory.get("/test/")
        self.middleware.process_request(request)

        # Mock get_request to return our test request
        with patch("aura.core.cache_instrumentation.get_request", return_value=request):
            instrumented_cache = InstrumentedCacheProxy(cache)

            # Reset counters
            request._cache_hits = 0
            request._cache_misses = 0

            # Get a non-existent value (should be a miss)
            value = instrumented_cache.get("nonexistent_key", "default")

            # Verify miss was tracked
            self.assertEqual(value, "default")
            self.assertEqual(request._cache_hits, 0)
            self.assertEqual(request._cache_misses, 1)

    def test_instrumented_cache_get_many(self):
        """Test that get_many properly tracks hits and misses."""
        # Create a request and initialize cache counters
        request = self.factory.get("/test/")
        self.middleware.process_request(request)

        # Mock get_request to return our test request
        with patch("aura.core.cache_instrumentation.get_request", return_value=request):
            instrumented_cache = InstrumentedCacheProxy(cache)

            # Set some values in cache
            instrumented_cache.set("key1", "value1")
            instrumented_cache.set("key2", "value2")

            # Reset counters
            request._cache_hits = 0
            request._cache_misses = 0

            # Get multiple keys (2 hits, 1 miss)
            result = instrumented_cache.get_many(["key1", "key2", "key3"])

            # Verify tracking
            self.assertEqual(len(result), 2)  # key1 and key2 found
            self.assertEqual(request._cache_hits, 2)
            self.assertEqual(request._cache_misses, 1)

    def test_instrumented_cache_has_key(self):
        """Test that has_key properly tracks hits and misses."""
        # Create a request and initialize cache counters
        request = self.factory.get("/test/")
        self.middleware.process_request(request)

        # Mock get_request to return our test request
        with patch("aura.core.cache_instrumentation.get_request", return_value=request):
            instrumented_cache = InstrumentedCacheProxy(cache)

            # Set a value in cache
            instrumented_cache.set("test_key", "test_value")

            # Reset counters
            request._cache_hits = 0
            request._cache_misses = 0

            # Check existing key (hit)
            exists = instrumented_cache.has_key("test_key")
            self.assertTrue(exists)
            self.assertEqual(request._cache_hits, 1)
            self.assertEqual(request._cache_misses, 0)

            # Check non-existent key (miss)
            not_exists = instrumented_cache.has_key("nonexistent_key")
            self.assertFalse(not_exists)
            self.assertEqual(request._cache_hits, 1)
            self.assertEqual(request._cache_misses, 1)

    def test_instrumented_cache_without_request(self):
        """Test that cache works without request context (no tracking)."""
        # No request context
        with patch("aura.core.cache_instrumentation.get_request", return_value=None):
            instrumented_cache = InstrumentedCacheProxy(cache)

            # Set and get value (should not crash)
            instrumented_cache.set("test_key", "test_value")
            value = instrumented_cache.get("test_key")

            # Verify operation worked
            self.assertEqual(value, "test_value")

    def test_cache_delegation(self):
        """Test that all cache methods are properly delegated."""
        instrumented_cache = InstrumentedCacheProxy(cache)

        # Test basic operations
        instrumented_cache.set("test_key", "test_value", timeout=300)
        self.assertEqual(instrumented_cache.get("test_key"), "test_value")

        instrumented_cache.add("add_key", "add_value")
        self.assertEqual(instrumented_cache.get("add_key"), "add_value")

        instrumented_cache.delete("test_key")
        self.assertIsNone(instrumented_cache.get("test_key"))

    def test_performance_middleware_integration(self):
        """Test integration with performance monitoring middleware."""
        request = self.factory.get("/test/")

        # Mock response
        response = Mock()
        response.status_code = 200
        response.content = b"test content"

        # Process request
        self.middleware.process_request(request)

        # Simulate cache operations during request
        with patch("aura.core.cache_instrumentation.get_request", return_value=request):
            instrumented_cache = InstrumentedCacheProxy(cache)

            # Perform cache operations
            instrumented_cache.set("key1", "value1")
            instrumented_cache.get("key1")  # hit
            instrumented_cache.get("key2", "default")  # miss
            instrumented_cache.get("key1")  # hit

        # Add some delay to simulate processing time
        time.sleep(0.1)

        # Process response
        with patch("aura.core.performance_middleware.logger") as mock_logger:
            result_response = self.middleware.process_response(request, response)

        # Verify response was returned
        self.assertEqual(result_response, response)

        # Verify performance logging occurred
        mock_logger.log.assert_called()

        # Verify cache metrics were included
        call_args = mock_logger.log.call_args
        performance_data = call_args[1]["extra"]["performance_data"]

        self.assertEqual(performance_data["cache_hits"], 2)
        self.assertEqual(performance_data["cache_misses"], 1)

    def test_get_cache_helper(self):
        """Test the get_cache() convenience function."""
        from aura.core.cache_instrumentation import get_cache

        # Get instrumented cache
        instrumented_cache = get_cache()

        # Verify it's the right type
        self.assertIsInstance(instrumented_cache, InstrumentedCacheProxy)

        # Test it works for basic operations
        instrumented_cache.set("test_key", "test_value")
        value = instrumented_cache.get("test_key")
        self.assertEqual(value, "test_value")

    def test_patch_unpatch_cache_instrumentation(self):
        """Test enabling and disabling cache instrumentation."""
        # Enable instrumentation
        patch_django_cache()

        # Get instrumented cache and verify it works
        instrumented_cache = get_instrumented_cache()
        self.assertIsInstance(instrumented_cache, InstrumentedCacheProxy)

        # Disable instrumentation
        unpatch_django_cache()

        # Note: After unpatching, get_instrumented_cache() will create a new instance
        # This is expected behavior in our safer approach
