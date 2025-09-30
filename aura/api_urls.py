"""
Main API URL configuration for the Aura platform
Following the PRD structure with /api/0/ prefix
"""

from django.urls import include
from django.urls import path

from aura.core.api.appointments import AppointmentCancelView
from aura.core.api.appointments import AppointmentCreateView
from aura.core.api.appointments import AppointmentDetailView
from aura.core.api.appointments import AppointmentListView
from aura.core.api.appointments import AppointmentRescheduleView
from aura.users.api.matching import MatchFeedbackView
from aura.users.api.matching import PatientMatchesView

# Import views for class-based view URLs
from aura.users.api.patient_profiles import PatientProfileCreateView
from aura.users.api.patient_profiles import PatientProfileDetailView
from aura.users.api.therapist_profiles import TherapistProfileCreateView
from aura.users.api.therapist_profiles import TherapistProfileDetailView

# Authentication URLs
auth_patterns = [
    path("auth/", include("aura.users.api.urls")),
]

# Patient URLs
patient_patterns = [
    path("patients/profile/", PatientProfileCreateView.as_view(), name="create_patient_profile"),
    path("patients/profile/", PatientProfileDetailView.as_view(), name="patient_profile_detail"),
    path("patients/matches/", PatientMatchesView.as_view(), name="get_patient_matches"),
    path("patients/matches/feedback/", MatchFeedbackView.as_view(), name="submit_match_feedback"),
]

# Therapist URLs
therapist_patterns = [
    path("therapists/profile/", TherapistProfileCreateView.as_view(), name="create_therapist_profile"),
    path("therapists/profile/", TherapistProfileDetailView.as_view(), name="therapist_profile_detail"),
]

# Appointment URLs
appointment_patterns = [
    path("appointments/", AppointmentCreateView.as_view(), name="create_appointment"),
    path("appointments/", AppointmentListView.as_view(), name="list_appointments"),
    path("appointments/<uuid:appointment_id>/", AppointmentDetailView.as_view(), name="appointment_detail"),
    path(
        "appointments/<uuid:appointment_id>/reschedule/",
        AppointmentRescheduleView.as_view(),
        name="reschedule_appointment",
    ),
    path(
        "appointments/<uuid:appointment_id>/cancel/",
        AppointmentCancelView.as_view(),
        name="cancel_appointment",
    ),
]

# Main API v0 patterns
api_v0_patterns = [
    *auth_patterns,
    *patient_patterns,
    *therapist_patterns,
    *appointment_patterns,
]

# Export for use in main URLs
urlpatterns = [
    path("api/0/", include(api_v0_patterns)),
]
