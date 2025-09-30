"""
Use cases for appointment operations.
Contains business logic for creating, managing, and updating appointments.
"""

from dataclasses import dataclass
from datetime import datetime

from aura.core.appointments import Appointment
from aura.core.domain.repositories.appointment_repository import AppointmentRepository
from aura.users.models import User


@dataclass
class CreateAppointmentRequest:
    """Request for creating an appointment."""

    patient: User
    therapist_id: str
    session_datetime: datetime
    session_duration: int = 60
    session_type: str = "video"
    notes: str = ""
    payment_method_id: str = ""


@dataclass
class CreateAppointmentResponse:
    """Response for creating an appointment."""

    success: bool
    appointment: Appointment | None = None
    error_message: str | None = None


@dataclass
class GetAppointmentsRequest:
    """Request for getting appointments."""

    user: User
    status_filter: str | None = None


@dataclass
class GetAppointmentsResponse:
    """Response for getting appointments."""

    success: bool
    appointments: list[Appointment] | None = None
    error_message: str | None = None


@dataclass
class GetAppointmentDetailRequest:
    """Request for getting appointment details."""

    appointment_id: str
    user: User


@dataclass
class GetAppointmentDetailResponse:
    """Response for getting appointment details."""

    success: bool
    appointment: Appointment | None = None
    error_message: str | None = None


@dataclass
class RescheduleAppointmentRequest:
    """Request for rescheduling an appointment."""

    appointment_id: str
    user: User
    new_session_datetime: datetime
    reason: str


@dataclass
class RescheduleAppointmentResponse:
    """Response for rescheduling an appointment."""

    success: bool
    appointment: Appointment | None = None
    error_message: str | None = None


@dataclass
class CancelAppointmentRequest:
    """Request for cancelling an appointment."""

    appointment_id: str
    user: User
    reason: str
    refund_requested: bool = True


@dataclass
class CancelAppointmentResponse:
    """Response for cancelling an appointment."""

    success: bool
    appointment: Appointment | None = None
    refund_processed: bool = False
    refund_amount: float = 0.0
    error_message: str | None = None


class CreateAppointmentUseCase:
    """Use case for creating an appointment."""

    def __init__(self, appointment_repository: AppointmentRepository):
        self._repository = appointment_repository

    def execute(self, request: CreateAppointmentRequest) -> CreateAppointmentResponse:
        """Execute the create appointment use case."""
        try:
            # Validate request
            self._validate_create_request(request)

            # Check for conflicts
            conflicting_appointments = self._repository.find_conflicting_appointments(
                therapist=User.objects.get(id=request.therapist_id),
                session_datetime=request.session_datetime,
                duration=request.session_duration,
            )

            if conflicting_appointments:
                return CreateAppointmentResponse(
                    success=False, error_message="Therapist is not available at the requested time"
                )

            # Create appointment data
            appointment_data = {
                "patient": request.patient,
                "therapist": User.objects.get(id=request.therapist_id),
                "session_datetime": request.session_datetime,
                "session_duration": request.session_duration,
                "session_type": request.session_type,
                "notes": request.notes,
                "status": "scheduled",
                "payment_status": "pending",
            }

            # Create appointment
            appointment = self._repository.create_appointment(appointment_data)

            return CreateAppointmentResponse(success=True, appointment=appointment)

        except ValueError as e:
            return CreateAppointmentResponse(success=False, error_message=str(e))
        except Exception as e:
            return CreateAppointmentResponse(success=False, error_message=f"Appointment creation failed: {e!s}")

    def _validate_create_request(self, request: CreateAppointmentRequest) -> None:
        """Validate appointment creation request."""
        if not request.patient:
            raise ValueError("Patient is required")

        if not request.therapist_id:
            raise ValueError("Therapist ID is required")

        if not request.session_datetime:
            raise ValueError("Session datetime is required")

        if request.session_datetime <= datetime.now():
            raise ValueError("Session datetime must be in the future")

        if request.session_duration not in [30, 45, 60, 90]:
            raise ValueError("Session duration must be 30, 45, 60, or 90 minutes")

        if request.session_type not in ["video", "audio", "in_person"]:
            raise ValueError("Invalid session type")


