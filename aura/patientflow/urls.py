from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ClinicViewSet, StatusViewSet, PatientViewSet, AppointmentViewSet,
    PatientFlowEventViewSet, NotificationViewSet, FlowBoardViewSet,
    AnalyticsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'clinics', ClinicViewSet)
router.register(r'statuses', StatusViewSet)
router.register(r'patients', PatientViewSet)
router.register(r'appointments', AppointmentViewSet)
router.register(r'flow-events', PatientFlowEventViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'flow-board', FlowBoardViewSet, basename='flowboard')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

app_name = 'patientflow'

urlpatterns = [
    # API v1 endpoints
    path('api/v1/', include(router.urls)),

    # Custom API endpoints (if needed)
    # path('api/v1/custom-endpoint/', custom_view, name='custom-endpoint'),
]

# For easy reference, the generated URLs will be:
"""
Generated API Endpoints:

Clinics:
- GET    /api/v1/clinics/                    - List clinics
- POST   /api/v1/clinics/                    - Create clinic
- GET    /api/v1/clinics/{id}/               - Retrieve clinic
- PUT    /api/v1/clinics/{id}/               - Update clinic
- PATCH  /api/v1/clinics/{id}/               - Partial update clinic
- DELETE /api/v1/clinics/{id}/               - Delete clinic
- GET    /api/v1/clinics/{id}/staff/         - List clinic staff
- GET    /api/v1/clinics/{id}/analytics/     - Clinic analytics

Statuses:
- GET    /api/v1/statuses/                   - List statuses
- POST   /api/v1/statuses/                   - Create status
- GET    /api/v1/statuses/{id}/              - Retrieve status
- PUT    /api/v1/statuses/{id}/              - Update status
- PATCH  /api/v1/statuses/{id}/              - Partial update status
- DELETE /api/v1/statuses/{id}/              - Delete status
- POST   /api/v1/statuses/reorder/           - Reorder statuses
- GET    /api/v1/statuses/{id}/appointments/ - List appointments in status

Patients:
- GET    /api/v1/patients/                   - List patients
- POST   /api/v1/patients/                   - Create patient
- GET    /api/v1/patients/{id}/              - Retrieve patient
- PUT    /api/v1/patients/{id}/              - Update patient
- PATCH  /api/v1/patients/{id}/              - Partial update patient
- DELETE /api/v1/patients/{id}/              - Delete patient
- GET    /api/v1/patients/{id}/appointments/ - List patient appointments

Appointments:
- GET    /api/v1/appointments/               - List appointments
- POST   /api/v1/appointments/               - Create appointment
- GET    /api/v1/appointments/{id}/          - Retrieve appointment
- PUT    /api/v1/appointments/{id}/          - Update appointment
- PATCH  /api/v1/appointments/{id}/          - Partial update appointment
- DELETE /api/v1/appointments/{id}/          - Delete appointment
- POST   /api/v1/appointments/{id}/update_status/ - Update appointment status
- GET    /api/v1/appointments/today/         - Today's appointments
- GET    /api/v1/appointments/active/        - Active appointments
- POST   /api/v1/appointments/bulk_update_status/ - Bulk status update
- GET    /api/v1/appointments/{id}/timeline/ - Appointment timeline

Flow Events:
- GET    /api/v1/flow-events/                - List flow events
- GET    /api/v1/flow-events/{id}/           - Retrieve flow event

Notifications:
- GET    /api/v1/notifications/              - List notifications
- POST   /api/v1/notifications/              - Create notification
- GET    /api/v1/notifications/{id}/         - Retrieve notification
- PUT    /api/v1/notifications/{id}/         - Update notification
- PATCH  /api/v1/notifications/{id}/         - Partial update notification
- DELETE /api/v1/notifications/{id}/         - Delete notification
- POST   /api/v1/notifications/{id}/mark_read/ - Mark notification as read
- POST   /api/v1/notifications/mark_all_read/ - Mark all notifications as read
- GET    /api/v1/notifications/unread_count/ - Get unread notification count

Flow Board:
- GET    /api/v1/flow-board/current/         - Current flow board view
- GET    /api/v1/flow-board/summary/         - Flow board summary

Analytics:
- GET    /api/v1/analytics/daily_report/     - Daily analytics report
- GET    /api/v1/analytics/weekly_trends/    - Weekly trend analysis

Query Parameters for Filtering (examples):

Appointments:
?clinic=1&status=2&today=true&provider_name=john&patient_name=smith&active=true

Flow Events:
?date=2024-01-15&status_name=waiting&patient_name=john&today=true

Notifications:
?is_read=false&via_email=true&today=true&recent=true

Patients:
?clinic=1&name=john&has_appointments=true&appointments_today=true

Statuses:
?clinic=1&is_active=true&has_appointments=true

General Query Parameters:
- ordering: ?ordering=created_at,-scheduled_time
- search: ?search=john
- page: ?page=2
- page_size: ?page_size=20
"""
