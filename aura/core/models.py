from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class AuditLog(models.Model):
    """
    Model to track all user actions for compliance and security.
    """

    ACTION_CHOICES = [
        ("create", "Create"),
        ("read", "Read"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("failed_login", "Failed Login"),
        ("profile_update", "Profile Update"),
        ("appointment_book", "Appointment Book"),
        ("appointment_cancel", "Appointment Cancel"),
        ("match_view", "Match View"),
        ("message_send", "Message Send"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    resource_type = models.CharField(max_length=100, help_text="Model name or resource type affected")
    resource_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID of the affected resource")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True, help_text="Additional details about the action")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource_type} - {self.timestamp}"


class SystemMetrics(models.Model):
    """
    Model to store system performance metrics.
    """

    metric_name = models.CharField(max_length=100, db_index=True)
    metric_value = models.FloatField()
    metric_unit = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["metric_name", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.metric_name}: {self.metric_value} {self.metric_unit}"