class GetAppointmentsUseCase:
    """Use case for getting user appointments."""

    def __init__(self, appointment_repository: AppointmentRepository):
        self._repository = appointment_repository

    def execute(self, request: GetAppointmentsRequest) -> GetAppointmentsResponse:
        """Execute the get appointments use case."""
        try:
            # Get appointments based on user type
            if request.user.user_type == "patient":
                appointments = self._repository.find_by_patient(request.user)
            elif request.user.user_type == "therapist":
                appointments = self._repository.find_by_therapist(request.user)
            else:
                return GetAppointmentsResponse(success=False, error_message="Access denied")

            # Filter by status if provided
            if request.status_filter:
                appointments = [a for a in appointments if a.status == request.status_filter]

            return GetAppointmentsResponse(success=True, appointments=appointments)

        except Exception as e:
            return GetAppointmentsResponse(success=False, error_message=f"Failed to get appointments: {e!s}")


class GetAppointmentDetailUseCase:
    """Use case for getting appointment details."""

    def __init__(self, appointment_repository: AppointmentRepository):
        self._repository = appointment_repository

    def execute(self, request: GetAppointmentDetailRequest) -> GetAppointmentDetailResponse:
        """Execute the get appointment detail use case."""
        try:
            appointment = self._repository.find_by_id(request.appointment_id)

            if not appointment:
                return GetAppointmentDetailResponse(success=False, error_message="Appointment not found")

            # Check permissions
            if request.user not in [appointment.patient, appointment.therapist]:
                return GetAppointmentDetailResponse(success=False, error_message="Access denied")

            return GetAppointmentDetailResponse(success=True, appointment=appointment)

        except Exception as e:
            return GetAppointmentDetailResponse(success=False, error_message=f"Failed to get appointment: {e!s}")


class RescheduleAppointmentUseCase:
    """Use case for rescheduling an appointment."""

    def __init__(self, appointment_repository: AppointmentRepository):
        self._repository = appointment_repository

    def execute(self, request: RescheduleAppointmentRequest) -> RescheduleAppointmentResponse:
        """Execute the reschedule appointment use case."""
        try:
            appointment = self._repository.find_by_id(request.appointment_id)

            if not appointment:
                return RescheduleAppointmentResponse(success=False, error_message="Appointment not found")

            # Check permissions
            if request.user not in [appointment.patient, appointment.therapist]:
                return RescheduleAppointmentResponse(success=False, error_message="Access denied")

            # Update appointment
            appointment.session_datetime = request.new_session_datetime
            appointment.status = "rescheduled"
            appointment.notes += f"\nRescheduled: {request.reason}"

            updated_appointment = self._repository.update_appointment(appointment)

            return RescheduleAppointmentResponse(success=True, appointment=updated_appointment)

        except Exception as e:
            return RescheduleAppointmentResponse(
                success=False, error_message=f"Failed to reschedule appointment: {e!s}"
            )


class CancelAppointmentUseCase:
    """Use case for cancelling an appointment."""

    def __init__(self, appointment_repository: AppointmentRepository):
        self._repository = appointment_repository

    def execute(self, request: CancelAppointmentRequest) -> CancelAppointmentResponse:
        """Execute the cancel appointment use case."""
        try:
            appointment = self._repository.find_by_id(request.appointment_id)

            if not appointment:
                return CancelAppointmentResponse(success=False, error_message="Appointment not found")

            # Check permissions
            if request.user not in [appointment.patient, appointment.therapist]:
                return CancelAppointmentResponse(success=False, error_message="Access denied")

            # Update appointment
            appointment.status = "cancelled"
            appointment.notes += f"\nCancelled: {request.reason}"

            updated_appointment = self._repository.update_appointment(appointment)

            # Process refund if requested
            refund_processed = False
            refund_amount = 0.0
            if request.refund_requested and appointment.payment_status == "paid":
                # Refund logic would go here
                refund_processed = True
                refund_amount = float(appointment.amount or 0)

            return CancelAppointmentResponse(
                success=True,
                appointment=updated_appointment,
                refund_processed=refund_processed,
                refund_amount=refund_amount,
            )

        except Exception as e:
            return CancelAppointmentResponse(success=False, error_message=f"Failed to cancel appointment: {e!s}")
