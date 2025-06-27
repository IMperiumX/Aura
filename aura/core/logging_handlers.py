import asyncio
import json
import logging
import logging.handlers
import queue
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

import redis
from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from django.utils import timezone


class AsyncBufferedHandler(logging.Handler):
    """
    High-performance async logging handler with intelligent buffering.

    Features:
    - Asynchronous log processing to prevent blocking
    - Intelligent buffering with size and time-based flushing
    - Circuit breaker pattern for reliability
    - Health monitoring and recovery
    - Graceful degradation under load
    """

    def __init__(self, target_handler, buffer_size=1000, flush_interval=5.0, max_workers=2):
        super().__init__()
        self.target_handler = target_handler
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.max_workers = max_workers

        # Thread-safe queue for log records
        self.log_queue = queue.Queue(maxsize=buffer_size * 2)

        # Buffer for batching
        self.buffer = []
        self.buffer_lock = threading.RLock()

        # Health monitoring
        self.health_stats = {
            'records_processed': 0,
            'records_dropped': 0,
            'flush_count': 0,
            'error_count': 0,
            'last_flush': time.time(),
            'circuit_open': False,
            'circuit_failures': 0,
        }

        # Worker threads
        self.workers = []
        self.shutdown_event = threading.Event()

        # Start background processing
        self._start_workers()

        # Periodic flush timer
        self._start_flush_timer()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emits a log record to the async processing queue.
        """
        try:
            # Check circuit breaker
            if self.health_stats['circuit_open']:
                self._handle_circuit_open(record)
                return

            # Try to add to queue (non-blocking)
            try:
                self.log_queue.put_nowait(record)
            except queue.Full:
                # Queue is full, drop record and update stats
                self.health_stats['records_dropped'] += 1
                self._check_circuit_breaker()

        except Exception:
            # Fallback: try to log directly
            self._emergency_log(record)

    def _start_workers(self) -> None:
        """
        Starts background worker threads for processing logs.
        """
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"AsyncLogWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

    def _worker_loop(self) -> None:
        """
        Main worker loop for processing log records.
        """
        while not self.shutdown_event.is_set():
            try:
                # Get record with timeout
                record = self.log_queue.get(timeout=1.0)

                with self.buffer_lock:
                    self.buffer.append(record)

                    # Check if buffer should be flushed
                    if (len(self.buffer) >= self.buffer_size or
                        time.time() - self.health_stats['last_flush'] >= self.flush_interval):
                        self._flush_buffer()

                self.log_queue.task_done()

            except queue.Empty:
                # Timeout - check for pending records to flush
                with self.buffer_lock:
                    if (self.buffer and
                        time.time() - self.health_stats['last_flush'] >= self.flush_interval):
                        self._flush_buffer()

            except Exception as e:
                self.health_stats['error_count'] += 1
                self._check_circuit_breaker()

    def _flush_buffer(self) -> None:
        """
        Flushes the current buffer to the target handler.
        """
        if not self.buffer:
            return

        records_to_flush = self.buffer.copy()
        self.buffer.clear()
        self.health_stats['last_flush'] = time.time()
        self.health_stats['flush_count'] += 1

        try:
            # Process records in batch
            for record in records_to_flush:
                self.target_handler.emit(record)

            self.health_stats['records_processed'] += len(records_to_flush)

            # Reset circuit breaker on successful flush
            if self.health_stats['circuit_open']:
                self._reset_circuit_breaker()

        except Exception as e:
            self.health_stats['error_count'] += 1
            self.health_stats['circuit_failures'] += 1
            self._check_circuit_breaker()

            # Emergency fallback
            for record in records_to_flush[:10]:  # Limit emergency logs
                self._emergency_log(record)

    def _start_flush_timer(self) -> None:
        """
        Starts a timer thread for periodic flushing.
        """
        def flush_timer():
            while not self.shutdown_event.is_set():
                time.sleep(self.flush_interval)
                with self.buffer_lock:
                    if self.buffer:
                        self._flush_buffer()

        timer_thread = threading.Thread(target=flush_timer, daemon=True)
        timer_thread.start()

    def _check_circuit_breaker(self) -> None:
        """
        Implements circuit breaker pattern for reliability.
        """
        error_rate = (self.health_stats['error_count'] /
                     max(1, self.health_stats['records_processed'] + self.health_stats['error_count']))

        # Open circuit if error rate is too high
        if error_rate > 0.1 and self.health_stats['circuit_failures'] > 5:
            self.health_stats['circuit_open'] = True
            self.health_stats['circuit_open_time'] = time.time()

    def _reset_circuit_breaker(self) -> None:
        """
        Resets the circuit breaker after successful operations.
        """
        self.health_stats['circuit_open'] = False
        self.health_stats['circuit_failures'] = 0

    def _handle_circuit_open(self, record: logging.LogRecord) -> None:
        """
        Handles logging when circuit breaker is open.
        """
        # Check if circuit should be closed (half-open state)
        if time.time() - self.health_stats.get('circuit_open_time', 0) > 60:
            self._reset_circuit_breaker()
            self.emit(record)  # Retry
        else:
            # Drop record or use emergency logging
            if record.levelno >= logging.ERROR:
                self._emergency_log(record)

    def _emergency_log(self, record: logging.LogRecord) -> None:
        """
        Emergency logging fallback when async processing fails.
        """
        try:
            # Use simple console logging as fallback
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '[EMERGENCY] %(asctime)s %(levelname)s %(name)s: %(message)s'
            ))
            console_handler.emit(record)
        except Exception:
            # Last resort: print to stderr
            import sys
            print(f"[CRITICAL LOGGING FAILURE] {record.getMessage()}", file=sys.stderr)

    def close(self) -> None:
        """
        Gracefully shuts down the handler.
        """
        self.shutdown_event.set()

        # Flush remaining records
        with self.buffer_lock:
            self._flush_buffer()

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)

        super().close()

    def get_health_stats(self) -> Dict[str, Any]:
        """
        Returns health statistics for monitoring.
        """
        return self.health_stats.copy()


class FailoverHandler(logging.Handler):
    """
    Failover logging handler that switches between multiple handlers.

    Features:
    - Automatic failover between primary and backup handlers
    - Health monitoring of each handler
    - Load balancing across healthy handlers
    - Configurable failover policies
    """

    def __init__(self, handlers: List[logging.Handler], failover_threshold=5):
        super().__init__()
        self.handlers = handlers
        self.failover_threshold = failover_threshold

        # Health tracking for each handler
        self.handler_health = {
            id(handler): {
                'failures': 0,
                'successes': 0,
                'last_failure': 0,
                'is_healthy': True,
                'total_records': 0,
            }
            for handler in handlers
        }

        self.current_primary = 0
        self.round_robin_index = 0

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emits record using failover logic.
        """
        # Try primary handler first
        if self._try_handler(self.handlers[self.current_primary], record):
            return

        # Primary failed, try other healthy handlers
        for i, handler in enumerate(self.handlers):
            if i != self.current_primary and self._is_handler_healthy(handler):
                if self._try_handler(handler, record):
                    # Update primary to this working handler
                    self.current_primary = i
                    return

        # All handlers failed, use emergency logging
        self._emergency_log(record)

    def _try_handler(self, handler: logging.Handler, record: logging.LogRecord) -> bool:
        """
        Attempts to emit record using specified handler.
        """
        handler_id = id(handler)

        try:
            handler.emit(record)

            # Update success stats
            health = self.handler_health[handler_id]
            health['successes'] += 1
            health['total_records'] += 1
            health['is_healthy'] = True

            return True

        except Exception as e:
            # Update failure stats
            health = self.handler_health[handler_id]
            health['failures'] += 1
            health['total_records'] += 1
            health['last_failure'] = time.time()

            # Mark as unhealthy if too many failures
            if health['failures'] >= self.failover_threshold:
                health['is_healthy'] = False

            return False

    def _is_handler_healthy(self, handler: logging.Handler) -> bool:
        """
        Checks if a handler is considered healthy.
        """
        handler_id = id(handler)
        health = self.handler_health[handler_id]

        # Auto-recovery after 5 minutes
        if not health['is_healthy']:
            if time.time() - health['last_failure'] > 300:
                health['is_healthy'] = True
                health['failures'] = 0

        return health['is_healthy']

    def _emergency_log(self, record: logging.LogRecord) -> None:
        """
        Emergency logging when all handlers fail.
        """
        try:
            import sys
            print(f"[FAILOVER EMERGENCY] {record.getMessage()}", file=sys.stderr)
        except Exception:
            pass

    def get_handler_stats(self) -> Dict[str, Any]:
        """
        Returns statistics for all handlers.
        """
        return {
            f"handler_{i}": {
                'class': handler.__class__.__name__,
                'health': self.handler_health[id(handler)]
            }
            for i, handler in enumerate(self.handlers)
        }


