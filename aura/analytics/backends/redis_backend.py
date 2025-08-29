"""
Redis backend for analytics events.
High-performance streaming and caching for real-time analytics.
"""

import json
import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from aura.analytics.base import Analytics
from aura.analytics.event import Event

logger = logging.getLogger(__name__)


class RedisAnalytics(Analytics):
    """
    Redis backend for high-performance analytics.

    Features:
    - Real-time event streaming via Redis Streams
    - Event caching for fast retrieval
    - Pub/Sub for live dashboard updates
    - Time-series data for metrics
    - Automatic expiration management
    """

    def __init__(
        self,
        redis_url: str = None,
        stream_name: str = "analytics:events",
        cache_prefix: str = "analytics:cache:",
        pubsub_channel: str = "analytics:live",
        max_stream_length: int = 10000,
        ttl_seconds: int = 86400 * 7,
    ):  # 7 days
        self.stream_name = stream_name
        self.cache_prefix = cache_prefix
        self.pubsub_channel = pubsub_channel
        self.max_stream_length = max_stream_length
        self.ttl_seconds = ttl_seconds

        self._setup_redis_connection(redis_url)

    def _setup_redis_connection(self, redis_url: str | None):
        """Setup Redis connection with fallback configuration."""
        try:
            import redis

            if redis_url:
                self.redis = redis.from_url(redis_url)
            else:
                # Use Django cache Redis if available
                redis_config = getattr(
                    settings,
                    "REDIS_CONFIG",
                    {
                        "host": "localhost",
                        "port": 6379,
                        "db": 1,  # Use different DB than cache
                        "decode_responses": False,  # We handle encoding ourselves
                    },
                )

                self.redis = redis.Redis(**redis_config)

            # Test connection
            self.redis.ping()
            logger.info("Redis analytics backend initialized successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    def record_event(self, event: Event) -> None:
        """Record event to Redis streams and cache."""
        if not self.redis:
            logger.warning("Redis not available, skipping event recording")
            return

        try:
            serialized = event.serialize()
            event_data = self._prepare_event_data(event, serialized)

            # Add to stream for real-time processing
            self._add_to_stream(event_data)

            # Cache for fast retrieval
            self._cache_event(event, event_data)

            # Publish for live updates
            self._publish_live_update(event_data)

            # Update metrics
            self._update_metrics(event)

        except Exception as e:
            logger.error(f"Failed to record event to Redis: {e}")

    def _prepare_event_data(
        self,
        event: Event,
        serialized: dict[str, Any],
    ) -> dict[str, str]:
        """Prepare event data for Redis storage."""
        return {
            "uuid": serialized["uuid"].decode()
            if isinstance(serialized["uuid"], bytes)
            else str(serialized["uuid"]),
            "type": event.type,
            "timestamp": str(serialized["timestamp"]),
            "data": json.dumps(serialized["data"], default=str),
            "user_id": str(serialized["data"].get("user_id", "")),
            "ip_address": serialized["data"].get("ip_address", ""),
        }

    def _add_to_stream(self, event_data: dict[str, str]) -> None:
        """Add event to Redis stream."""
        try:
            # Add to stream
            stream_id = self.redis.xadd(
                self.stream_name,
                event_data,
                maxlen=self.max_stream_length,
                approximate=True,
            )

            # Set expiration on stream if it's new
            self.redis.expire(self.stream_name, self.ttl_seconds)

            logger.debug(f"Added event to stream {self.stream_name}: {stream_id}")

        except Exception as e:
            logger.error(f"Failed to add event to stream: {e}")

    def _cache_event(self, event: Event, event_data: dict[str, str]) -> None:
        """Cache event for fast retrieval."""
        try:
            # Cache by UUID
            cache_key = f"{self.cache_prefix}event:{event_data['uuid']}"
            self.redis.setex(cache_key, self.ttl_seconds, json.dumps(event_data))

            # Add to type-based sets for filtering
            type_key = f"{self.cache_prefix}type:{event.type}"
            self.redis.zadd(type_key, {event_data["uuid"]: event.datetime.timestamp()})
            self.redis.expire(type_key, self.ttl_seconds)

            # Add to user-based sets if user_id exists
            if event_data.get("user_id"):
                user_key = f"{self.cache_prefix}user:{event_data['user_id']}"
                self.redis.zadd(
                    user_key,
                    {event_data["uuid"]: event.datetime.timestamp()},
                )
                self.redis.expire(user_key, self.ttl_seconds)

        except Exception as e:
            logger.error(f"Failed to cache event: {e}")

    def _publish_live_update(self, event_data: dict[str, str]) -> None:
        """Publish event for live dashboard updates."""
        try:
            live_data = {
                "type": "new_event",
                "event_type": event_data["type"],
                "timestamp": event_data["timestamp"],
                "user_id": event_data.get("user_id"),
            }

            self.redis.publish(self.pubsub_channel, json.dumps(live_data))

        except Exception as e:
            logger.error(f"Failed to publish live update: {e}")

    def _update_metrics(self, event: Event) -> None:
        """Update real-time metrics."""
        try:
            now = timezone.now()
            hour_key = f"{self.cache_prefix}metrics:hourly:{now.strftime('%Y%m%d%H')}"
            day_key = f"{self.cache_prefix}metrics:daily:{now.strftime('%Y%m%d')}"

            # Increment counters
            pipe = self.redis.pipeline()

            # Hourly metrics
            pipe.hincrby(hour_key, "total_events", 1)
            pipe.hincrby(hour_key, f"event_type:{event.type}", 1)
            pipe.expire(hour_key, 86400 * 2)  # Keep for 2 days

            # Daily metrics
            pipe.hincrby(day_key, "total_events", 1)
            pipe.hincrby(day_key, f"event_type:{event.type}", 1)
            pipe.expire(day_key, 86400 * 30)  # Keep for 30 days

            # User metrics if available
            user_id = getattr(event, "data", {}).get("user_id")
            if user_id:
                pipe.hincrby(hour_key, f"user:{user_id}", 1)
                pipe.hincrby(day_key, f"user:{user_id}", 1)

            pipe.execute()

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    def get_events(
        self,
        event_type: str | None = None,
        user_id: int | None = None,
        start_time: timezone.datetime | None = None,
        end_time: timezone.datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve events from Redis cache."""
        if not self.redis:
            return []

        try:
            event_uuids = self._get_filtered_event_uuids(
                event_type,
                user_id,
                start_time,
                end_time,
                limit,
            )

            events = []
            for uuid in event_uuids:
                cache_key = f"{self.cache_prefix}event:{uuid}"
                event_data = self.redis.get(cache_key)
                if event_data:
                    events.append(json.loads(event_data))

            return events

        except Exception as e:
            logger.error(f"Failed to retrieve events: {e}")
            return []

    def _get_filtered_event_uuids(
        self,
        event_type: str | None,
        user_id: int | None,
        start_time: timezone.datetime | None,
        end_time: timezone.datetime | None,
        limit: int,
    ) -> list[str]:
        """Get filtered list of event UUIDs."""
        # Determine which index to use
        if event_type:
            key = f"{self.cache_prefix}type:{event_type}"
        elif user_id:
            key = f"{self.cache_prefix}user:{user_id}"
        else:
            # Fall back to stream reading
            return self._get_uuids_from_stream(start_time, end_time, limit)

        # Time range filtering
        min_score = start_time.timestamp() if start_time else 0
        max_score = end_time.timestamp() if end_time else "+inf"

        # Get UUIDs in reverse chronological order
        return self.redis.zrevrangebyscore(
            key,
            max_score,
            min_score,
            start=0,
            num=limit,
        )

    def _get_uuids_from_stream(
        self,
        start_time: timezone.datetime | None,
        end_time: timezone.datetime | None,
        limit: int,
    ) -> list[str]:
        """Get event UUIDs from stream when no specific index is available."""
        try:
            # Read from stream (latest events first)
            events = self.redis.xrevrange(self.stream_name, count=limit)
            return [event_data[b"uuid"].decode() for _, event_data in events]
        except Exception:
            return []

    def get_live_metrics(self, time_window: str = "hour") -> dict[str, Any]:
        """Get real-time metrics for dashboard."""
        if not self.redis:
            return {}

        try:
            now = timezone.now()

            if time_window == "hour":
                key = f"{self.cache_prefix}metrics:hourly:{now.strftime('%Y%m%d%H')}"
            else:
                key = f"{self.cache_prefix}metrics:daily:{now.strftime('%Y%m%d')}"

            metrics = self.redis.hgetall(key)

            # Convert bytes keys/values to strings/ints
            result = {}
            for k, v in metrics.items():
                key_str = k.decode() if isinstance(k, bytes) else k
                val_int = int(v.decode() if isinstance(v, bytes) else v)
                result[key_str] = val_int

            return result

        except Exception as e:
            logger.error(f"Failed to get live metrics: {e}")
            return {}

    def subscribe_to_live_updates(self):
        """Get Redis pubsub object for live updates."""
        if not self.redis:
            return None

        try:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(self.pubsub_channel)
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to live updates: {e}")
            return None

    def cleanup_old_data(self, days_to_keep: int = 7) -> int:
        """Clean up old cached data."""
        if not self.redis:
            return 0

        try:
            cutoff_timestamp = (
                timezone.now() - timezone.timedelta(days=days_to_keep)
            ).timestamp()

            # Clean up time-based sorted sets
            pattern = f"{self.cache_prefix}type:*"
            keys = self.redis.keys(pattern)

            cleaned_count = 0
            for key in keys:
                removed = self.redis.zremrangebyscore(key, 0, cutoff_timestamp)
                cleaned_count += removed

            logger.info(f"Cleaned up {cleaned_count} old analytics entries from Redis")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
