import uuid
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from aura.users.models import TherapistProfile
from aura.users.models import User

from .appointments import Appointment
from .appointments import AvailabilityException
from .appointments import TherapistAvailability


class AppointmentBookingService:
    """Service for handling appointment bookings with business logic validation"""

    def __init__(self, patient: User, therapist: User, session_datetime: datetime):
        self.patient = patient
        self.therapist = therapist
        self.session_datetime = session_datetime
        self.therapist_profile = None

        # Get therapist profile
        try:
            self.therapist_profile = TherapistProfile.objects.get(user=therapist)
        except TherapistProfile.DoesNotExist:
            raise ValidationError("Therapist profile not found")

    @transaction.atomic
    def book_appointment(self, **kwargs) -> Appointment:
        """
        Book an appointment with full validation

        Args:
            session_duration: Duration in minutes
            session_type: Type of session (video, audio, in_person)
            notes: Optional notes
            payment_method_id: Payment method ID for processing

        Returns:
            Created Appointment object

        Raises:
            ValidationError: If booking validation fails
        """
        session_duration = kwargs.get("session_duration", 60)
        session_type = kwargs.get("session_type", "video")
        notes = kwargs.get("notes", "")
        payment_method_id = kwargs.get("payment_method_id")

        # 1. Validate availability
        if not self._is_time_available():
            raise ValidationError("Time slot not available")

        # 2. Check advance booking limit
        if not self._within_booking_window():
            raise ValidationError("Booking too far in advance")

        # 3. Validate business hours
        if not self._within_business_hours():
            raise ValidationError("Session outside therapist's available hours")

        # 4. Calculate amount
        amount = self._calculate_amount(session_duration)

        # 5. Authorize payment (mock implementation)
        payment_intent_id = self._authorize_payment(payment_method_id, amount)

        # 6. Create appointment
        appointment = Appointment.objects.create(
            patient=self.patient,
            therapist=self.therapist,
            session_datetime=self.session_datetime,
            session_duration=session_duration,
            session_type=session_type,
            notes=notes,
            payment_intent_id=payment_intent_id,
            payment_status="authorized",
            amount=amount,
            status="confirmed",
        )

        # 7. Generate session link
        if session_type in ["video", "audio"]:
            appointment.session_link = self._generate_session_link(appointment)
            appointment.save()

        # 8. Send confirmations
        self._send_confirmations(appointment)

        # 9. Update appointment status
        appointment.confirmation_sent = True
        appointment.save()

        return appointment

    def _is_time_available(self) -> bool:
        """Check if the requested time slot is available"""
        session_end = self.session_datetime + timedelta(minutes=60)  # Default duration for checking

        # Check for conflicting appointments
        conflicting_appointments = (
            Appointment.objects.filter(
                therapist=self.therapist,
                status__in=["confirmed", "pending"],
                session_datetime__lt=session_end,
            )
            .filter(session_datetime__gte=self.session_datetime - timedelta(minutes=60))
            .exists()
        )

        if conflicting_appointments:
            return False

        # Check availability exceptions (vacations, etc.)
        date = self.session_datetime.date()
        time = self.session_datetime.time()

        exceptions = AvailabilityException.objects.filter(therapist=self.therapist_profile, date=date)

        for exception in exceptions:
            if not exception.is_available:
                if not exception.start_time or not exception.end_time:
                    # Full day unavailable
                    return False
                if exception.start_time <= time <= exception.end_time:
                    # Time range unavailable
                    return False

        return True

    def _within_booking_window(self) -> bool:
        """Check if booking is within allowed advance booking window"""
        now = timezone.now()

        # Must be at least 1 hour in the future
        if self.session_datetime <= now + timedelta(hours=1):
            return False

        # Must be within 30 days (can be configured per therapist)
        advance_booking_days = getattr(self.therapist_profile, "advance_booking_days", 30)
        max_advance = now + timedelta(days=advance_booking_days)

        return self.session_datetime <= max_advance

    def _within_business_hours(self) -> bool:
        """Check if session time is within therapist's business hours"""
        weekday = self.session_datetime.weekday()
        time = self.session_datetime.time()

        # Check regular availability
        availability_slots = TherapistAvailability.objects.filter(
            therapist=self.therapist_profile,
            weekday=weekday,
            is_available=True,
            start_time__lte=time,
            end_time__gt=time,
        ).exists()

        return availability_slots

    def _calculate_amount(self, session_duration: int) -> float:
        """Calculate session amount based on therapist's rate"""
        base_rate = float(self.therapist_profile.base_rate or 100)

        # Adjust for session duration
        if session_duration == 30:
            return base_rate * 0.6
        if session_duration == 45:
            return base_rate * 0.8
        if session_duration == 90:
            return base_rate * 1.5
        # 60 minutes
        return base_rate

    def _authorize_payment(self, payment_method_id: str, amount: float) -> str:
        """
        Authorize payment (mock implementation)
        In production, this would integrate with Stripe or similar payment processor
        """
        if not payment_method_id:
            raise ValidationError("Payment method is required")

        # Mock payment authorization
        # In reality, you would:
        # 1. Create payment intent with Stripe
        # 2. Authorize the amount
        # 3. Return the payment intent ID

        return f"pi_mock_{uuid.uuid4().hex[:16]}"

    def _generate_session_link(self, appointment: Appointment) -> str:
        """Generate session link for video/audio sessions"""
        # Mock session link generation
        # In production, this would integrate with video conferencing service
        session_id = f"session_{appointment.id.hex[:12]}"
        return f"https://sessions.aura.com/join/{session_id}"

    def _send_confirmations(self, appointment: Appointment) -> None:
        """Send confirmation emails/notifications"""
        # Mock implementation
        # In production, this would:
        # 1. Send email confirmations to both patient and therapist
        # 2. Add calendar events
        # 3. Schedule reminder notifications

    @staticmethod
    def get_calendar_links(appointment: Appointment) -> dict[str, str]:
        """Generate calendar links for appointment"""
        start_time = appointment.session_datetime.strftime("%Y%m%dT%H%M%S")
        end_time = appointment.session_end_datetime.strftime("%Y%m%dT%H%M%S")

        title = f"Therapy Session with Dr. {appointment.therapist.first_name} {appointment.therapist.last_name}"
        description = (
            f"Session Type: {appointment.get_session_type_display()}\\nDuration: {appointment.session_duration} minutes"
        )

        if appointment.session_link:
            description += f"\\nJoin Link: {appointment.session_link}"

        # Google Calendar link
        google_link = (
            f"https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={title}"
            f"&dates={start_time}/{end_time}"
            f"&details={description}"
        )

        # Outlook link
        outlook_link = (
            f"https://outlook.com/calendar/deeplink/compose?subject={title}"
            f"&startdt={start_time}"
            f"&enddt={end_time}"
            f"&body={description}"
        )

        return {"google": google_link, "outlook": outlook_link}


