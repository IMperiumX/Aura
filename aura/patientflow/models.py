from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Optional

User = get_user_model()

class Clinic(models.Model):
    """A healthcare clinic or facility."""
    name: str = models.CharField(max_length=255, unique=True)
    address: Optional[str] = models.TextField(blank=True)
    is_active: bool = models.BooleanField(default=True)
    created_at: timezone.datetime = models.DateTimeField(auto_now_add=True)
    updated_at: timezone.datetime = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

class Status(models.Model):
    """Customizable patient status for a clinic (e.g., Waiting, With Provider)."""
    clinic: Clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='statuses')
    name: str = models.CharField(max_length=100)
    color: str = models.CharField(max_length=7, default='#FFFFFF')  # Hex color
    order: int = models.PositiveIntegerField(default=0)
    is_active: bool = models.BooleanField(default=True)
    created_at: timezone.datetime = models.DateTimeField(auto_now_add=True)
    updated_at: timezone.datetime = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('clinic', 'name')
        ordering = ['order']

    def __str__(self) -> str:
        return f"{self.clinic.name}: {self.name}"

class Patient(models.Model):
    """Patient record (can be linked to a global patient model if present)."""
    first_name: str = models.CharField(max_length=100)
    last_name: str = models.CharField(max_length=100)
    dob: Optional[timezone.datetime] = models.DateField(null=True, blank=True)
    clinic: Clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='patients')
    # Add more fields as needed (MRN, contact info, etc.)
    created_at: timezone.datetime = models.DateTimeField(auto_now_add=True)
    updated_at: timezone.datetime = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.clinic.name})"

class Appointment(models.Model):
    """Appointment for a patient at a clinic."""
    patient: Patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    clinic: Clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='appointments')
    scheduled_time: timezone.datetime = models.DateTimeField()
    provider: Optional[User] = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    status: Optional[Status] = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    # Integration fields for external scheduling system (if needed)
    external_id: Optional[str] = models.CharField(max_length=255, blank=True, null=True)
    created_at: timezone.datetime = models.DateTimeField(auto_now_add=True)
    updated_at: timezone.datetime = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.patient} @ {self.scheduled_time:%Y-%m-%d %H:%M}"

class PatientFlowEvent(models.Model):
    """Tracks each status change for an appointment (for audit and time tracking)."""
    appointment: Appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='flow_events')
    status: Status = models.ForeignKey(Status, on_delete=models.PROTECT)
    timestamp: timezone.datetime = models.DateTimeField(auto_now_add=True)
    updated_by: Optional[User] = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='flow_events')
    notes: str = models.TextField(blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self) -> str:
        return f"{self.appointment} -> {self.status.name} at {self.timestamp:%H:%M}"

class Notification(models.Model):
    """Notification for staff about patient flow events (in-app, email, SMS)."""
    recipient: User = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    event: PatientFlowEvent = models.ForeignKey(PatientFlowEvent, on_delete=models.CASCADE, related_name='notifications')
    message: str = models.TextField()
    is_read: bool = models.BooleanField(default=False)
    sent_at: timezone.datetime = models.DateTimeField(auto_now_add=True)
    read_at: Optional[timezone.datetime] = models.DateTimeField(null=True, blank=True)
    via_email: bool = models.BooleanField(default=False)
    via_sms: bool = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"To {self.recipient}: {self.message[:40]}..."

class UserProfile(models.Model):
    """Extends user with role and clinic association (if not already present)."""
    user: User = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    clinic: Optional[Clinic] = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    ROLE_CHOICES = [
        ('front_desk', 'Front Desk'),
        ('nurse', 'Nurse'),
        ('provider', 'Provider'),
        ('admin', 'Admin'),
        ('other', 'Other'),
    ]
    role: str = models.CharField(max_length=20, choices=ROLE_CHOICES, default='other')
    # Add more fields as needed (e.g., notification preferences)

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"
