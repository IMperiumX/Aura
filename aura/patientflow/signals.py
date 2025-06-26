from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Optional
import json
import logging

from .models import (
    UserProfile, Appointment, PatientFlowEvent,
    Notification, Status, Patient
)
from .tasks import send_notification_email, send_notification_sms
from aura import analytics

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=Patient)
def track_patient_creation(sender, instance, created, **kwargs):
    """Track patient creation events."""
    if created:
        try:
            # Get the user who created this patient (if available in context)
            created_by_user_id = getattr(instance, '_created_by_user_id', None)

            analytics.record(
                "patient.created",
                instance=instance,
                patient_id=instance.id,
                clinic_id=instance.clinic.id if instance.clinic else None,
                first_name=instance.first_name,
                last_name=instance.last_name,
                email=getattr(instance, 'email', '') or '',
                created_by_user_id=created_by_user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to record patient creation event: {e}")


@receiver(post_save, sender=Appointment)
def track_appointment_creation(sender, instance, created, **kwargs):
    """Track appointment creation events."""
    if created:
        try:
            # Get the user who created this appointment (if available in context)
            created_by_user_id = getattr(instance, '_created_by_user_id', None)

            analytics.record(
                "appointment.created",
                instance=instance,
                appointment_id=instance.id,
                patient_id=instance.patient.id,
                clinic_id=instance.clinic.id,
                provider_id=instance.provider.id if instance.provider else None,
                scheduled_time=instance.scheduled_time.isoformat(),
                created_by_user_id=created_by_user_id,
                external_id=instance.external_id,
            )
        except Exception as e:
            logger.warning(f"Failed to record appointment creation event: {e}")


@receiver(pre_save, sender=Appointment)
def track_appointment_status_change(sender, instance, **kwargs):
    """Track status changes and create PatientFlowEvent."""
    if instance.pk:  # Existing appointment
        try:
            old_instance = Appointment.objects.get(pk=instance.pk)
            if old_instance.status != instance.status and instance.status:
                # Status changed, create flow event in post_save
                instance._status_changed = True
                instance._old_status = old_instance.status
                instance._status_change_time = timezone.now()

                # Calculate duration in previous status
                if old_instance.status:
                    # Find the most recent flow event for the old status
                    latest_flow_event = PatientFlowEvent.objects.filter(
                        appointment=instance,
                        status=old_instance.status
                    ).order_by('-timestamp').first()

                    if latest_flow_event:
                        duration = instance._status_change_time - latest_flow_event.timestamp
                        instance._duration_in_status = int(duration.total_seconds() / 60)  # Minutes

        except Appointment.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"Failed to track appointment status change: {e}")


@receiver(post_save, sender=Appointment)
def create_flow_event_on_status_change(sender, instance, created, **kwargs):
    """Create PatientFlowEvent when appointment status changes."""
    if created and instance.status:
        # New appointment with initial status
        flow_event = PatientFlowEvent.objects.create(
            appointment=instance,
            status=instance.status,
            notes=f"Initial status set to {instance.status.name}"
        )
        generate_notifications_for_flow_event(flow_event)

    elif hasattr(instance, '_status_changed') and instance._status_changed:
        # Status changed on existing appointment
        changed_by_user_id = getattr(instance, '_changed_by_user_id', None)

        flow_event = PatientFlowEvent.objects.create(
            appointment=instance,
            status=instance.status,
            updated_by_id=changed_by_user_id,
            notes=f"Status changed from {instance._old_status.name if instance._old_status else 'None'} to {instance.status.name}"
        )
        generate_notifications_for_flow_event(flow_event)

        # Record analytics event for status change
        try:
            analytics.record(
                "appointment.status_changed",
                instance=instance,
                appointment_id=instance.id,
                patient_id=instance.patient.id,
                clinic_id=instance.clinic.id,
                old_status=instance._old_status.name if instance._old_status else None,
                new_status=instance.status.name,
                changed_by_user_id=changed_by_user_id,
                duration_in_status_minutes=getattr(instance, '_duration_in_status', None),
            )
        except Exception as e:
            logger.warning(f"Failed to record appointment status change event: {e}")


