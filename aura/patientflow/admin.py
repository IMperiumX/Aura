from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Clinic, Status, Patient, Appointment,
    PatientFlowEvent, Notification, UserProfile
)


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'patient_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'address')
    readonly_fields = ('created_at', 'updated_at')

    def patient_count(self, obj):
        return obj.patients.count()
    patient_count.short_description = 'Patients'


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'clinic', 'color_preview', 'order', 'is_active')
    list_filter = ('clinic', 'is_active')
    search_fields = ('name', 'clinic__name')
    list_editable = ('order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('clinic', 'order')

    def color_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'clinic', 'dob', 'appointment_count', 'created_at')
    list_filter = ('clinic', 'created_at')
    search_fields = ('first_name', 'last_name', 'clinic__name')
    readonly_fields = ('created_at', 'updated_at')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'

    def appointment_count(self, obj):
        return obj.appointments.count()
    appointment_count.short_description = 'Appointments'


class PatientFlowEventInline(admin.TabularInline):
    model = PatientFlowEvent
    extra = 0
    readonly_fields = ('timestamp', 'updated_by')
    fields = ('status', 'timestamp', 'updated_by', 'notes')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'clinic', 'scheduled_time', 'provider', 'current_status', 'duration_in_system')
    list_filter = ('clinic', 'scheduled_time', 'status', 'provider')
    search_fields = ('patient__first_name', 'patient__last_name', 'clinic__name', 'provider__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PatientFlowEventInline]
    date_hierarchy = 'scheduled_time'

    def current_status(self, obj):
        if obj.status:
            return format_html(
                '<span style="background-color: {}; padding: 2px 6px; border-radius: 3px; color: white;">{}</span>',
                obj.status.color,
                obj.status.name
            )
        return 'No Status'
    current_status.short_description = 'Status'

    def duration_in_system(self, obj):
        if obj.flow_events.exists():
            first_event = obj.flow_events.first()
            duration = timezone.now() - first_event.timestamp
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m"
        return "Not started"
    duration_in_system.short_description = 'Time in System'


@admin.register(PatientFlowEvent)
class PatientFlowEventAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'status', 'timestamp', 'updated_by', 'duration_in_status')
    list_filter = ('status', 'timestamp', 'updated_by')
    search_fields = ('appointment__patient__first_name', 'appointment__patient__last_name', 'status__name')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

    def duration_in_status(self, obj):
        # Calculate time spent in this status
        next_event = PatientFlowEvent.objects.filter(
            appointment=obj.appointment,
            timestamp__gt=obj.timestamp
        ).first()

        if next_event:
            duration = next_event.timestamp - obj.timestamp
        else:
            duration = timezone.now() - obj.timestamp

        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m"
    duration_in_status.short_description = 'Duration'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message_preview', 'is_read', 'delivery_methods', 'sent_at')
    list_filter = ('is_read', 'via_email', 'via_sms', 'sent_at')
    search_fields = ('recipient__username', 'message')
    readonly_fields = ('sent_at',)
    actions = ['mark_as_read', 'mark_as_unread']

    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'

    def delivery_methods(self, obj):
        methods = []
        if obj.via_email:
            methods.append('Email')
        if obj.via_sms:
            methods.append('SMS')
        if not methods:
            methods.append('In-app')
        return ', '.join(methods)
    delivery_methods.short_description = 'Delivery'

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
    mark_as_unread.short_description = "Mark selected notifications as unread"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'clinic', 'notification_count')
    list_filter = ('role', 'clinic')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'clinic__name')

    def notification_count(self, obj):
        return obj.user.notifications.filter(is_read=False).count()
    notification_count.short_description = 'Unread Notifications'
