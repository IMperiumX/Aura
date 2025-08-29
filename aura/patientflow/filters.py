from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Appointment
from .models import Clinic
from .models import Notification
from .models import Patient
from .models import PatientFlowEvent
from .models import Status


class AppointmentFilter(django_filters.FilterSet):
    """Filter for Appointment model with advanced date and status filtering."""

    # Date filters
    scheduled_date = django_filters.DateFilter(field_name="scheduled_time__date")
    scheduled_date_gte = django_filters.DateFilter(
        field_name="scheduled_time__date",
        lookup_expr="gte",
    )
    scheduled_date_lte = django_filters.DateFilter(
        field_name="scheduled_time__date",
        lookup_expr="lte",
    )
    scheduled_time_gte = django_filters.DateTimeFilter(
        field_name="scheduled_time",
        lookup_expr="gte",
    )
    scheduled_time_lte = django_filters.DateTimeFilter(
        field_name="scheduled_time",
        lookup_expr="lte",
    )

    # Status filters
    status = django_filters.ModelChoiceFilter(queryset=Status.objects.all())
    status_name = django_filters.CharFilter(
        field_name="status__name",
        lookup_expr="icontains",
    )
    has_status = django_filters.BooleanFilter(
        field_name="status",
        lookup_expr="isnull",
        exclude=True,
    )

    # Provider filters
    provider = django_filters.ModelChoiceFilter(
        queryset=None,
    )  # Will be set in __init__
    provider_name = django_filters.CharFilter(method="filter_provider_name")
    has_provider = django_filters.BooleanFilter(
        field_name="provider",
        lookup_expr="isnull",
        exclude=True,
    )

    # Patient filters
    patient_name = django_filters.CharFilter(method="filter_patient_name")

    # Time-based filters
    today = django_filters.BooleanFilter(method="filter_today")
    this_week = django_filters.BooleanFilter(method="filter_this_week")
    active = django_filters.BooleanFilter(method="filter_active")

    # Time in system filters
    time_in_system_gte = django_filters.NumberFilter(method="filter_time_in_system_gte")
    time_in_system_lte = django_filters.NumberFilter(method="filter_time_in_system_lte")

    class Meta:
        model = Appointment
        fields = [
            "clinic",
            "patient",
            "provider",
            "status",
            "external_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set provider queryset based on request user's clinic
        request = kwargs.get("request")
        if request and hasattr(request.user, "profile") and request.user.profile.clinic:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            self.filters["provider"].queryset = User.objects.filter(
                profile__clinic=request.user.profile.clinic,
            )

    def filter_provider_name(self, queryset, name, value):
        """Filter by provider's full name or username."""
        return queryset.filter(
            Q(provider__first_name__icontains=value)
            | Q(provider__last_name__icontains=value)
            | Q(provider__username__icontains=value),
        )

    def filter_patient_name(self, queryset, name, value):
        """Filter by patient's full name."""
        return queryset.filter(
            Q(patient__first_name__icontains=value)
            | Q(patient__last_name__icontains=value),
        )

    def filter_today(self, queryset, name, value):
        """Filter appointments for today."""
        if value:
            today = timezone.now().date()
            return queryset.filter(scheduled_time__date=today)
        return queryset

    def filter_this_week(self, queryset, name, value):
        """Filter appointments for this week."""
        if value:
            today = timezone.now().date()
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return queryset.filter(
                scheduled_time__date__gte=start_week,
                scheduled_time__date__lte=end_week,
            )
        return queryset

    def filter_active(self, queryset, name, value):
        """Filter appointments that have flow events (are active in the system)."""
        if value:
            return queryset.filter(flow_events__isnull=False).distinct()
        else:
            return queryset.filter(flow_events__isnull=True)

    def filter_time_in_system_gte(self, queryset, name, value):
        """Filter appointments that have been in system for at least X minutes."""
        if value:
            cutoff_time = timezone.now() - timedelta(minutes=value)
            return queryset.filter(flow_events__timestamp__lte=cutoff_time).distinct()
        return queryset

    def filter_time_in_system_lte(self, queryset, name, value):
        """Filter appointments that have been in system for at most X minutes."""
        if value:
            cutoff_time = timezone.now() - timedelta(minutes=value)
            return queryset.filter(flow_events__timestamp__gte=cutoff_time).distinct()
        return queryset


class PatientFlowEventFilter(django_filters.FilterSet):
    """Filter for PatientFlowEvent model."""

    # Date filters
    date = django_filters.DateFilter(field_name="timestamp__date")
    date_gte = django_filters.DateFilter(
        field_name="timestamp__date",
        lookup_expr="gte",
    )
    date_lte = django_filters.DateFilter(
        field_name="timestamp__date",
        lookup_expr="lte",
    )
    timestamp_gte = django_filters.DateTimeFilter(
        field_name="timestamp",
        lookup_expr="gte",
    )
    timestamp_lte = django_filters.DateTimeFilter(
        field_name="timestamp",
        lookup_expr="lte",
    )

    # Status filters
    status = django_filters.ModelChoiceFilter(queryset=Status.objects.all())
    status_name = django_filters.CharFilter(
        field_name="status__name",
        lookup_expr="icontains",
    )

    # Appointment filters
    appointment = django_filters.ModelChoiceFilter(queryset=Appointment.objects.all())
    patient_name = django_filters.CharFilter(method="filter_patient_name")
    clinic = django_filters.ModelChoiceFilter(
        field_name="appointment__clinic",
        queryset=Clinic.objects.all(),
    )

    # User filters
    updated_by = django_filters.ModelChoiceFilter(queryset=None)  # Set in __init__
    updated_by_name = django_filters.CharFilter(method="filter_updated_by_name")

    # Time-based filters
    today = django_filters.BooleanFilter(method="filter_today")
    this_week = django_filters.BooleanFilter(method="filter_this_week")

    class Meta:
        model = PatientFlowEvent
        fields = ["appointment", "status", "updated_by"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set updated_by queryset based on request user's clinic
        request = kwargs.get("request")
        if request and hasattr(request.user, "profile") and request.user.profile.clinic:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            self.filters["updated_by"].queryset = User.objects.filter(
                profile__clinic=request.user.profile.clinic,
            )

    def filter_patient_name(self, queryset, name, value):
        """Filter by patient's full name."""
        return queryset.filter(
            Q(appointment__patient__first_name__icontains=value)
            | Q(appointment__patient__last_name__icontains=value),
        )

    def filter_updated_by_name(self, queryset, name, value):
        """Filter by updated_by user's name."""
        return queryset.filter(
            Q(updated_by__first_name__icontains=value)
            | Q(updated_by__last_name__icontains=value)
            | Q(updated_by__username__icontains=value),
        )

    def filter_today(self, queryset, name, value):
        """Filter events for today."""
        if value:
            today = timezone.now().date()
            return queryset.filter(timestamp__date=today)
        return queryset

    def filter_this_week(self, queryset, name, value):
        """Filter events for this week."""
        if value:
            today = timezone.now().date()
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return queryset.filter(
                timestamp__date__gte=start_week,
                timestamp__date__lte=end_week,
            )
        return queryset


class NotificationFilter(django_filters.FilterSet):
    """Filter for Notification model."""

    # Read status filters
    is_read = django_filters.BooleanFilter()
    unread = django_filters.BooleanFilter(
        field_name="is_read",
        lookup_expr="exact",
        exclude=True,
    )

    # Date filters
    sent_date = django_filters.DateFilter(field_name="sent_at__date")
    sent_date_gte = django_filters.DateFilter(
        field_name="sent_at__date",
        lookup_expr="gte",
    )
    sent_date_lte = django_filters.DateFilter(
        field_name="sent_at__date",
        lookup_expr="lte",
    )
    sent_at_gte = django_filters.DateTimeFilter(field_name="sent_at", lookup_expr="gte")
    sent_at_lte = django_filters.DateTimeFilter(field_name="sent_at", lookup_expr="lte")

    # Delivery method filters
    via_email = django_filters.BooleanFilter()
    via_sms = django_filters.BooleanFilter()
    in_app_only = django_filters.BooleanFilter(method="filter_in_app_only")

    # Event filters
    event_status = django_filters.CharFilter(
        field_name="event__status__name",
        lookup_expr="icontains",
    )
    event_clinic = django_filters.ModelChoiceFilter(
        field_name="event__appointment__clinic",
        queryset=Clinic.objects.all(),
    )
    patient_name = django_filters.CharFilter(method="filter_patient_name")

    # Time-based filters
    today = django_filters.BooleanFilter(method="filter_today")
    this_week = django_filters.BooleanFilter(method="filter_this_week")
    recent = django_filters.BooleanFilter(method="filter_recent")  # Last 24 hours

    class Meta:
        model = Notification
        fields = ["recipient", "is_read", "via_email", "via_sms"]

    def filter_in_app_only(self, queryset, name, value):
        """Filter notifications that are in-app only (no email/SMS)."""
        if value:
            return queryset.filter(via_email=False, via_sms=False)
        else:
            return queryset.filter(Q(via_email=True) | Q(via_sms=True))

    def filter_patient_name(self, queryset, name, value):
        """Filter by patient's full name from the related event."""
        return queryset.filter(
            Q(event__appointment__patient__first_name__icontains=value)
            | Q(event__appointment__patient__last_name__icontains=value),
        )

    def filter_today(self, queryset, name, value):
        """Filter notifications sent today."""
        if value:
            today = timezone.now().date()
            return queryset.filter(sent_at__date=today)
        return queryset

    def filter_this_week(self, queryset, name, value):
        """Filter notifications sent this week."""
        if value:
            today = timezone.now().date()
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return queryset.filter(
                sent_at__date__gte=start_week,
                sent_at__date__lte=end_week,
            )
        return queryset

    def filter_recent(self, queryset, name, value):
        """Filter notifications from the last 24 hours."""
        if value:
            twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
            return queryset.filter(sent_at__gte=twenty_four_hours_ago)
        return queryset


class PatientFilter(django_filters.FilterSet):
    """Filter for Patient model."""

    # Name filters
    name = django_filters.CharFilter(method="filter_name")
    first_name = django_filters.CharFilter(lookup_expr="icontains")
    last_name = django_filters.CharFilter(lookup_expr="icontains")

    # Date filters
    created_date = django_filters.DateFilter(field_name="created_at__date")
    created_date_gte = django_filters.DateFilter(
        field_name="created_at__date",
        lookup_expr="gte",
    )
    created_date_lte = django_filters.DateFilter(
        field_name="created_at__date",
        lookup_expr="lte",
    )

    # Age filters (if DOB is provided)
    age_gte = django_filters.NumberFilter(method="filter_age_gte")
    age_lte = django_filters.NumberFilter(method="filter_age_lte")

    # Appointment filters
    has_appointments = django_filters.BooleanFilter(method="filter_has_appointments")
    appointments_today = django_filters.BooleanFilter(
        method="filter_appointments_today",
    )

    class Meta:
        model = Patient
        fields = ["clinic", "first_name", "last_name"]

    def filter_name(self, queryset, name, value):
        """Filter by full name (first or last)."""
        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value),
        )

    def filter_age_gte(self, queryset, name, value):
        """Filter patients older than or equal to X years."""
        if value:
            cutoff_date = timezone.now().date() - timedelta(days=value * 365.25)
            return queryset.filter(dob__lte=cutoff_date)
        return queryset

    def filter_age_lte(self, queryset, name, value):
        """Filter patients younger than or equal to X years."""
        if value:
            cutoff_date = timezone.now().date() - timedelta(days=value * 365.25)
            return queryset.filter(dob__gte=cutoff_date)
        return queryset

    def filter_has_appointments(self, queryset, name, value):
        """Filter patients with or without appointments."""
        if value:
            return queryset.filter(appointments__isnull=False).distinct()
        else:
            return queryset.filter(appointments__isnull=True)

    def filter_appointments_today(self, queryset, name, value):
        """Filter patients with appointments today."""
        if value:
            today = timezone.now().date()
            return queryset.filter(
                appointments__scheduled_time__date=today,
            ).distinct()
        return queryset


class StatusFilter(django_filters.FilterSet):
    """Filter for Status model."""

    # Name filters
    name = django_filters.CharFilter(lookup_expr="icontains")

    # Active filters
    is_active = django_filters.BooleanFilter()

    # Order filters
    order_gte = django_filters.NumberFilter(field_name="order", lookup_expr="gte")
    order_lte = django_filters.NumberFilter(field_name="order", lookup_expr="lte")

    # Usage filters
    has_appointments = django_filters.BooleanFilter(method="filter_has_appointments")
    appointment_count_gte = django_filters.NumberFilter(
        method="filter_appointment_count_gte",
    )

    class Meta:
        model = Status
        fields = ["clinic", "name", "is_active"]

    def filter_has_appointments(self, queryset, name, value):
        """Filter statuses with or without appointments."""
        if value:
            return queryset.filter(appointments__isnull=False).distinct()
        else:
            return queryset.filter(appointments__isnull=True)

    def filter_appointment_count_gte(self, queryset, name, value):
        """Filter statuses with at least X appointments."""
        if value:
            return queryset.annotate(
                appointment_count=Count("appointments"),
            ).filter(appointment_count__gte=value)
        return queryset
