import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, Any, Optional

from .models import Clinic, UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class PatientFlowConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time patient flow updates."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clinic_id = None
        self.clinic_group_name = None
        self.user = None
        self.user_profile = None

    async def connect(self):
        """Handle WebSocket connection."""
        # Get clinic ID from URL
        self.clinic_id = self.scope['url_route']['kwargs']['clinic_id']
        self.clinic_group_name = f"clinic_{self.clinic_id}"

        # Get user from scope
        self.user = self.scope["user"]

        # Check authentication
        if not self.user.is_authenticated:
            logger.warning("Unauthenticated user attempted to connect to WebSocket")
            await self.close(code=4001)
            return

        # Get user profile and verify clinic access
        try:
            self.user_profile = await self.get_user_profile(self.user)
            if not await self.can_access_clinic(self.user, self.clinic_id):
                logger.warning(f"User {self.user.username} denied access to clinic {self.clinic_id}")
                await self.close(code=4003)
                return
        except Exception as e:
            logger.error(f"Error verifying user access: {str(e)}")
            await self.close(code=4000)
            return

        # Join clinic group
        await self.channel_layer.group_add(
            self.clinic_group_name,
            self.channel_name
        )

        # Accept the connection
        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to clinic {self.clinic_id}',
            'timestamp': timezone.now().isoformat(),
            'user': self.user.username
        }))

        # Send initial data
        await self.send_initial_data()

        logger.info(f"User {self.user.username} connected to clinic {self.clinic_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.clinic_group_name:
            # Leave clinic group
            await self.channel_layer.group_discard(
                self.clinic_group_name,
                self.channel_name
            )

        logger.info(f"User {self.user.username if self.user else 'Unknown'} disconnected from clinic {self.clinic_id} (code: {close_code})")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.handle_ping(data)
            elif message_type == 'subscribe':
                await self.handle_subscribe(data)
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe(data)
            elif message_type == 'request_data':
                await self.handle_request_data(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error("Unknown message type")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {self.user.username}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message from {self.user.username}: {str(e)}")
            await self.send_error("Internal error")

    async def handle_ping(self, data):
        """Handle ping messages for keepalive."""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))

    async def handle_subscribe(self, data):
        """Handle subscription to specific data streams."""
        subscription_type = data.get('subscription_type')

        if subscription_type == 'appointments':
            # Subscribe to appointment updates
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'subscription_type': 'appointments',
                'message': 'Subscribed to appointment updates'
            }))
        elif subscription_type == 'notifications':
            # Subscribe to notification updates
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'subscription_type': 'notifications',
                'message': 'Subscribed to notification updates'
            }))

    async def handle_unsubscribe(self, data):
        """Handle unsubscription from data streams."""
        subscription_type = data.get('subscription_type')
        await self.send(text_data=json.dumps({
            'type': 'unsubscription_confirmed',
            'subscription_type': subscription_type,
            'message': f'Unsubscribed from {subscription_type}'
        }))

    async def handle_request_data(self, data):
        """Handle requests for specific data."""
        data_type = data.get('data_type')

        if data_type == 'flow_board':
            await self.send_flow_board_data()
        elif data_type == 'notifications':
            await self.send_user_notifications()
        elif data_type == 'clinic_summary':
            await self.send_clinic_summary()

    async def send_initial_data(self):
        """Send initial data after connection."""
        # Send flow board data
        await self.send_flow_board_data()

        # Send user notifications
        await self.send_user_notifications()

        # Send clinic summary
        await self.send_clinic_summary()

    async def send_flow_board_data(self):
        """Send current flow board data."""
        try:
            flow_board_data = await self.get_flow_board_data()
            await self.send(text_data=json.dumps({
                'type': 'flow_board_data',
                'data': flow_board_data,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending flow board data: {str(e)}")
            await self.send_error("Error loading flow board data")

    async def send_user_notifications(self):
        """Send user's unread notifications."""
        try:
            notifications_data = await self.get_user_notifications()
            await self.send(text_data=json.dumps({
                'type': 'user_notifications',
                'data': notifications_data,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            await self.send_error("Error loading notifications")

    async def send_clinic_summary(self):
        """Send clinic summary statistics."""
        try:
            summary_data = await self.get_clinic_summary()
            await self.send(text_data=json.dumps({
                'type': 'clinic_summary',
                'data': summary_data,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending clinic summary: {str(e)}")
            await self.send_error("Error loading clinic summary")

    async def send_error(self, message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))

    # Group message handlers (called by channel layer)

    async def send_status_update(self, event):
        """Send status update to client."""
        message = event['message']

        # Filter based on user permissions
        if await self.user_can_see_update(message):
            await self.send(text_data=json.dumps({
                'type': 'status_update',
                'data': message,
                'timestamp': timezone.now().isoformat()
            }))

    async def send_notification_update(self, event):
        """Send notification update to client."""
        notification = event['notification']

        # Only send to the intended recipient
        if notification.get('recipient_id') == self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'notification_update',
                'data': notification,
                'timestamp': timezone.now().isoformat()
            }))

    async def send_appointment_created(self, event):
        """Send appointment creation update."""
        appointment = event['appointment']

        if await self.user_can_see_appointment(appointment):
            await self.send(text_data=json.dumps({
                'type': 'appointment_created',
                'data': appointment,
                'timestamp': timezone.now().isoformat()
            }))

    async def send_appointment_updated(self, event):
        """Send appointment update."""
        appointment = event['appointment']

        if await self.user_can_see_appointment(appointment):
            await self.send(text_data=json.dumps({
                'type': 'appointment_updated',
                'data': appointment,
                'timestamp': timezone.now().isoformat()
            }))

    async def send_appointment_deleted(self, event):
        """Send appointment deletion update."""
        appointment_id = event['appointment_id']

        await self.send(text_data=json.dumps({
            'type': 'appointment_deleted',
            'appointment_id': appointment_id,
            'timestamp': timezone.now().isoformat()
        }))

    # Database query methods (sync to async)

    @database_sync_to_async
    def get_user_profile(self, user):
        """Get user profile."""
        try:
            return user.profile
        except UserProfile.DoesNotExist:
            return None

    @database_sync_to_async
    def can_access_clinic(self, user, clinic_id):
        """Check if user can access clinic."""
        if user.is_superuser:
            return True

        try:
            profile = user.profile
            if profile.role == 'admin':
                return True

            return profile.clinic_id == int(clinic_id)
        except (UserProfile.DoesNotExist, ValueError):
            return False

    @database_sync_to_async
    def get_flow_board_data(self):
        """Get flow board data for the clinic."""
        from .serializers import FlowBoardSerializer
        from .models import Appointment, Status

        try:
            clinic = Clinic.objects.get(id=self.clinic_id)
            today = timezone.now().date()

            appointments = Appointment.objects.filter(
                clinic=clinic,
                scheduled_time__date=today
            ).select_related('patient', 'clinic', 'provider', 'status').prefetch_related('flow_events')

            statuses = Status.objects.filter(clinic=clinic, is_active=True).order_by('order')

            data = {
                'clinic': clinic,
                'appointments': list(appointments),
                'statuses': list(statuses)
            }

            serializer = FlowBoardSerializer(data)
            return serializer.data

        except Clinic.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_notifications(self):
        """Get user's unread notifications."""
        from .serializers import NotificationSerializer
        from .models import Notification

        notifications = Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).order_by('-sent_at')[:10]  # Last 10 unread

        serializer = NotificationSerializer(notifications, many=True)
        return serializer.data

    @database_sync_to_async
    def get_clinic_summary(self):
        """Get clinic summary statistics."""
        from .models import Appointment

        try:
            clinic = Clinic.objects.get(id=self.clinic_id)
            today = timezone.now().date()

            total_appointments = clinic.appointments.filter(scheduled_time__date=today).count()
            active_appointments = clinic.appointments.filter(
                scheduled_time__date=today,
                flow_events__isnull=False
            ).distinct().count()

            completed_appointments = clinic.appointments.filter(
                scheduled_time__date=today,
                status__name__icontains='completed'
            ).count()

            return {
                'total_appointments': total_appointments,
                'active_appointments': active_appointments,
                'completed_appointments': completed_appointments,
                'completion_rate': (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
                'last_updated': timezone.now().isoformat()
            }

        except Clinic.DoesNotExist:
            return None

    @database_sync_to_async
    def user_can_see_update(self, message):
        """Check if user can see the status update."""
        # Check if the update is from the same clinic
        return message.get('clinic_id') == int(self.clinic_id)

    @database_sync_to_async
    def user_can_see_appointment(self, appointment_data):
        """Check if user can see the appointment."""
        # Check if appointment is from the same clinic
        return appointment_data.get('clinic_id') == int(self.clinic_id)


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer specifically for user notifications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_group_name = None

    async def connect(self):
        """Handle WebSocket connection for notifications."""
        self.user = self.scope["user"]

        # Check authentication
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Create user-specific group
        self.user_group_name = f"user_{self.user.id}_notifications"

        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial notification count
        await self.send_notification_count()

        logger.info(f"User {self.user.username} connected to notifications")

    async def disconnect(self, close_code):
        """Handle disconnection."""
        if self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

        logger.info(f"User {self.user.username if self.user else 'Unknown'} disconnected from notifications")

    async def receive(self, text_data):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'mark_read':
                await self.handle_mark_read(data)
            elif message_type == 'get_count':
                await self.send_notification_count()

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")

    async def handle_mark_read(self, data):
        """Handle marking notification as read."""
        notification_id = data.get('notification_id')
        if notification_id:
            await self.mark_notification_read(notification_id)
            await self.send_notification_count()

    async def send_notification_count(self):
        """Send unread notification count."""
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': count,
            'timestamp': timezone.now().isoformat()
        }))

    async def send_error(self, message: str):
        """Send error message."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))

    # Group message handlers

    async def new_notification(self, event):
        """Handle new notification."""
        notification = event['notification']
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'data': notification,
            'timestamp': timezone.now().isoformat()
        }))

        # Update count
        await self.send_notification_count()

    # Database methods

    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count."""
        from .models import Notification
        return Notification.objects.filter(recipient=self.user, is_read=False).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read."""
        from .models import Notification
        try:
            notification = Notification.objects.get(id=notification_id, recipient=self.user)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