class MetricsHandler(logging.Handler):
    """
    Handler that extracts and exports metrics from log records.

    Features:
    - Real-time metrics extraction
    - Integration with monitoring systems
    - Anomaly detection
    - Performance tracking
    """

    def __init__(self, metrics_backend='redis'):
        super().__init__()
        self.metrics_backend = metrics_backend
        self.metrics_cache = defaultdict(lambda: defaultdict(int))
        self.anomaly_detector = AnomalyDetector()

        # Initialize metrics backend
        if metrics_backend == 'redis':
            try:
                self.redis_client = redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0'))
            except Exception:
                self.redis_client = None

    def emit(self, record: logging.LogRecord) -> None:
        """
        Extracts metrics from log record and exports them.
        """
        try:
            # Extract basic metrics
            self._extract_basic_metrics(record)

            # Extract performance metrics
            self._extract_performance_metrics(record)

            # Extract security metrics
            self._extract_security_metrics(record)

            # Check for anomalies
            self._check_anomalies(record)

            # Export metrics
            self._export_metrics()

        except Exception:
            # Don't let metrics extraction break logging
            pass

    def _extract_basic_metrics(self, record: logging.LogRecord) -> None:
        """
        Extracts basic metrics like log levels, loggers, etc.
        """
        timestamp = int(time.time())

        # Log level metrics
        self.metrics_cache[f'log_level_{record.levelname.lower()}'][timestamp] += 1

        # Logger metrics
        logger_name = record.name.replace('.', '_')
        self.metrics_cache[f'logger_{logger_name}'][timestamp] += 1

        # Error rate
        if record.levelno >= logging.ERROR:
            self.metrics_cache['error_rate'][timestamp] += 1

    def _extract_performance_metrics(self, record: logging.LogRecord) -> None:
        """
        Extracts performance-related metrics.
        """
        timestamp = int(time.time())

        # Request duration
        if hasattr(record, 'request_duration'):
            duration_ms = int(record.request_duration * 1000)
            self.metrics_cache['request_duration_ms'][timestamp] = max(
                self.metrics_cache['request_duration_ms'][timestamp],
                duration_ms
            )

        # Database queries
        if hasattr(record, 'db_queries'):
            self.metrics_cache['db_queries'][timestamp] = max(
                self.metrics_cache['db_queries'][timestamp],
                record.db_queries
            )

        # Memory usage
        if hasattr(record, 'memory_percent'):
            self.metrics_cache['memory_usage_percent'][timestamp] = max(
                self.metrics_cache['memory_usage_percent'][timestamp],
                int(record.memory_percent)
            )

    def _extract_security_metrics(self, record: logging.LogRecord) -> None:
        """
        Extracts security-related metrics.
        """
        timestamp = int(time.time())

        # Security events
        if hasattr(record, 'security_event') and record.security_event:
            self.metrics_cache['security_events'][timestamp] += 1

            # Threat type metrics
            if hasattr(record, 'threat_type'):
                threat_key = f'threat_{record.threat_type}'
                self.metrics_cache[threat_key][timestamp] += 1

        # Authentication failures
        message = str(getattr(record, 'msg', '')).lower()
        if 'authentication failed' in message or 'login failed' in message:
            self.metrics_cache['auth_failures'][timestamp] += 1

    def _check_anomalies(self, record: logging.LogRecord) -> None:
        """
        Checks for anomalies in log patterns.
        """
        self.anomaly_detector.check_record(record)

    def _export_metrics(self) -> None:
        """
        Exports metrics to the configured backend.
        """
        if self.metrics_backend == 'redis' and self.redis_client:
            self._export_to_redis()

    def _export_to_redis(self) -> None:
        """
        Exports metrics to Redis for monitoring systems.
        """
        try:
            current_time = int(time.time())

            for metric_name, time_series in self.metrics_cache.items():
                # Only export recent metrics (last 5 minutes)
                recent_data = {
                    ts: value for ts, value in time_series.items()
                    if current_time - ts <= 300
                }

                if recent_data:
                    # Store as Redis hash
                    key = f"metrics:{metric_name}"
                    self.redis_client.hmset(key, recent_data)
                    self.redis_client.expire(key, 3600)  # 1 hour TTL

        except Exception:
            # Metrics export failure shouldn't break logging
            pass


