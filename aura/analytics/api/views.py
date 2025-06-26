"""
Django REST Framework views for analytics dashboard API.
Provides endpoints for widgets, metrics, alerts, and real-time data.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from aura.analytics.models import (
    DashboardWidget,
    AlertRule,
    AlertInstance,
    MetricsSnapshot,
    DashboardConfig
)
from aura.analytics.api.serializers import (
    DashboardWidgetSerializer,
    AlertRuleSerializer,
    AlertInstanceSerializer,
    MetricsSnapshotSerializer,
    DashboardConfigSerializer,
    LiveMetricsSerializer,
    AnalyticsQuerySerializer
)
from aura.analytics import (
    get_live_metrics,
    get_events,
    get_backend_status,
    get_analytics_config
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API results."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class DashboardWidgetViewSet(ModelViewSet):
    """
    ViewSet for managing dashboard widgets.

    Provides CRUD operations plus additional actions for widget management.
    """

    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter widgets based on user permissions."""
        user = self.request.user

        # Get widgets created by user or public widgets they have access to
        queryset = DashboardWidget.objects.filter(
            Q(created_by=user) |
            Q(is_public=True) |
            Q(allowed_users=user)
        ).distinct()

        # Filter by dashboard if specified
        dashboard_id = self.request.query_params.get('dashboard_id')
        if dashboard_id:
            queryset = queryset.filter(dashboard_id=dashboard_id)

        # Filter by widget type if specified
        widget_type = self.request.query_params.get('widget_type')
        if widget_type:
            queryset = queryset.filter(widget_type=widget_type)

        return queryset.order_by('position_y', 'position_x')

    def perform_create(self, serializer):
        """Set the created_by field when creating a widget."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        """Update widget position on the dashboard."""
        widget = self.get_object()

        position_x = request.data.get('position_x')
        position_y = request.data.get('position_y')

        if position_x is not None:
            widget.position_x = position_x
        if position_y is not None:
            widget.position_y = position_y

        widget.save(update_fields=['position_x', 'position_y'])

        return Response({'status': 'position updated'})

    @action(detail=True, methods=['post'])
    def update_size(self, request, pk=None):
        """Update widget size."""
        widget = self.get_object()

        width = request.data.get('width')
        height = request.data.get('height')

        if width is not None:
            widget.width = width
        if height is not None:
            widget.height = height

        widget.save(update_fields=['width', 'height'])

        return Response({'status': 'size updated'})

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        """Get widget data based on its type and filters."""
        widget = self.get_object()
        widget.update_last_accessed()

        try:
            data = self._get_widget_data(widget)
            return Response(data)
        except Exception as e:
            return Response(
                {'error': f'Failed to get widget data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget based on its type."""
        widget_type = widget.widget_type
        filters = widget.get_filters()

        if widget_type == 'event_count':
            return self._get_event_count_data(filters)
        elif widget_type == 'event_timeline':
            return self._get_event_timeline_data(filters)
        elif widget_type == 'user_activity':
            return self._get_user_activity_data(filters)
        elif widget_type == 'system_health':
            return self._get_system_health_data()
        elif widget_type == 'real_time_feed':
            return self._get_real_time_feed_data(filters)
        elif widget_type == 'top_events':
            return self._get_top_events_data(filters)
        else:
            return {'message': f'Widget type {widget_type} not implemented'}

    def _get_event_count_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get event count data."""
        try:
            events = get_events(
                event_type=filters.get('event_type'),
                user_id=filters.get('user_id'),
                limit=1000  # Get more for counting
            )

            return {
                'total_count': len(events),
                'filtered_count': len(events),
                'timestamp': timezone.now().isoformat()
            }
        except Exception:
            return {'total_count': 0, 'filtered_count': 0}

    def _get_event_timeline_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get event timeline data."""
        try:
            events = get_events(limit=100)

            # Group events by hour
            timeline_data = {}
            for event in events:
                # Parse timestamp
                timestamp_str = event.get('timestamp', '')
                if timestamp_str:
                    try:
                        if isinstance(timestamp_str, str):
                            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            dt = timestamp_str
                        hour_key = dt.strftime('%Y-%m-%d %H:00')
                        timeline_data[hour_key] = timeline_data.get(hour_key, 0) + 1
                    except (ValueError, AttributeError):
                        continue

            # Convert to list of points
            timeline_points = [
                {'time': time, 'count': count}
                for time, count in sorted(timeline_data.items())
            ]

            return {
                'timeline': timeline_points,
                'total_events': len(events)
            }
        except Exception:
            return {'timeline': [], 'total_events': 0}

    def _get_user_activity_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get user activity data."""
        try:
            events = get_events(limit=200)

            # Count unique users
            user_ids = set()
            for event in events:
                user_id = event.get('user_id')
                if user_id:
                    user_ids.add(user_id)

            return {
                'unique_users': len(user_ids),
                'total_events': len(events),
                'avg_events_per_user': len(events) / len(user_ids) if user_ids else 0
            }
        except Exception:
            return {'unique_users': 0, 'total_events': 0, 'avg_events_per_user': 0}

    def _get_system_health_data(self) -> Dict[str, Any]:
        """Get system health data."""
        try:
            backend_status = get_backend_status()
            config = get_analytics_config()

            return {
                'backend_status': backend_status,
                'environment': config.environment,
                'production_ready': config.is_production_ready(),
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            return {
                'backend_status': {'error': str(e)},
                'environment': 'unknown',
                'production_ready': False
            }

    def _get_real_time_feed_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get real-time event feed."""
        try:
            events = get_events(limit=filters.get('limit', 20))

            # Format events for display
            formatted_events = []
            for event in events:
                formatted_events.append({
                    'type': event.get('event_type', 'Unknown'),
                    'timestamp': event.get('timestamp'),
                    'user_id': event.get('user_id'),
                    'ip_address': event.get('ip_address', '')[:8] + '...' if event.get('ip_address') else '',
                    'data': event.get('data', {})
                })

            return {
                'events': formatted_events,
                'count': len(formatted_events)
            }
        except Exception:
            return {'events': [], 'count': 0}

    def _get_top_events_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get top events data."""
        try:
            events = get_events(limit=500)

            # Count events by type
            event_counts = {}
            for event in events:
                event_type = event.get('event_type', 'Unknown')
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # Sort by count
            top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                'top_events': [{'type': event_type, 'count': count} for event_type, count in top_events],
                'total_events': len(events)
            }
        except Exception:
            return {'top_events': [], 'total_events': 0}


class AlertRuleViewSet(ModelViewSet):
    """ViewSet for managing alert rules."""

    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter alert rules by user."""
        return AlertRule.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        """Set the created_by field when creating an alert rule."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle alert rule active status."""
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save(update_fields=['is_active'])

        return Response({
            'status': 'toggled',
            'is_active': rule.is_active
        })

    @action(detail=True, methods=['get'])
    def test(self, request, pk=None):
        """Test alert rule with current data."""
        rule = self.get_object()

        # This would implement the actual alert logic
        # For now, return a mock test result
        return Response({
            'can_trigger': rule.can_trigger(),
            'test_result': 'Alert rule test not implemented yet',
            'current_value': 0,
            'threshold': rule.threshold_value
        })


