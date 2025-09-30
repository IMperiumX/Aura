from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from aura.core.appointments import Appointment
from aura.core.services import AppointmentBookingService
from aura.core.services import AppointmentManagementService
from aura.users.models import User


class AppointmentCreateSerializer(serializers.Serializer):
    """Serializer for creating appointments"""

    therapist_id = serializers.UUIDField()
    session_datetime = serializers.DateTimeField()
    session_duration = serializers.IntegerField(default=60)
    session_type = serializers.ChoiceField(
        choices=[("video", "Video"), ("audio", "Audio"), ("in_person", "In-Person")], default="video"
    )
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    payment_method_id = serializers.CharField(max_length=100)

    def validate_session_duration(self, value):
        if value not in [30, 45, 60, 90]:
            msg = "Session duration must be 30, 45, 60, or 90 minutes"
            raise serializers.ValidationError(msg)
        return value

    def validate_therapist_id(self, value):
        try:
            therapist = User.objects.get(id=value, user_type="therapist")
            if not hasattr(therapist, "therapist_profile"):
                msg = "Therapist profile not found"
                raise serializers.ValidationError(msg)
            if not therapist.therapist_profile.is_verified:
                msg = "Therapist is not verified"
                raise serializers.ValidationError(msg)
        except User.DoesNotExist:
            msg = "Therapist not found"
            raise serializers.ValidationError(msg) from None
        else:
            return value


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for appointment details"""

    therapist = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    calendar_links = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "therapist",
            "session_datetime",
            "session_duration",
            "session_type",
            "status",
            "notes",
            "payment_status",
            "amount",
            "session_link",
            "confirmation_sent",
            "created_at",
            "calendar_links",
        ]

    def get_therapist(self, obj):
        return {
            "id": str(obj.therapist.id),
            "name": f"Dr. {obj.therapist.first_name} {obj.therapist.last_name}",
            "credentials": obj.therapist.therapist_profile.credentials
            if hasattr(obj.therapist, "therapist_profile")
            else [],
        }

    def get_patient(self, obj):
        return {"id": str(obj.patient.id), "name": f"{obj.patient.first_name} {obj.patient.last_name}"}

    def get_calendar_links(self, obj):
        return AppointmentBookingService.get_calendar_links(obj)


class RescheduleSerializer(serializers.Serializer):
    """Serializer for rescheduling appointments"""

    new_session_datetime = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500)


class CancellationSerializer(serializers.Serializer):
    """Serializer for cancelling appointments"""

    reason = serializers.CharField(max_length=500)
    refund_requested = serializers.BooleanField(default=True)


class AppointmentCreateView(APIView):
    """
    Create a new appointment
    POST /api/0/appointments/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only patients can book appointments
        if request.user.user_type != "patient":
            return Response(
                {
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Only patients can book appointments",
                        "details": {},
                    },
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AppointmentCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                therapist = User.objects.get(id=serializer.validated_data["therapist_id"])

                booking_service = AppointmentBookingService(
                    patient=request.user,
                    therapist=therapist,
                    session_datetime=serializer.validated_data["session_datetime"],
                )

                appointment = booking_service.book_appointment(
                    session_duration=serializer.validated_data["session_duration"],
                    session_type=serializer.validated_data["session_type"],
                    notes=serializer.validated_data.get("notes", ""),
                    payment_method_id=serializer.validated_data["payment_method_id"],
                )

                response_data = {
                    "appointment_id": str(appointment.id),
                    "status": appointment.status,
                    "session_datetime": appointment.session_datetime.isoformat(),
                    "session_duration": appointment.session_duration,
                    "session_type": appointment.session_type,
                    "therapist": {
                        "id": str(appointment.therapist.id),
                        "name": f"Dr. {appointment.therapist.first_name} {appointment.therapist.last_name}",
                        "credentials": appointment.therapist.therapist_profile.credentials,
                    },
                    "payment_status": appointment.payment_status,
                    "confirmation_sent": appointment.confirmation_sent,
                    "calendar_links": AppointmentBookingService.get_calendar_links(appointment),
                }

                return Response(
                    {
                        "data": response_data,
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )

            except ValidationError as e:
                return Response(
                    {
                        "error": {"code": "BOOKING_ERROR", "message": str(e), "details": {}},
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            except User.DoesNotExist:
                return Response(
                    {
                        "error": {"code": "THERAPIST_NOT_FOUND", "message": "Therapist not found", "details": {}},
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid appointment data",
                    "details": {"field_errors": serializer.errors},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AppointmentListView(APIView):
    """
    List user's appointments
    GET /api/0/appointments/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get appointments for the user
        if request.user.user_type == "patient":
            appointments = Appointment.objects.filter(patient=request.user)
        elif request.user.user_type == "therapist":
            appointments = Appointment.objects.filter(therapist=request.user)
        else:
            return Response(
                {
                    "error": {"code": "PERMISSION_DENIED", "message": "Access denied", "details": {}},
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Filter by status if provided
        status_filter = request.GET.get("status")
        if status_filter:
            appointments = appointments.filter(status=status_filter)

        # Order by session date
        appointments = appointments.order_by("-session_datetime").select_related("patient", "therapist")

        serializer = AppointmentSerializer(appointments, many=True)

        return Response(
            {
                "data": serializer.data,
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            }
        )


class AppointmentDetailView(APIView):
    """
    Get appointment details
    GET /api/0/appointments/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id)

        # Check permissions
        if request.user not in [appointment.patient, appointment.therapist]:
            return Response(
                {
                    "error": {"code": "PERMISSION_DENIED", "message": "Access denied", "details": {}},
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AppointmentSerializer(appointment)

        return Response(
            {
                "data": serializer.data,
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            }
        )


class AppointmentRescheduleView(APIView):
    """
    Reschedule an appointment
    PATCH /api/0/appointments/{id}/reschedule/
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id)

        # Check permissions (both patient and therapist can reschedule)
        if request.user not in [appointment.patient, appointment.therapist]:
            return Response(
                {
                    "error": {"code": "PERMISSION_DENIED", "message": "Access denied", "details": {}},
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RescheduleSerializer(data=request.data)
        if serializer.is_valid():
            try:
                updated_appointment = AppointmentManagementService.reschedule_appointment(
                    appointment=appointment,
                    new_datetime=serializer.validated_data["new_session_datetime"],
                    reason=serializer.validated_data["reason"],
                    requested_by=request.user,
                )

                return Response(
                    {
                        "data": {
                            "appointment_id": str(updated_appointment.id),
                            "status": updated_appointment.status,
                            "old_datetime": appointment.session_datetime.isoformat(),
                            "new_datetime": updated_appointment.session_datetime.isoformat(),
                            "message": "Appointment successfully rescheduled",
                        },
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    }
                )

            except ValidationError as e:
                return Response(
                    {
                        "error": {"code": "RESCHEDULE_ERROR", "message": str(e), "details": {}},
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid reschedule data",
                    "details": {"field_errors": serializer.errors},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AppointmentCancelView(APIView):
    """
    Cancel an appointment
    PATCH /api/0/appointments/{id}/cancel/
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id)

        # Check permissions (both patient and therapist can cancel)
        if request.user not in [appointment.patient, appointment.therapist]:
            return Response(
                {
                    "error": {"code": "PERMISSION_DENIED", "message": "Access denied", "details": {}},
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CancellationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = AppointmentManagementService.cancel_appointment(
                    appointment=appointment,
                    reason=serializer.validated_data["reason"],
                    cancelled_by=request.user,
                    refund_requested=serializer.validated_data.get("refund_requested", True),
                )

                return Response(
                    {
                        "data": {
                            "appointment_id": str(appointment.id),
                            "status": result["status"],
                            "refund_processed": result["refund_processed"],
                            "refund_amount": result["refund_amount"],
                            "message": "Appointment successfully cancelled",
                        },
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    }
                )

            except ValidationError as e:
                return Response(
                    {
                        "error": {"code": "CANCELLATION_ERROR", "message": str(e), "details": {}},
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid cancellation data",
                    "details": {"field_errors": serializer.errors},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
