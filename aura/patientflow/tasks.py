import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(self, notification_id: int):
    """Send email notification with retry logic."""
    try:
        notification = Notification.objects.get(id=notification_id)
        recipient = notification.recipient

        # Skip if user has no email
        if not recipient.email:
            logger.warning(f"User {recipient.username} has no email address")
            return

        # Prepare email content
        subject = f"Patient Flow Update - {notification.event.appointment.clinic.name}"

        # Use template for HTML email
        html_message = render_to_string(
            "patientflow/email/notification.html",
            {
                "notification": notification,
                "appointment": notification.event.appointment,
                "patient": notification.event.appointment.patient,
                "status": notification.event.status,
                "recipient": recipient,
                "clinic": notification.event.appointment.clinic,
            },
        )

        # Plain text version
        plain_message = notification.message

        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(
            f"Email notification sent to {recipient.email} for notification {notification_id}",
        )

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return

    except Exception as exc:
        logger.error(f"Failed to send email notification {notification_id}: {exc!s}")
        # Retry the task
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_sms(self, notification_id: int):
    """Send SMS notification via Twilio or similar service."""
    try:
        notification = Notification.objects.get(id=notification_id)
        recipient = notification.recipient

        # Get phone number (assuming it's stored in user profile or user model)
        phone_number = getattr(recipient, "phone", None)
        if hasattr(recipient, "profile"):
            phone_number = getattr(recipient.profile, "phone", phone_number)

        if not phone_number:
            logger.warning(f"User {recipient.username} has no phone number")
            return

        # Prepare SMS content (keep it short)
        message = f"URGENT: {notification.message[:140]}..."  # SMS limit

        # Send SMS using Twilio (you'll need to configure Twilio settings)
        success = send_sms_via_twilio(phone_number, message)

        if success:
            logger.info(
                f"SMS notification sent to {phone_number} for notification {notification_id}",
            )
        else:
            raise Exception("SMS sending failed")

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return

    except Exception as exc:
        logger.error(f"Failed to send SMS notification {notification_id}: {exc!s}")
        # Retry the task
        raise self.retry(exc=exc)


def send_sms_via_twilio(phone_number: str, message: str) -> bool:
    """Send SMS via Twilio API."""
    try:
        # This is a placeholder implementation
        # You would implement actual Twilio integration here

        # Example Twilio implementation:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone_number
        # )

        # For now, just log the message
        logger.info(f"SMS would be sent to {phone_number}: {message}")
        return True

    except Exception as e:
        logger.error(f"Twilio SMS failed: {e!s}")
        return False


@shared_task
def cleanup_old_notifications():
    """Clean up old read notifications (run daily)."""
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=30)

    # Delete read notifications older than 30 days
    deleted_count = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff_date,
    ).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old notifications")
    return deleted_count


@shared_task
def send_delay_alerts():
    """Send alerts for patients who have been in the system too long."""
    from datetime import timedelta

    from .models import Appointment
    from .models import PatientFlowEvent

    # Find appointments with patients in system for more than 2 hours
    two_hours_ago = timezone.now() - timedelta(hours=2)

    delayed_appointments = []

    # Get all active appointments (those with recent flow events)
    recent_events = (
        PatientFlowEvent.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=12),
        )
        .values("appointment_id")
        .distinct()
    )

    for event_data in recent_events:
        appointment = Appointment.objects.get(id=event_data["appointment_id"])
        first_event = appointment.flow_events.first()

        if first_event and first_event.timestamp <= two_hours_ago:
            # Check if not already checked out
            latest_event = appointment.flow_events.last()
            if latest_event.status.name.lower() not in [
                "checked out",
                "completed",
                "cancelled",
            ]:
                delayed_appointments.append(appointment)

    # Send delay notifications
    for appointment in delayed_appointments:
        # Create a special delay notification
        delay_notification = Notification.objects.create(
            recipient=appointment.provider
            or appointment.clinic.user_profiles.filter(role="admin").first().user,
            message=f"DELAY ALERT: Patient {appointment.patient.first_name} {appointment.patient.last_name} has been in system for over 2 hours",
            via_email=True,
            via_sms=True,
        )

        # Send immediately
        send_notification_email.delay(delay_notification.id)
        send_notification_sms.delay(delay_notification.id)

    logger.info(f"Sent delay alerts for {len(delayed_appointments)} appointments")
    return len(delayed_appointments)


@shared_task
def generate_daily_flow_report():
    """Generate daily patient flow analytics report."""
    from django.db.models import Count

    from .models import Appointment
    from .models import PatientFlowEvent

    today = timezone.now().date()

    # Get all appointments from today
    today_appointments = Appointment.objects.filter(
        scheduled_time__date=today,
    )

    # Calculate metrics
    total_appointments = today_appointments.count()
    completed_appointments = (
        today_appointments.filter(
            flow_events__status__name__icontains="completed",
        )
        .distinct()
        .count()
    )

    # Average time in system
    avg_times = []
    for appointment in today_appointments:
        events = appointment.flow_events.all()
        if events.count() >= 2:
            time_in_system = events.last().timestamp - events.first().timestamp
            avg_times.append(time_in_system.total_seconds() / 60)  # minutes

    avg_time_minutes = sum(avg_times) / len(avg_times) if avg_times else 0

    # Status distribution
    status_counts = (
        PatientFlowEvent.objects.filter(
            timestamp__date=today,
        )
        .values("status__name")
        .annotate(count=Count("id"))
    )

    # Prepare report
    report = {
        "date": today.isoformat(),
        "total_appointments": total_appointments,
        "completed_appointments": completed_appointments,
        "completion_rate": (completed_appointments / total_appointments * 100)
        if total_appointments > 0
        else 0,
        "average_time_minutes": round(avg_time_minutes, 2),
        "status_distribution": list(status_counts),
    }

    # Send report to admins
    admin_users = User.objects.filter(profile__role="admin")
    for admin in admin_users:
        if admin.email:
            send_mail(
                subject=f"Daily Patient Flow Report - {today}",
                message=f"Daily Report:\n\n"
                f"Total Appointments: {total_appointments}\n"
                f"Completed: {completed_appointments}\n"
                f"Completion Rate: {report['completion_rate']:.1f}%\n"
                f"Average Time in System: {avg_time_minutes:.1f} minutes\n",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=True,
            )

    logger.info(f"Generated daily flow report: {report}")
    return report