class AppointmentManagementService:
    """Service for managing existing appointments (reschedule, cancel, etc.)"""

    @staticmethod
    @transaction.atomic
    def reschedule_appointment(
        appointment: Appointment, new_datetime: datetime, reason: str, requested_by: User
    ) -> Appointment:
        """Reschedule an existing appointment"""
        from .appointments import AppointmentReschedule

        if not appointment.can_be_rescheduled:
            raise ValidationError("Appointment cannot be rescheduled")

        # Store old datetime
        old_datetime = appointment.session_datetime

        # Validate new time slot
        booking_service = AppointmentBookingService(
            patient=appointment.patient, therapist=appointment.therapist, session_datetime=new_datetime
        )

        if not booking_service._is_time_available():
            raise ValidationError("New time slot is not available")

        # Update appointment
        appointment.session_datetime = new_datetime
        appointment.status = "confirmed"
        appointment.save()

        # Create reschedule record
        AppointmentReschedule.objects.create(
            original_appointment=appointment,
            old_datetime=old_datetime,
            new_datetime=new_datetime,
            reason=reason,
            requested_by=requested_by,
        )

        return appointment

    @staticmethod
    @transaction.atomic
    def cancel_appointment(
        appointment: Appointment, reason: str, cancelled_by: User, refund_requested: bool = True
    ) -> dict[str, Any]:
        """Cancel an existing appointment"""
        from .appointments import AppointmentCancellation

        if not appointment.can_be_cancelled:
            raise ValidationError("Appointment cannot be cancelled")

        # Update appointment status
        appointment.status = "cancelled"
        appointment.save()

        # Create cancellation record
        cancellation = AppointmentCancellation.objects.create(
            appointment=appointment, reason=reason, cancelled_by=cancelled_by, refund_requested=refund_requested
        )

        # Process refund if requested and within policy
        refund_amount = None
        if refund_requested:
            hours_before = (appointment.session_datetime - timezone.now()).total_seconds() / 3600

            if hours_before >= 24:
                # Full refund for 24+ hours notice
                refund_amount = float(appointment.amount)
            elif hours_before >= 12:
                # Partial refund for 12-24 hours notice
                refund_amount = float(appointment.amount) * 0.5

            if refund_amount:
                # Mock refund processing
                cancellation.refund_processed = True
                cancellation.refund_amount = refund_amount
                cancellation.save()

        return {
            "status": "cancelled",
            "refund_processed": cancellation.refund_processed,
            "refund_amount": refund_amount,
        }