class AnomalyDetector:
    """
    Detects anomalies in log patterns for proactive monitoring.
    """

    def __init__(self):
        self.pattern_counts = defaultdict(lambda: deque(maxlen=100))
        self.alert_thresholds = {
            'error_spike': 10,  # 10 errors in window
            'auth_failure_spike': 5,  # 5 auth failures in window
            'performance_degradation': 5,  # 5 slow requests in window
        }

    def check_record(self, record: logging.LogRecord) -> None:
        """
        Checks a log record for anomalous patterns.
        """
        current_time = time.time()

        # Error spike detection
        if record.levelno >= logging.ERROR:
            self.pattern_counts['errors'].append(current_time)
            self._check_spike('errors', 'error_spike')

        # Authentication failure detection
        message = str(getattr(record, 'msg', '')).lower()
        if 'authentication failed' in message:
            self.pattern_counts['auth_failures'].append(current_time)
            self._check_spike('auth_failures', 'auth_failure_spike')

        # Performance degradation detection
        if hasattr(record, 'request_duration') and record.request_duration > 5.0:
            self.pattern_counts['slow_requests'].append(current_time)
            self._check_spike('slow_requests', 'performance_degradation')

    def _check_spike(self, pattern: str, alert_type: str) -> None:
        """
        Checks if a pattern constitutes a spike.
        """
        current_time = time.time()
        window_start = current_time - 300  # 5 minute window

        # Count events in window
        recent_events = [
            ts for ts in self.pattern_counts[pattern]
            if ts >= window_start
        ]

        if len(recent_events) >= self.alert_thresholds[alert_type]:
            self._send_alert(alert_type, len(recent_events))

    def _send_alert(self, alert_type: str, count: int) -> None:
        """
        Sends an alert for detected anomaly.
        """
        try:
            # Send email alert to admins
            subject = f"[AURA ALERT] {alert_type.replace('_', ' ').title()} Detected"
            message = f"Detected {count} occurrences of {alert_type} in the last 5 minutes."

            mail_admins(subject, message, fail_silently=True)

            # Store alert in cache for dashboard
            cache_key = f"alert:{alert_type}:{int(time.time())}"
            cache.set(cache_key, {
                'type': alert_type,
                'count': count,
                'timestamp': timezone.now().isoformat(),
            }, timeout=3600)

        except Exception:
            # Alert sending failure shouldn't break logging
            pass


class StructuredFileHandler(logging.handlers.RotatingFileHandler):
    """
    Enhanced file handler with structured logging and compression.
    """

    def __init__(self, filename, mode='a', maxBytes=100*1024*1024,
                 backupCount=10, encoding='utf-8', delay=False,
                 compress_rotated=True):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.compress_rotated = compress_rotated

    def doRollover(self) -> None:
        """
        Enhanced rollover with compression.
        """
        super().doRollover()

        if self.compress_rotated:
            self._compress_old_logs()

    def _compress_old_logs(self) -> None:
        """
        Compresses rotated log files to save space.
        """
        import gzip
        import os

        try:
            for i in range(1, self.backupCount + 1):
                log_file = f"{self.baseFilename}.{i}"
                compressed_file = f"{log_file}.gz"

                if os.path.exists(log_file) and not os.path.exists(compressed_file):
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            f_out.writelines(f_in)

                    os.remove(log_file)

        except Exception:
            # Compression failure shouldn't break logging
            pass