class AlertInstanceViewSet(ModelViewSet):
    """ViewSet for managing alert instances."""

    queryset = AlertInstance.objects.all()
    serializer_class = AlertInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter alert instances by user's alert rules."""
        return AlertInstance.objects.filter(rule__created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert instance."""
        instance = self.get_object()
        instance.acknowledge(self.request.user)

        return Response({'status': 'acknowledged'})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert instance."""
        instance = self.get_object()
        instance.resolve()

        return Response({'status': 'resolved'})


class DashboardConfigViewSet(ModelViewSet):
    """ViewSet for managing dashboard configurations."""

    queryset = DashboardConfig.objects.all()
    serializer_class = DashboardConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter dashboards based on user permissions."""
        user = self.request.user

        return DashboardConfig.objects.filter(
            Q(created_by=user) |
            Q(is_public=True) |
            Q(allowed_users=user)
        ).distinct()

    def perform_create(self, serializer):
        """Set the created_by field when creating a dashboard."""
        serializer.save(created_by=self.request.user)


class LiveMetricsAPIView(APIView):
    """API view for live metrics data."""

    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(30))  # Cache for 30 seconds
    def get(self, request):
        """Get current live metrics."""
        time_window = request.query_params.get('time_window', 'hour')

        try:
            # Get metrics from analytics backend
            metrics = get_live_metrics(time_window=time_window)
            backend_status = get_backend_status()

            # Format response
            response_data = {
                'timestamp': timezone.now(),
                'total_events': 0,
                'events_per_minute': 0.0,
                'unique_users': 0,
                'top_event_types': [],
                'system_health': {'status': 'unknown'},
                'backend_status': backend_status
            }

            # Extract metrics if available
            if isinstance(metrics, dict):
                for backend_name, backend_metrics in metrics.items():
                    if isinstance(backend_metrics, dict):
                        total_events = backend_metrics.get('total_events', 0)
                        if total_events > response_data['total_events']:
                            response_data['total_events'] = total_events

                        # Extract event types
                        for key, value in backend_metrics.items():
                            if key.startswith('event_type:'):
                                event_type = key.replace('event_type:', '')
                                response_data['top_event_types'].append({
                                    'type': event_type,
                                    'count': value
                                })

            # Sort top event types
            response_data['top_event_types'] = sorted(
                response_data['top_event_types'],
                key=lambda x: x['count'],
                reverse=True
            )[:10]

            # Calculate events per minute (rough estimate)
            if time_window == 'hour' and response_data['total_events'] > 0:
                response_data['events_per_minute'] = response_data['total_events'] / 60.0

            serializer = LiveMetricsSerializer(response_data)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': f'Failed to get live metrics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyticsQueryAPIView(APIView):
    """API view for flexible analytics queries."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Execute analytics query with filters."""
        serializer = AnalyticsQuerySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Extract query parameters
            query_params = serializer.validated_data

            # Execute query
            events = get_events(
                event_type=query_params.get('event_type'),
                user_id=query_params.get('user_id'),
                start_time=query_params.get('start_date'),
                end_time=query_params.get('end_date'),
                limit=query_params.get('limit', 100)
            )

            # Apply aggregation if requested
            aggregation = query_params.get('aggregation')
            if aggregation:
                events = self._aggregate_events(events, aggregation)

            return Response({
                'events': events,
                'count': len(events),
                'query': query_params
            })

        except Exception as e:
            return Response(
                {'error': f'Query failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _aggregate_events(self, events: List[Dict], aggregation: str) -> List[Dict]:
        """Aggregate events by time period."""
        aggregated = {}

        for event in events:
            timestamp_str = event.get('timestamp', '')
            if not timestamp_str:
                continue

            try:
                if isinstance(timestamp_str, str):
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    dt = timestamp_str

                # Create aggregation key
                if aggregation == 'hour':
                    key = dt.strftime('%Y-%m-%d %H:00')
                elif aggregation == 'day':
                    key = dt.strftime('%Y-%m-%d')
                elif aggregation == 'week':
                    # Get Monday of the week
                    monday = dt - timedelta(days=dt.weekday())
                    key = monday.strftime('%Y-W%U')
                elif aggregation == 'month':
                    key = dt.strftime('%Y-%m')
                else:
                    continue

                if key not in aggregated:
                    aggregated[key] = {
                        'period': key,
                        'count': 0,
                        'events': []
                    }

                aggregated[key]['count'] += 1
                aggregated[key]['events'].append(event)

            except (ValueError, AttributeError):
                continue

        return list(aggregated.values())


class SystemStatusAPIView(APIView):
    """API view for system status and health information."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get comprehensive system status."""
        try:
            config = get_analytics_config()
            backend_status = get_backend_status()

            # Get alert summary
            active_alerts = AlertInstance.objects.filter(
                status='active',
                rule__created_by=request.user
            ).count()

            # Get widget counts
            widget_count = DashboardWidget.objects.filter(
                created_by=request.user
            ).count()

            return Response({
                'timestamp': timezone.now(),
                'environment': config.environment,
                'production_ready': config.is_production_ready(),
                'backend_status': backend_status,
                'active_alerts': active_alerts,
                'widget_count': widget_count,
                'system_health': {
                    'status': 'healthy' if config.is_production_ready() else 'warning',
                    'uptime': 'N/A',  # Would need to track this
                    'last_event': timezone.now()  # Would get from backend
                }
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to get system status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
