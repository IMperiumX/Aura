"""
Database backend for analytics events.
Stores events in local database for development and as fallback.
"""
import logging
from typing import Any, Dict, Optional
from django.db import transaction
from django.utils import timezone

from aura.analytics.base import Analytics
from aura.analytics.event import Event

logger = logging.getLogger(__name__)


class DatabaseAnalytics(Analytics):
    """
    Database backend for analytics events.

    Stores events in local database table for:
    - Development environments
    - Fallback when other backends fail
    - Local analytics processing
    - Compliance and audit trails
    """

    def __init__(self,
                 table_name: str = "analytics_events",
                 max_retries: int = 3,
                 enable_batching: bool = True,
                 batch_size: int = 100):
        self.table_name = table_name
        self.max_retries = max_retries
        self.enable_batching = enable_batching
        self.batch_size = batch_size
        self._batch_queue = []
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensure the analytics events table exists."""
        from django.db import connection

        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=%s
            """, [self.table_name])

            if not cursor.fetchone():
                # Create table
                cursor.execute(f"""
                    CREATE TABLE {self.table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uuid TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        user_id INTEGER NULL,
                        session_id TEXT NULL,
                        ip_address TEXT NULL,
                        data TEXT NOT NULL,  -- JSON data
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        processed BOOLEAN DEFAULT FALSE,
                        INDEX idx_event_type (event_type),
                        INDEX idx_timestamp (timestamp),
                        INDEX idx_user_id (user_id),
                        INDEX idx_processed (processed)
                    )
                """)
                logger.info(f"Created analytics table: {self.table_name}")

    def record_event(self, event: Event) -> None:
        """Record a single event to the database."""
        if self.enable_batching:
            self._add_to_batch(event)
        else:
            self._write_event(event)

    def _add_to_batch(self, event: Event) -> None:
        """Add event to batch queue."""
        self._batch_queue.append(event)

        if len(self._batch_queue) >= self.batch_size:
            self._flush_batch()

    def _flush_batch(self) -> None:
        """Flush batch queue to database."""
        if not self._batch_queue:
            return

        events_to_write = self._batch_queue.copy()
        self._batch_queue.clear()

        try:
            self._write_events_batch(events_to_write)
            logger.debug(f"Flushed {len(events_to_write)} events to database")
        except Exception as e:
            logger.error(f"Failed to flush events batch: {e}")
            # Re-add to queue for retry
            self._batch_queue.extend(events_to_write)

    def _write_event(self, event: Event) -> None:
        """Write single event to database."""
        for attempt in range(self.max_retries):
            try:
                with transaction.atomic():
                    self._insert_event(event)
                return
            except Exception as e:
                logger.warning(f"Failed to write event (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to write event after {self.max_retries} attempts: {e}")

    def _write_events_batch(self, events: list[Event]) -> None:
        """Write multiple events in a single transaction."""
        from django.db import connection

        with transaction.atomic():
            with connection.cursor() as cursor:
                values = []
                params = []

                for event in events:
                    serialized = event.serialize()

                    values.append("(?, ?, ?, ?, ?, ?, ?)")
                    params.extend([
                        serialized['uuid'].decode() if isinstance(serialized['uuid'], bytes) else str(serialized['uuid']),
                        event.type,
                        event.datetime,
                        serialized['data'].get('user_id'),
                        None,  # session_id - can be added later
                        serialized['data'].get('ip_address'),
                        self._serialize_data(serialized['data'])
                    ])

                if values:
                    query = f"""
                        INSERT INTO {self.table_name}
                        (uuid, event_type, timestamp, user_id, session_id, ip_address, data)
                        VALUES {', '.join(values)}
                    """
                    cursor.execute(query, params)

    def _insert_event(self, event: Event) -> None:
        """Insert single event into database."""
        from django.db import connection

        serialized = event.serialize()

        with connection.cursor() as cursor:
            cursor.execute(f"""
                INSERT INTO {self.table_name}
                (uuid, event_type, timestamp, user_id, session_id, ip_address, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                serialized['uuid'].decode() if isinstance(serialized['uuid'], bytes) else str(serialized['uuid']),
                event.type,
                event.datetime,
                serialized['data'].get('user_id'),
                None,  # session_id
                serialized['data'].get('ip_address'),
                self._serialize_data(serialized['data'])
            ])

    def _serialize_data(self, data: Dict[str, Any]) -> str:
        """Serialize event data to JSON string."""
        import json
        return json.dumps(data, default=str)

    def get_events(self,
                   event_type: Optional[str] = None,
                   user_id: Optional[int] = None,
                   start_time: Optional[timezone.datetime] = None,
                   end_time: Optional[timezone.datetime] = None,
                   limit: int = 100) -> list[Dict[str, Any]]:
        """Retrieve events from database with filtering."""
        from django.db import connection

        conditions = []
        params = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT uuid, event_type, timestamp, user_id, ip_address, data
                FROM {self.table_name}
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """, params + [limit])

            results = []
            for row in cursor.fetchall():
                import json
                results.append({
                    'uuid': row[0],
                    'event_type': row[1],
                    'timestamp': row[2],
                    'user_id': row[3],
                    'ip_address': row[4],
                    'data': json.loads(row[5])
                })

            return results

    def get_event_counts(self,
                        start_time: Optional[timezone.datetime] = None,
                        end_time: Optional[timezone.datetime] = None) -> Dict[str, int]:
        """Get event counts by type for analytics."""
        from django.db import connection

        conditions = []
        params = []

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT event_type, COUNT(*) as count
                FROM {self.table_name}
                WHERE {where_clause}
                GROUP BY event_type
                ORDER BY count DESC
            """, params)

            return {row[0]: row[1] for row in cursor.fetchall()}

    def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Clean up old events to manage storage."""
        from django.db import connection

        cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)

        with connection.cursor() as cursor:
            cursor.execute(f"""
                DELETE FROM {self.table_name}
                WHERE timestamp < ?
            """, [cutoff_date])

            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old analytics events")
            return deleted_count

    def __del__(self):
        """Flush any remaining events on destruction."""
        try:
            self._flush_batch()
        except Exception:
            pass  # Don't raise exceptions in destructor
