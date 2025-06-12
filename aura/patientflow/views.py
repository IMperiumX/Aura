from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Avg, F
from django.db import transaction
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Dict, Any, List
import logging

from .models import (
    Clinic, Status, Patient, Appointment,
    PatientFlowEvent, Notification, UserProfile
)
from .serializers import (
    ClinicSerializer, StatusSerializer, PatientSerializer,
    AppointmentListSerializer, AppointmentDetailSerializer, AppointmentCreateUpdateSerializer,
    PatientFlowEventSerializer, NotificationSerializer, UserProfileSerializer,
    FlowBoardSerializer
)
from .permissions import (
    ClinicPermission, ClinicStatusPermission, ClinicPatientPermission,
    ClinicAppointmentPermission, NotificationPermission, FlowEventPermission,
    PatientFlowStaffPermission, IsAdminUser
)
from .filters import (
    AppointmentFilter, PatientFlowEventFilter, NotificationFilter
)

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


class ClinicViewSet(viewsets.ModelViewSet):
    """ViewSet for Clinic model with staff management."""
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [ClinicPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'address']
    filterset_fields = ['is_active']

    def get_queryset(self):
        """Filter clinics based on user permissions."""
        user = self.request.user
        if user.is_superuser:
            return Clinic.objects.all()

        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return Clinic.objects.all()

        if hasattr(user, 'profile') and user.profile.clinic:
            return Clinic.objects.filter(id=user.profile.clinic.id)

        return Clinic.objects.none()

    @action(detail=True, methods=['get'])
    def staff(self, request, pk=None):
        """Get all staff members for a clinic."""
        clinic = self.get_object()
        staff = UserProfile.objects.filter(clinic=clinic)
        serializer = UserProfileSerializer(staff, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a clinic."""
        clinic = self.get_object()
        today = timezone.now().date()

        # Calculate metrics
        total_appointments = clinic.appointments.filter(scheduled_time__date=today).count()
        active_appointments = clinic.appointments.filter(
            scheduled_time__date=today,
            flow_events__isnull=False
        ).distinct().count()

        completed_appointments = clinic.appointments.filter(
            scheduled_time__date=today,
            status__name__icontains='completed'
        ).count()

        # Average wait times
        avg_times = []
        for appointment in clinic.appointments.filter(scheduled_time__date=today):
            if appointment.flow_events.exists():
                first_event = appointment.flow_events.first()
                time_in_system = timezone.now() - first_event.timestamp
                avg_times.append(time_in_system.total_seconds() / 60)

        avg_wait_time = sum(avg_times) / len(avg_times) if avg_times else 0

        # Status distribution
        status_distribution = clinic.appointments.filter(
            scheduled_time__date=today
        ).values('status__name').annotate(count=Count('id'))

        analytics = {
            'date': today.isoformat(),
            'total_appointments': total_appointments,
            'active_appointments': active_appointments,
            'completed_appointments': completed_appointments,
            'completion_rate': (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            'average_wait_time_minutes': round(avg_wait_time, 2),
            'status_distribution': list(status_distribution),
            'staff_count': clinic.user_profiles.count(),
            'patient_count': clinic.patients.count(),
        }

        return Response(analytics)


class StatusViewSet(viewsets.ModelViewSet):
    """ViewSet for Status model with ordering support."""
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [ClinicStatusPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    filterset_fields = ['clinic', 'is_active']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order']

    def get_queryset(self):
        """Filter statuses based on user's clinic."""
        user = self.request.user
        if user.is_superuser:
            return Status.objects.all()

        if hasattr(user, 'profile') and user.profile.clinic:
            return Status.objects.filter(clinic=user.profile.clinic)

        return Status.objects.none()

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder statuses."""
        status_orders = request.data.get('status_orders', [])

        with transaction.atomic():
            for item in status_orders:
                Status.objects.filter(id=item['id']).update(order=item['order'])

        return Response({'success': True})

    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        """Get all appointments currently in this status."""
        status_obj = self.get_object()
        appointments = status_obj.appointments.all()
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)


class PatientViewSet(viewsets.ModelViewSet):
    """ViewSet for Patient model."""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [ClinicPatientPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['first_name', 'last_name']
    filterset_fields = ['clinic']

    def get_queryset(self):
        """Filter patients based on user's clinic."""
        user = self.request.user
        if user.is_superuser:
            return Patient.objects.all()

        if hasattr(user, 'profile') and user.profile.clinic:
            return Patient.objects.filter(clinic=user.profile.clinic)

        return Patient.objects.none()

    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        """Get all appointments for a patient."""
        patient = self.get_object()
        appointments = patient.appointments.all().order_by('-scheduled_time')
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Appointment model with status management."""
    queryset = Appointment.objects.all()
    permission_classes = [ClinicAppointmentPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AppointmentFilter
    search_fields = ['patient__first_name', 'patient__last_name', 'provider__username']
    ordering_fields = ['scheduled_time', 'created_at']
    ordering = ['scheduled_time']

    def get_queryset(self):
        """Filter appointments based on user's clinic and role."""
        user = self.request.user
        if user.is_superuser:
            return Appointment.objects.all()

        queryset = Appointment.objects.none()

        if hasattr(user, 'profile') and user.profile.clinic:
            # Base filter by clinic
            queryset = Appointment.objects.filter(clinic=user.profile.clinic)

            # Additional filters based on role
            if user.profile.role == 'provider':
                # Providers see their own appointments + unassigned
                queryset = queryset.filter(
                    Q(provider=user) | Q(provider__isnull=True)
                )

        return queryset.select_related('patient', 'clinic', 'provider', 'status').prefetch_related('flow_events')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return AppointmentCreateUpdateSerializer
        elif self.action == 'retrieve':
            return AppointmentDetailSerializer
        return AppointmentListSerializer

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update appointment status and create flow event."""
        appointment = self.get_object()
        status_id = request.data.get('status_id')
        notes = request.data.get('notes', '')

        if not status_id:
            return Response({'error': 'status_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = Status.objects.get(id=status_id, clinic=appointment.clinic)
        except Status.DoesNotExist:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Update appointment status
            old_status = appointment.status
            appointment.status = new_status
            appointment.save()

            # Create flow event
            flow_event = PatientFlowEvent.objects.create(
                appointment=appointment,
                status=new_status,
                updated_by=request.user,
                notes=notes
            )

            # Broadcast real-time update
            self.broadcast_status_update(appointment, old_status, new_status, request.user)

        serializer = AppointmentDetailSerializer(appointment)
        return Response(serializer.data)

    def broadcast_status_update(self, appointment, old_status, new_status, user):
        """Broadcast status update via WebSocket."""
        if channel_layer:
            message = {
                'type': 'status_update',
                'appointment_id': appointment.id,
                'patient_name': f"{appointment.patient.first_name} {appointment.patient.last_name}",
                'old_status': old_status.name if old_status else None,
                'new_status': new_status.name,
                'updated_by': user.get_full_name() or user.username,
                'timestamp': timezone.now().isoformat(),
                'clinic_id': appointment.clinic.id
            }

            # Send to clinic group
            group_name = f"clinic_{appointment.clinic.id}"
            async_to_sync(channel_layer.group_send)(group_name, {
                'type': 'send_status_update',
                'message': message
            })

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's appointments."""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(scheduled_time__date=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active appointments (those with flow events today)."""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            flow_events__timestamp__date=today
        ).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update_status(self, request):
        """Bulk update status for multiple appointments."""
        appointment_ids = request.data.get('appointment_ids', [])
        status_id = request.data.get('status_id')
        notes = request.data.get('notes', 'Bulk status update')

        if not appointment_ids or not status_id:
            return Response({'error': 'appointment_ids and status_id are required'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = Status.objects.get(id=status_id)
        except Status.DoesNotExist:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        with transaction.atomic():
            for appointment_id in appointment_ids:
                try:
                    appointment = self.get_queryset().get(id=appointment_id)
                    if appointment.clinic == new_status.clinic:
                        old_status = appointment.status
                        appointment.status = new_status
                        appointment.save()

                        # Create flow event
                        PatientFlowEvent.objects.create(
                            appointment=appointment,
                            status=new_status,
                            updated_by=request.user,
                            notes=notes
                        )

                        # Broadcast update
                        self.broadcast_status_update(appointment, old_status, new_status, request.user)
                        updated_count += 1

                except Appointment.DoesNotExist:
                    continue

        return Response({'updated_count': updated_count})

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get detailed timeline for an appointment."""
        appointment = self.get_object()
        events = appointment.flow_events.all().order_by('timestamp')

        timeline = []
        for i, event in enumerate(events):
            if i < len(events) - 1:
                next_event = events[i + 1]
                duration = next_event.timestamp - event.timestamp
                duration_minutes = round(duration.total_seconds() / 60, 2)
            else:
                duration = timezone.now() - event.timestamp
                duration_minutes = round(duration.total_seconds() / 60, 2)

            timeline.append({
                'status': event.status.name,
                'color': event.status.color,
                'timestamp': event.timestamp,
                'duration_minutes': duration_minutes,
                'updated_by': event.updated_by.get_full_name() if event.updated_by else None,
                'notes': event.notes,
                'is_current': i == len(events) - 1
            })

        return Response(timeline)


class PatientFlowEventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for PatientFlowEvent model (read-only)."""
    queryset = PatientFlowEvent.objects.all()
    serializer_class = PatientFlowEventSerializer
    permission_classes = [FlowEventPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PatientFlowEventFilter
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        """Filter flow events based on user's clinic."""
        user = self.request.user
        if user.is_superuser:
            return PatientFlowEvent.objects.all()

        if hasattr(user, 'profile') and user.profile.clinic:
            return PatientFlowEvent.objects.filter(
                appointment__clinic=user.profile.clinic
            ).select_related('appointment', 'status', 'updated_by')

        return PatientFlowEvent.objects.none()


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for Notification model."""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [NotificationPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = NotificationFilter
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']

    def get_queryset(self):
        """Users see only their own notifications unless admin."""
        user = self.request.user
        if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin'):
            return Notification.objects.all()

        return Notification.objects.filter(recipient=user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all user's notifications as read."""
        updated_count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'updated_count': updated_count})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


