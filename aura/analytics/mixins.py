"""
Analytics mixins to provide easy event recording capabilities.
"""
import logging
from typing import Any, Optional, Dict, Union
from django.http import HttpRequest
from aura import analytics

logger = logging.getLogger(__name__)


class AnalyticsRecordingMixin:
    """
    Mixin to provide analytics recording capabilities to views, models, and services.

    This mixin provides safe event recording with error handling and contextual information.
    """

    def record_analytics_event(
        self,
        event_type: str,
        instance: Any = None,
        request: Optional[HttpRequest] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """
        Record an analytics event safely with error handling.

        Args:
            event_type: The type of event to record (e.g., 'patient.created')
            instance: The model instance related to the event
            request: HTTP request object to extract user context
            extra_data: Additional data to include in the event
            **kwargs: Additional keyword arguments to pass to the event
        """
        try:
            # Merge extra data with kwargs
            event_data = kwargs.copy()
            if extra_data:
                event_data.update(extra_data)

            # Add user context from request if available
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                # Only add user info if not already provided
                if 'user_id' not in event_data and not any(k.endswith('_user_id') for k in event_data):
                    event_data['user_id'] = request.user.id

                # Add IP address if available
                if 'ip_address' not in event_data:
                    event_data['ip_address'] = self._get_client_ip(request)

            # Record the event
            analytics.record(event_type, instance=instance, **event_data)

        except Exception as e:
            # Log the error but don't let analytics failures break application flow
            logger.warning(
                f"Failed to record analytics event '{event_type}': {e}",
                exc_info=True,
                extra={
                    'event_type': event_type,
                    'instance_type': type(instance).__name__ if instance else None,
                    'instance_id': getattr(instance, 'id', None) if instance else None,
                    'extra_data': extra_data,
                }
            )

    def _get_client_ip(self, request: HttpRequest) -> Optional[str]:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def record_user_action(
        self,
        action: str,
        user_id: Optional[int] = None,
        request: Optional[HttpRequest] = None,
        **kwargs: Any
    ) -> None:
        """
        Convenience method to record user actions.

        Args:
            action: The action being performed (e.g., 'login', 'logout', 'profile_updated')
            user_id: ID of the user performing the action
            request: HTTP request object
            **kwargs: Additional event data
        """
        if not user_id and request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id

        event_data = kwargs.copy()
        if user_id:
            event_data['user_id'] = user_id

        if request:
            event_data['ip_address'] = self._get_client_ip(request)
            event_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate long user agents

        self.record_analytics_event(f"user.{action}", extra_data=event_data)

    def record_model_event(
        self,
        model_instance: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs: Any
    ) -> None:
        """
        Convenience method to record model-related events.

        Args:
            model_instance: The model instance involved
            action: The action performed (e.g., 'created', 'updated', 'deleted')
            request: HTTP request object
            **kwargs: Additional event data
        """
        model_name = model_instance._meta.model_name.lower()
        event_type = f"{model_name}.{action}"

        # Add model ID to event data
        event_data = kwargs.copy()
        event_data[f"{model_name}_id"] = model_instance.id

        self.record_analytics_event(
            event_type,
            instance=model_instance,
            request=request,
            extra_data=event_data
        )
