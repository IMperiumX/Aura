import logging
import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("aura.performance")


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Advanced performance monitoring middleware that tracks:
    - Request/response timing
    - Database query counts and timing
    - Cache hit/miss ratios
    - Memory usage patterns
    - Slow request detection and alerting
    """

    def __init__(self, get_response: Callable = None):
        super().__init__(get_response)
        self.slow_request_threshold = getattr(
            settings, "SLOW_REQUEST_THRESHOLD", 2.0
        )  # 2 seconds
        self.db_query_threshold = getattr(
            settings, "DB_QUERY_THRESHOLD", 20
        )  # 20 queries

    def process_request(self, request: HttpRequest) -> None:
        """
        Initialize performance tracking for the request.
        """
        # Start timing
        request._performance_start_time = time.time()
        request._request_start_time = time.time()  # For logging filter compatibility

        # Track initial database query count
        request._initial_db_queries = len(connection.queries)
        request._db_queries_count = 0

        # Initialize cache tracking
        # Note: These counters are incremented by InstrumentedCacheProxy
        # when cache operations occur during the request
        request._cache_hits = 0
        request._cache_misses = 0

        # Memory tracking
        try:
            import psutil

            process = psutil.Process()
            request._initial_memory = process.memory_info().rss
        except ImportError:
            request._initial_memory = 0

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """
        Process and log performance metrics for the completed request.
        """
        if not hasattr(request, "_performance_start_time"):
            return response

        # Calculate timing
        total_time = time.time() - request._performance_start_time

        # Database metrics
        current_db_queries = len(connection.queries) - request._initial_db_queries
        request._db_queries_count = current_db_queries

        # Memory metrics
        try:
            import psutil

            process = psutil.Process()
            final_memory = process.memory_info().rss
            memory_delta = final_memory - request._initial_memory
        except ImportError:
            memory_delta = 0

        # Prepare performance data
        performance_data = {
            "request_duration": total_time,
            "db_queries": current_db_queries,
            "cache_hits": getattr(request, "_cache_hits", 0),
            "cache_misses": getattr(request, "_cache_misses", 0),
            "memory_delta": memory_delta,
            "status_code": response.status_code,
            "content_length": (
                len(response.content) if hasattr(response, "content") else 0
            ),
        }

        # Log performance metrics
        self._log_performance_metrics(request, performance_data)

        # Check for performance issues
        self._check_performance_alerts(request, performance_data)

        # Store metrics in cache for monitoring dashboard
        self._store_metrics(request, performance_data)

        return response

    def _log_performance_metrics(self, request: HttpRequest, data: dict) -> None:
        """
        Log performance metrics with appropriate level based on performance.
        """
        log_level = logging.INFO

        # Determine log level based on performance
        if data["request_duration"] > self.slow_request_threshold:
            log_level = logging.WARNING
        if data["db_queries"] > self.db_query_threshold:
            log_level = logging.WARNING
        if data["status_code"] >= 400:
            log_level = logging.ERROR

        # Create log message
        message = (
            f"Request completed: {request.method} {request.path} "
            f"[{data['status_code']}] in {data['request_duration']:.3f}s "
            f"({data['db_queries']} queries, "
            f"{data['cache_hits']}/{data['cache_misses']} cache hit/miss)"
        )

        # Log with performance data attached
        logger.log(
            log_level,
            message,
            extra={
                "performance_data": data,
                "is_performance_log": True,
            },
        )

    def _check_performance_alerts(self, request: HttpRequest, data: dict) -> None:
        """
        Check for performance issues and trigger alerts if necessary.
        """
        alerts = []

        # Slow request detection
        if data["request_duration"] > self.slow_request_threshold:
            alerts.append(f"Slow request detected: {data['request_duration']:.3f}s")

        # High database query count
        if data["db_queries"] > self.db_query_threshold:
            alerts.append(f"High DB query count: {data['db_queries']} queries")

        # High memory usage
        if data["memory_delta"] > 50 * 1024 * 1024:  # 50MB
            alerts.append(
                f"High memory usage: {data['memory_delta'] / 1024 / 1024:.1f}MB"
            )

        # Cache miss ratio
        total_cache_ops = data["cache_hits"] + data["cache_misses"]
        if total_cache_ops > 0:
            miss_ratio = data["cache_misses"] / total_cache_ops
            if miss_ratio > 0.8:  # 80% miss ratio
                alerts.append(f"High cache miss ratio: {miss_ratio:.1%}")

        # Log alerts
        for alert in alerts:
            logger.warning(
                f"Performance Alert: {alert} for {request.method} {request.path}",
                extra={
                    "alert_type": "performance",
                    "performance_data": data,
                },
            )

    def _store_metrics(self, request: HttpRequest, data: dict) -> None:
        """
        Store performance metrics in cache for monitoring dashboard.
        """
        try:
            # Create a time-series key
            timestamp = int(time.time())

            # Store individual metrics
            metrics = {
                f"perf:response_time:{timestamp}": data["request_duration"],
                f"perf:db_queries:{timestamp}": data["db_queries"],
                f"perf:cache_hits:{timestamp}": data["cache_hits"],
                f"perf:cache_misses:{timestamp}": data["cache_misses"],
                f"perf:memory_delta:{timestamp}": data["memory_delta"],
            }

            # Store with 1-hour TTL
            for key, value in metrics.items():
                cache.set(key, value, timeout=3600)

            # Store aggregated metrics
            self._update_aggregated_metrics(data)

        except Exception:
            # Don't let metrics storage break the request
            pass

    def _update_aggregated_metrics(self, data: dict) -> None:
        """
        Update aggregated performance metrics for dashboard.
        """
        try:
            # Get current aggregated data
            current_hour = int(time.time() // 3600)
            agg_key = f"perf:aggregated:{current_hour}"

            agg_data = cache.get(
                agg_key,
                {
                    "total_requests": 0,
                    "total_time": 0,
                    "total_db_queries": 0,
                    "total_cache_hits": 0,
                    "total_cache_misses": 0,
                    "slow_requests": 0,
                    "error_requests": 0,
                },
            )

            # Update aggregated data
            agg_data["total_requests"] += 1
            agg_data["total_time"] += data["request_duration"]
            agg_data["total_db_queries"] += data["db_queries"]
            agg_data["total_cache_hits"] += data["cache_hits"]
            agg_data["total_cache_misses"] += data["cache_misses"]

            if data["request_duration"] > self.slow_request_threshold:
                agg_data["slow_requests"] += 1

            if data["status_code"] >= 400:
                agg_data["error_requests"] += 1

            # Store updated aggregated data
            cache.set(agg_key, agg_data, timeout=7200)  # 2 hours TTL

        except Exception:
            pass


class DatabaseQueryTrackingMiddleware(MiddlewareMixin):
    """
    Specialized middleware for detailed database query tracking and optimization hints.
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Reset query tracking for the request.
        """
        if settings.DEBUG:
            connection.queries_log.clear()

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """
        Analyze database queries and provide optimization hints.
        """
        if not settings.DEBUG:
            return response

        queries = connection.queries
        if not queries:
            return response

        # Analyze queries for optimization opportunities
        analysis = self._analyze_queries(queries)

        if analysis["issues"]:
            logger.warning(
                f"Database optimization opportunities found for {request.path}",
                extra={
                    "query_analysis": analysis,
                    "optimization_hints": True,
                },
            )

        return response

    def _analyze_queries(self, queries: list) -> dict:
        """
        Analyze database queries for performance issues and optimization opportunities.
        """
        analysis = {
            "total_queries": len(queries),
            "total_time": sum(float(q["time"]) for q in queries),
            "slow_queries": [],
            "duplicate_queries": [],
            "n_plus_one_potential": [],
            "issues": [],
        }

        # Track query patterns
        query_patterns = {}

        for i, query in enumerate(queries):
            query_time = float(query["time"])
            sql = query["sql"]

            # Detect slow queries
            if query_time > 0.1:  # 100ms threshold
                analysis["slow_queries"].append(
                    {
                        "index": i,
                        "time": query_time,
                        "sql": sql[:200] + "..." if len(sql) > 200 else sql,
                    }
                )
                analysis["issues"].append(f"Slow query detected: {query_time:.3f}s")

            # Detect duplicate queries
            sql_normalized = self._normalize_sql(sql)
            if sql_normalized in query_patterns:
                query_patterns[sql_normalized].append(i)
            else:
                query_patterns[sql_normalized] = [i]

        # Find duplicates
        for pattern, indices in query_patterns.items():
            if len(indices) > 1:
                analysis["duplicate_queries"].append(
                    {
                        "pattern": (
                            pattern[:100] + "..." if len(pattern) > 100 else pattern
                        ),
                        "count": len(indices),
                        "indices": indices,
                    }
                )
                analysis["issues"].append(
                    f"Duplicate query pattern executed {len(indices)} times"
                )

        # Detect potential N+1 queries
        if len(queries) > 10:
            similar_patterns = [
                p for p, indices in query_patterns.items() if len(indices) > 5
            ]
            if similar_patterns:
                analysis["n_plus_one_potential"] = similar_patterns
                analysis["issues"].append("Potential N+1 query pattern detected")

        return analysis

    def _normalize_sql(self, sql: str) -> str:
        """
        Normalize SQL query for pattern matching.
        """
        import re

        # Remove specific values and normalize whitespace
        normalized = re.sub(r"\b\d+\b", "N", sql)  # Replace numbers
        normalized = re.sub(r"'[^']*'", "'X'", normalized)  # Replace string literals
        normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace

        return normalized.strip().upper()