class FlowBoardViewSet(viewsets.GenericViewSet):
    """Special viewset for the patient flow board."""
    permission_classes = [PatientFlowStaffPermission]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current flow board for user's clinic."""
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.clinic:
            return Response({'error': 'User not associated with a clinic'},
                          status=status.HTTP_400_BAD_REQUEST)

        clinic = user.profile.clinic
        today = timezone.now().date()

        # Get today's appointments
        appointments = Appointment.objects.filter(
            clinic=clinic,
            scheduled_time__date=today
        ).select_related('patient', 'clinic', 'provider', 'status').prefetch_related('flow_events')

        # Get clinic statuses
        statuses = Status.objects.filter(clinic=clinic, is_active=True).order_by('order')

        # Prepare data for serializer
        data = {
            'clinic': clinic,
            'appointments': appointments,
            'statuses': statuses
        }

        serializer = FlowBoardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for the flow board."""
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.clinic:
            return Response({'error': 'User not associated with a clinic'},
                          status=status.HTTP_400_BAD_REQUEST)

        clinic = user.profile.clinic
        today = timezone.now().date()

        # Calculate summary metrics
        total_appointments = clinic.appointments.filter(scheduled_time__date=today).count()
        active_appointments = clinic.appointments.filter(
            scheduled_time__date=today,
            flow_events__timestamp__date=today
        ).distinct().count()

        # Average wait time
        wait_times = []
        for appointment in clinic.appointments.filter(scheduled_time__date=today):
            if appointment.flow_events.exists():
                first_event = appointment.flow_events.first()
                wait_time = timezone.now() - first_event.timestamp
                wait_times.append(wait_time.total_seconds() / 60)

        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0

        # Status breakdown
        status_breakdown = {}
        for appointment in clinic.appointments.filter(scheduled_time__date=today):
            if appointment.status:
                status_name = appointment.status.name
                if status_name not in status_breakdown:
                    status_breakdown[status_name] = 0
                status_breakdown[status_name] += 1

        summary = {
            'total_appointments': total_appointments,
            'active_appointments': active_appointments,
            'average_wait_time_minutes': round(avg_wait_time, 2),
            'status_breakdown': status_breakdown,
            'last_updated': timezone.now()
        }

        return Response(summary)


class AnalyticsViewSet(viewsets.GenericViewSet):
    """ViewSet for analytics and reporting."""
    permission_classes = [PatientFlowStaffPermission]

    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Get daily flow analytics."""
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.clinic:
            return Response({'error': 'User not associated with a clinic'},
                          status=status.HTTP_400_BAD_REQUEST)

        clinic = user.profile.clinic
        date_str = request.query_params.get('date', timezone.now().date().isoformat())

        try:
            target_date = timezone.datetime.fromisoformat(date_str).date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        # Get appointments for the target date
        appointments = clinic.appointments.filter(scheduled_time__date=target_date)

        # Calculate metrics
        total_appointments = appointments.count()
        completed_appointments = appointments.filter(
            flow_events__status__name__icontains='completed'
        ).distinct().count()

        # Time analysis
        time_data = []
        for appointment in appointments:
            events = appointment.flow_events.filter(timestamp__date=target_date)
            if events.exists():
                first_event = events.first()
                last_event = events.last()
                total_time = last_event.timestamp - first_event.timestamp
                time_data.append({
                    'appointment_id': appointment.id,
                    'patient_name': f"{appointment.patient.first_name} {appointment.patient.last_name}",
                    'total_time_minutes': round(total_time.total_seconds() / 60, 2),
                    'status_changes': events.count(),
                })

        avg_time = sum([d['total_time_minutes'] for d in time_data]) / len(time_data) if time_data else 0

        # Status distribution
        status_counts = PatientFlowEvent.objects.filter(
            appointment__clinic=clinic,
            timestamp__date=target_date
        ).values('status__name').annotate(count=Count('id'))

        report = {
            'date': target_date.isoformat(),
            'clinic': clinic.name,
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'completion_rate': (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            'average_time_minutes': round(avg_time, 2),
            'status_distribution': list(status_counts),
            'appointment_details': time_data,
        }

        return Response(report)

    @action(detail=False, methods=['get'])
    def weekly_trends(self, request):
        """Get weekly trend analysis."""
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.clinic:
            return Response({'error': 'User not associated with a clinic'},
                          status=status.HTTP_400_BAD_REQUEST)

        clinic = user.profile.clinic

        # Get last 7 days of data
        from datetime import timedelta
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

        daily_data = []
        current_date = start_date

        while current_date <= end_date:
            appointments = clinic.appointments.filter(scheduled_time__date=current_date)
            total = appointments.count()
            completed = appointments.filter(
                flow_events__status__name__icontains='completed'
            ).distinct().count()

            daily_data.append({
                'date': current_date.isoformat(),
                'total_appointments': total,
                'completed_appointments': completed,
                'completion_rate': (completed / total * 100) if total > 0 else 0,
            })

            current_date += timedelta(days=1)

        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'daily_data': daily_data,
        })
