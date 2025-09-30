import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from aura.users.models import TherapistProfile

User = get_user_model()


class TherapistAvailability(models.Model):
    """Model to manage therapist availability schedules"""

    WEEKDAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name="availability_slots")
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["therapist", "weekday", "start_time"]
        indexes = [
            models.Index(fields=["therapist", "weekday", "is_available"]),
        ]

    def __str__(self):
        return f"{self.therapist.user.email} - {self.get_weekday_display()}: {self.start_time}-{self.end_time}"

    def clean(self):
        if self.start_time >= self.end_time:
            msg = "Start time must be before end time"
            raise ValidationError(msg)


class AvailabilityException(models.Model):
    """Model to handle availability exceptions (vacations, holidays, etc.)"""

    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name="availability_exceptions")
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(default=False)
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["therapist", "date", "start_time"]
        indexes = [
            models.Index(fields=["therapist", "date"]),
        ]

    def __str__(self):
        return f"{self.therapist.user.email} - {self.date}: {'Available' if self.is_available else 'Unavailable'}"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            msg = "Start time must be before end time"
            raise ValidationError(msg)


class Appointment(models.Model):
    """Model for therapy appointments"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
        ("rescheduled", "Rescheduled"),
    ]

    SESSION_TYPE_CHOICES = [
        ("video", "Video"),
        ("audio", "Audio"),
        ("in_person", "In-Person"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("authorized", "Authorized"),
        ("captured", "Captured"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="patient_appointments")
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="therapist_appointments")
    session_datetime = models.DateTimeField()
    session_duration = models.IntegerField(default=60)  # minutes
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default="video")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)

    # Payment information
    payment_intent_id = models.CharField(max_length=100, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Session links and metadata
    session_link = models.URLField(blank=True)
    session_metadata = models.JSONField(default=dict, blank=True)

    # Notifications
    confirmation_sent = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointments"
        indexes = [
            models.Index(fields=["patient", "session_datetime"]),
            models.Index(fields=["therapist", "session_datetime"]),
            models.Index(fields=["status", "session_datetime"]),
            models.Index(fields=["session_datetime", "status"]),
        ]

    def __str__(self):
        return f"Appointment {self.id} - {self.patient.email} with {self.therapist.email} on {self.session_datetime}"

    def clean(self):
        # Validate session is in the future
        if self.session_datetime and self.session_datetime <= timezone.now():
            msg = "Session must be scheduled for a future time"
            raise ValidationError(msg)

        # Validate session duration
        if self.session_duration not in [30, 45, 60, 90]:
            msg = "Session duration must be 30, 45, 60, or 90 minutes"
            raise ValidationError(msg)

    @property
    def session_end_datetime(self):
        """Calculate session end time"""
        return self.session_datetime + timedelta(minutes=self.session_duration)

    @property
    def can_be_cancelled(self):
        """Check if appointment can be cancelled (24+ hours before session)"""
        return self.status in ["pending", "confirmed"] and self.session_datetime > timezone.now() + timedelta(hours=24)

    @property
    def can_be_rescheduled(self):
        """Check if appointment can be rescheduled"""
        return self.status in ["pending", "confirmed"] and self.session_datetime > timezone.now() + timedelta(hours=24)


class AppointmentReschedule(models.Model):
    """Model to track appointment reschedule history"""

    original_appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="reschedule_history")
    old_datetime = models.DateTimeField()
    new_datetime = models.DateTimeField()
    reason = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requested_reschedules")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reschedule {self.original_appointment.id}: {self.old_datetime} -> {self.new_datetime}"


class AppointmentCancellation(models.Model):
    """Model to track appointment cancellations"""

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="cancellation")
    reason = models.TextField()
    cancelled_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cancelled_appointments")
    refund_requested = models.BooleanField(default=False)
    refund_processed = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation for {self.appointment.id}"
