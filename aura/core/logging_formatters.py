"""
Custom logging formatters for structured logging and ELK stack integration
"""

import json
import logging

from django.utils import timezone


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging that outputs JSON format
    suitable for ELK stack ingestion
    """

    def format(self, record):
        # Base log structure
        log_entry = {
            "timestamp": timezone.now().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra structured data if present
        if hasattr(record, "structured_data"):
            log_entry["structured_data"] = record.structured_data

        # Add request context if available
        if hasattr(record, "request"):
            request = record.request
            log_entry["request"] = {
                "method": request.method,
                "path": request.path,
                "query_string": request.META.get("QUERY_STRING", ""),
                "user_agent": request.headers.get("user-agent", ""),
                "remote_addr": request.META.get("REMOTE_ADDR", ""),
                "user_id": str(request.user.id) if hasattr(request, "user") and request.user.is_authenticated else None,
            }

        # Add user context if available
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        return json.dumps(log_entry, ensure_ascii=False)


class AuditFormatter(logging.Formatter):
    """
    Specialized formatter for audit logs
    """

    def format(self, record):
        audit_entry = {
            "timestamp": timezone.now().isoformat() + "Z",
            "event_type": "audit",
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add structured audit data
        if hasattr(record, "audit_data"):
            audit_entry.update(record.audit_data)

        return json.dumps(audit_entry, ensure_ascii=False)


class SecurityFormatter(logging.Formatter):
    """
    Specialized formatter for security events
    """

    def format(self, record):
        security_entry = {
            "timestamp": timezone.now().isoformat() + "Z",
            "event_type": "security",
            "level": record.levelname,
            "message": record.getMessage(),
            "severity": getattr(record, "severity", "unknown"),
        }

        # Add security-specific data
        if hasattr(record, "security_data"):
            security_entry.update(record.security_data)

        # Always include IP and user agent for security events
        if hasattr(record, "ip_address"):
            security_entry["ip_address"] = record.ip_address

        if hasattr(record, "user_agent"):
            security_entry["user_agent"] = record.user_agent

        return json.dumps(security_entry, ensure_ascii=False)
