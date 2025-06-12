from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, Any, Optional

from .models import (
    Clinic, Status, Patient, Appointment,
    PatientFlowEvent, Notification, UserProfile
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with limited fields for privacy."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = ['id', 'username']

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    user = UserSerializer(read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['user', 'clinic', 'clinic_name', 'role']
        read_only_fields = ['user']


class ClinicSerializer(serializers.ModelSerializer):
    """Serializer for Clinic model."""
    patient_count = serializers.SerializerMethodField()
    active_appointments_count = serializers.SerializerMethodField()
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Clinic
        fields = [
            'id', 'name', 'address', 'is_active', 'created_at', 'updated_at',
            'patient_count', 'active_appointments_count', 'staff_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_patient_count(self, obj) -> int:
        return obj.patients.count()

    def get_active_appointments_count(self, obj) -> int:
        today = timezone.now().date()
        return obj.appointments.filter(scheduled_time__date=today).count()

    def get_staff_count(self, obj) -> int:
        return obj.user_profiles.count()


class StatusSerializer(serializers.ModelSerializer):
    """Serializer for Status model."""
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    appointment_count = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = [
            'id', 'name', 'color', 'order', 'is_active', 'clinic', 'clinic_name',
            'created_at', 'updated_at', 'appointment_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_appointment_count(self, obj) -> int:
        """Get count of appointments currently in this status."""
        return obj.appointments.count()

    def validate_color(self, value: str) -> str:
        """Validate hex color format."""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color (e.g., #FFFFFF)")
        return value


class PatientSerializer(serializers.ModelSerializer):
    """Serializer for Patient model."""
    full_name = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    appointment_count = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'dob', 'clinic', 'clinic_name',
            'created_at', 'updated_at', 'appointment_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"

    def get_appointment_count(self, obj) -> int:
        return obj.appointments.count()


class PatientFlowEventSerializer(serializers.ModelSerializer):
    """Serializer for PatientFlowEvent model."""
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_color = serializers.CharField(source='status.color', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = PatientFlowEvent
        fields = [
            'id', 'appointment', 'status', 'status_name', 'status_color',
            'timestamp', 'updated_by', 'updated_by_name', 'notes', 'duration_minutes'
        ]
        read_only_fields = ['id', 'timestamp']

    def get_duration_minutes(self, obj) -> Optional[float]:
        """Calculate duration in this status in minutes."""
        # Get the next event for this appointment
        next_event = PatientFlowEvent.objects.filter(
            appointment=obj.appointment,
            timestamp__gt=obj.timestamp
        ).first()

        if next_event:
            duration = next_event.timestamp - obj.timestamp
            return round(duration.total_seconds() / 60, 2)
        else:
            # Still in this status
            duration = timezone.now() - obj.timestamp
            return round(duration.total_seconds() / 60, 2)


class AppointmentListSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model in list views."""
    patient_name = serializers.CharField(source='patient.first_name', read_only=True)
    patient_last_name = serializers.CharField(source='patient.last_name', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_color = serializers.CharField(source='status.color', read_only=True)
    time_in_system_minutes = serializers.SerializerMethodField()
    current_status_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_last_name',
            'clinic', 'clinic_name', 'scheduled_time', 'provider', 'provider_name',
            'status', 'status_name', 'status_color', 'external_id',
            'time_in_system_minutes', 'current_status_duration_minutes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_time_in_system_minutes(self, obj) -> Optional[float]:
        """Total time patient has been in the system."""
        if obj.flow_events.exists():
            first_event = obj.flow_events.first()
            duration = timezone.now() - first_event.timestamp
            return round(duration.total_seconds() / 60, 2)
        return None

    def get_current_status_duration_minutes(self, obj) -> Optional[float]:
        """Time in current status."""
        if obj.flow_events.exists():
            latest_event = obj.flow_events.last()
            duration = timezone.now() - latest_event.timestamp
            return round(duration.total_seconds() / 60, 2)
        return None


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Appointment model."""
    patient = PatientSerializer(read_only=True)
    clinic = ClinicSerializer(read_only=True)
    provider = UserSerializer(read_only=True)
    status = StatusSerializer(read_only=True)
    flow_events = PatientFlowEventSerializer(many=True, read_only=True)
    time_in_system_minutes = serializers.SerializerMethodField()
    status_history = serializers.SerializerMethodField()
    analytics = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'clinic', 'scheduled_time', 'provider', 'status',
            'external_id', 'flow_events', 'time_in_system_minutes', 'status_history',
            'analytics', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_time_in_system_minutes(self, obj) -> Optional[float]:
        """Total time patient has been in the system."""
        if obj.flow_events.exists():
            first_event = obj.flow_events.first()
            duration = timezone.now() - first_event.timestamp
            return round(duration.total_seconds() / 60, 2)
        return None

    def get_status_history(self, obj) -> list:
        """Get status history with durations."""
        events = obj.flow_events.all()
        history = []

        for i, event in enumerate(events):
            if i < len(events) - 1:
                next_event = events[i + 1]
                duration = next_event.timestamp - event.timestamp
                duration_minutes = round(duration.total_seconds() / 60, 2)
            else:
                # Current status
                duration = timezone.now() - event.timestamp
                duration_minutes = round(duration.total_seconds() / 60, 2)

            history.append({
                'status': event.status.name,
                'color': event.status.color,
                'timestamp': event.timestamp,
                'duration_minutes': duration_minutes,
                'updated_by': event.updated_by.get_full_name() if event.updated_by else None,
                'notes': event.notes
            })

        return history

    def get_analytics(self, obj) -> Dict[str, Any]:
        """Get analytics for this appointment."""
        events = obj.flow_events.all()
        if not events:
            return {}

        total_time = timezone.now() - events.first().timestamp
        status_counts = {}

        for event in events:
            status_name = event.status.name
            if status_name not in status_counts:
                status_counts[status_name] = 0
            status_counts[status_name] += 1

        return {
            'total_time_minutes': round(total_time.total_seconds() / 60, 2),
            'total_status_changes': events.count(),
            'status_distribution': status_counts,
            'average_time_per_status': round(total_time.total_seconds() / 60 / events.count(), 2) if events.count() > 0 else 0
        }


class AppointmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating appointments."""

    class Meta:
        model = Appointment
        fields = [
            'patient', 'clinic', 'scheduled_time', 'provider', 'status', 'external_id'
        ]

    def validate(self, data):
        """Validate appointment data."""
        # Ensure patient belongs to the same clinic
        if 'patient' in data and 'clinic' in data:
            if data['patient'].clinic != data['clinic']:
                raise serializers.ValidationError("Patient must belong to the selected clinic")

        # Ensure status belongs to the same clinic
        if 'status' in data and 'clinic' in data:
            if data['status'].clinic != data['clinic']:
                raise serializers.ValidationError("Status must belong to the selected clinic")

        return data


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    event_details = serializers.SerializerMethodField()
    delivery_methods = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'event', 'event_details',
            'message', 'is_read', 'sent_at', 'read_at', 'delivery_methods'
        ]
        read_only_fields = ['id', 'sent_at']

    def get_event_details(self, obj) -> Dict[str, Any]:
        """Get event details for the notification."""
        event = obj.event
        return {
            'appointment_id': event.appointment.id,
            'patient_name': f"{event.appointment.patient.first_name} {event.appointment.patient.last_name}",
            'status': event.status.name,
            'timestamp': event.timestamp,
            'clinic': event.appointment.clinic.name
        }

    def get_delivery_methods(self, obj) -> list:
        """Get delivery methods used."""
        methods = ['in_app']
        if obj.via_email:
            methods.append('email')
        if obj.via_sms:
            methods.append('sms')
        return methods


class FlowBoardSerializer(serializers.Serializer):
    """Serializer for the patient flow board view."""
    clinic = ClinicSerializer(read_only=True)
    statuses = StatusSerializer(many=True, read_only=True)
    appointments_by_status = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    def get_appointments_by_status(self, obj) -> Dict[str, list]:
        """Group appointments by status."""
        clinic = obj['clinic']
        appointments = obj['appointments']
        statuses = obj['statuses']

        result = {}

        # Initialize all statuses
        for status in statuses:
            result[status.name] = []

        # Add appointments to their respective statuses
        for appointment in appointments:
            if appointment.status:
                status_name = appointment.status.name
                if status_name in result:
                    serializer = AppointmentListSerializer(appointment)
                    result[status_name].append(serializer.data)

        return result

    def get_summary(self, obj) -> Dict[str, Any]:
        """Get summary statistics for the flow board."""
        appointments = obj['appointments']
        total_appointments = len(appointments)

        # Calculate averages
        total_time_minutes = 0
        active_appointments = 0

        for appointment in appointments:
            if appointment.flow_events.exists():
                first_event = appointment.flow_events.first()
                time_in_system = timezone.now() - first_event.timestamp
                total_time_minutes += time_in_system.total_seconds() / 60
                active_appointments += 1

        avg_time_minutes = total_time_minutes / active_appointments if active_appointments > 0 else 0

        return {
            'total_appointments': total_appointments,
            'active_appointments': active_appointments,
            'average_time_minutes': round(avg_time_minutes, 2),
            'last_updated': timezone.now()
        }
