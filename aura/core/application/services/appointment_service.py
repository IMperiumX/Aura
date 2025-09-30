"""
Service layer for appointment operations.
Orchestrates appointment use cases and provides a clean interface for views.
"""

from datetime import datetime

from aura.core.application.use_cases.appointments import CancelAppointmentRequest
from aura.core.application.use_cases.appointments import CancelAppointmentUseCase
from aura.core.application.use_cases.appointments import CreateAppointmentRequest
from aura.core.application.use_cases.appointments import CreateAppointmentUseCase
from aura.core.application.use_cases.appointments import GetAppointmentDetailRequest
from aura.core.application.use_cases.appointments import GetAppointmentDetailUseCase
from aura.core.application.use_cases.appointments import GetAppointmentsRequest
from aura.core.application.use_cases.appointments import GetAppointmentsUseCase
from aura.core.application.use_cases.appointments import RescheduleAppointmentRequest
from aura.core.application.use_cases.appointments import RescheduleAppointmentUseCase
from aura.core.domain.repositories.appointment_repository import AppointmentRepository


class AppointmentService:
    """Service for appointment operations."""

    def __init__(self, appointment_repository: AppointmentRepository):
        self._repository = appointment_repository
        self._create_use_case = CreateAppointmentUseCase(appointment_repository)
        self._get_appointments_use_case = GetAppointmentsUseCase(appointment_repository)
        self._get_detail_use_case = GetAppointmentDetailUseCase(appointment_repository)
        self._reschedule_use_case = RescheduleAppointmentUseCase(appointment_repository)
        self._cancel_use_case = CancelAppointmentUseCase(appointment_repository)

    def create_appointment(
        self,
        patient,
        therapist_id: str,
        session_datetime: datetime,
        session_duration: int = 60,
        session_type: str = "video",
        notes: str = "",
        payment_method_id: str = "",
    ):
        """Create a new appointment."""
        request = CreateAppointmentRequest(
            patient=patient,
            therapist_id=therapist_id,
            session_datetime=session_datetime,
            session_duration=session_duration,
            session_type=session_type,
            notes=notes,
            payment_method_id=payment_method_id,
        )
        return self._create_use_case.execute(request)

    def get_user_appointments(self, user, status_filter: str = None):
        """Get appointments for a user."""
        request = GetAppointmentsRequest(user=user, status_filter=status_filter)
        return self._get_appointments_use_case.execute(request)

    def get_appointment_detail(self, appointment_id: str, user):
        """Get appointment details."""
        request = GetAppointmentDetailRequest(appointment_id=appointment_id, user=user)
        return self._get_detail_use_case.execute(request)

    def reschedule_appointment(self, appointment_id: str, user, new_session_datetime: datetime, reason: str):
        """Reschedule an appointment."""
        request = RescheduleAppointmentRequest(
            appointment_id=appointment_id, user=user, new_session_datetime=new_session_datetime, reason=reason
        )
        return self._reschedule_use_case.execute(request)

    def cancel_appointment(self, appointment_id: str, user, reason: str, refund_requested: bool = True):
        """Cancel an appointment."""
        request = CancelAppointmentRequest(
            appointment_id=appointment_id, user=user, reason=reason, refund_requested=refund_requested
        )
        return self._cancel_use_case.execute(request)

    def serialize_appointment(self, appointment):
        """Serialize appointment for API response."""
        return {
            "id": str(appointment.id),
            "patient": {
                "id": str(appointment.patient.id),
                "name": f"{appointment.patient.first_name} {appointment.patient.last_name}",
            },
            "therapist": {
                "id": str(appointment.therapist.id),
                "name": f"Dr. {appointment.therapist.first_name} {appointment.therapist.last_name}",
                "credentials": getattr(appointment.therapist, "therapist_profile", {}).get("credentials", []),
            },
            "session_datetime": appointment.session_datetime.isoformat(),
            "session_duration": appointment.session_duration,
            "session_type": appointment.session_type,
            "status": appointment.status,
            "notes": appointment.notes,
            "payment_status": appointment.payment_status,
            "amount": float(appointment.amount) if appointment.amount else None,
            "session_link": appointment.session_link,
            "confirmation_sent": appointment.confirmation_sent,
            "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
        }