def generate_notifications_for_flow_event(flow_event: PatientFlowEvent):
    """Generate notifications based on flow event and business rules."""
    appointment = flow_event.appointment
    status = flow_event.status
    clinic = appointment.clinic

    # Get all users who should be notified
    notification_recipients = []

    # Rule 1: Notify all clinic staff
    clinic_staff = User.objects.filter(
        profile__clinic=clinic,
        profile__role__in=['front_desk', 'nurse', 'provider', 'admin']
    )
    notification_recipients.extend(clinic_staff)

    # Rule 2: Always notify the provider if assigned
    if appointment.provider:
        notification_recipients.append(appointment.provider)

    # Rule 3: Notify front desk for check-in/check-out statuses
    if status.name.lower() in ['checked in', 'ready for checkout', 'checked out']:
        front_desk_staff = User.objects.filter(
            profile__clinic=clinic,
            profile__role='front_desk'
        )
        notification_recipients.extend(front_desk_staff)

    # Rule 4: Notify nurses for 'waiting for provider' status
    if status.name.lower() in ['waiting for provider', 'ready for nurse']:
        nurses = User.objects.filter(
            profile__clinic=clinic,
            profile__role='nurse'
        )
        notification_recipients.extend(nurses)

    # Remove duplicates
    notification_recipients = list(set(notification_recipients))

    # Create notifications
    for recipient in notification_recipients:
        message = generate_notification_message(flow_event, recipient)

        notification = Notification.objects.create(
            recipient=recipient,
            event=flow_event,
            message=message,
            via_email=should_send_email(recipient, flow_event),
            via_sms=should_send_sms(recipient, flow_event)
        )

        # Send external notifications asynchronously
        if notification.via_email:
            send_notification_email.delay(notification.id)

        if notification.via_sms:
            send_notification_sms.delay(notification.id)

        # Record notification analytics event
        try:
            if notification.via_email:
                analytics.record(
                    "notification.sent",
                    notification_id=notification.id,
                    recipient_id=recipient.id,
                    notification_type='appointment_status_change',
                    delivery_method='email',
                    related_object_type='appointment',
                    related_object_id=appointment.id,
                    success=True,  # Assume success since we're sending async
                )

            if notification.via_sms:
                analytics.record(
                    "notification.sent",
                    notification_id=notification.id,
                    recipient_id=recipient.id,
                    notification_type='appointment_status_change',
                    delivery_method='sms',
                    related_object_type='appointment',
                    related_object_id=appointment.id,
                    success=True,  # Assume success since we're sending async
                )
        except Exception as e:
            logger.warning(f"Failed to record notification event: {e}")


def generate_notification_message(flow_event: PatientFlowEvent, recipient: User) -> str:
    """Generate personalized notification message."""
    appointment = flow_event.appointment
    patient = appointment.patient
    status = flow_event.status

    base_message = f"Patient {patient.first_name} {patient.last_name} is now '{status.name}'"

    # Add time information
    time_info = f" at {flow_event.timestamp.strftime('%H:%M')}"

    # Add location if relevant
    location_info = ""
    if appointment.clinic:
        location_info = f" in {appointment.clinic.name}"

    # Add provider info if relevant
    provider_info = ""
    if appointment.provider and appointment.provider != recipient:
        provider_info = f" (Provider: {appointment.provider.get_full_name() or appointment.provider.username})"

    # Add role-specific information
    role_specific = ""
    if hasattr(recipient, 'profile'):
        if recipient.profile.role == 'front_desk':
            if status.name.lower() in ['ready for checkout', 'checked out']:
                role_specific = " - Action may be required"
        elif recipient.profile.role == 'nurse':
            if status.name.lower() in ['ready for nurse', 'waiting for provider']:
                role_specific = " - Please assess patient"
        elif recipient.profile.role == 'provider':
            if status.name.lower() in ['waiting for provider', 'ready for provider']:
                role_specific = " - Patient ready for consultation"

    return f"{base_message}{time_info}{location_info}{provider_info}{role_specific}"


def should_send_email(recipient: User, flow_event: PatientFlowEvent) -> bool:
    """Determine if email notification should be sent."""
    # Complex business rules for email notifications

    # Always send email for critical statuses
    critical_statuses = ['emergency', 'urgent', 'delayed', 'no show']
    if flow_event.status.name.lower() in critical_statuses:
        return True

    # Send email for providers when their patients are ready
    if (hasattr(recipient, 'profile') and
        recipient.profile.role == 'provider' and
        flow_event.appointment.provider == recipient and
        flow_event.status.name.lower() in ['waiting for provider', 'ready for provider']):
        return True

    # Send email for admin role always
    if hasattr(recipient, 'profile') and recipient.profile.role == 'admin':
        return True

    # Check if it's after hours (assuming 8 AM - 6 PM are normal hours)
    current_hour = timezone.now().hour
    if current_hour < 8 or current_hour > 18:
        return True

    return False


def should_send_sms(recipient: User, flow_event: PatientFlowEvent) -> bool:
    """Determine if SMS notification should be sent."""
    # SMS only for critical/urgent situations

    # Emergency statuses
    emergency_statuses = ['emergency', 'code blue', 'urgent', 'critical']
    if flow_event.status.name.lower() in emergency_statuses:
        return True

    # Major delays (if patient has been in system for more than 2 hours)
    if flow_event.appointment.flow_events.exists():
        first_event = flow_event.appointment.flow_events.first()
        time_in_system = timezone.now() - first_event.timestamp
        if time_in_system.total_seconds() > 7200:  # 2 hours
            return True

    # Provider-specific urgent notifications
    if (hasattr(recipient, 'profile') and
        recipient.profile.role == 'provider' and
        flow_event.appointment.provider == recipient and
        flow_event.status.name.lower() in ['emergency', 'urgent', 'stat']):
        return True

    return False
