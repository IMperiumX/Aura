"""
Mental Health API Views using Clean Architecture.
This is the presentation layer that orchestrates use cases.
"""

from datetime import datetime

from django.http import Http404
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from aura.mentalhealth.application.use_cases.manage_therapy_session import CancelSessionRequest
from aura.mentalhealth.application.use_cases.manage_therapy_session import (
    CancelTherapySessionUseCase,
)
from aura.mentalhealth.application.use_cases.manage_therapy_session import EndSessionRequest
from aura.mentalhealth.application.use_cases.manage_therapy_session import EndTherapySessionUseCase
from aura.mentalhealth.application.use_cases.manage_therapy_session import StartSessionRequest
from aura.mentalhealth.application.use_cases.manage_therapy_session import (
    StartTherapySessionUseCase,
)
from aura.mentalhealth.application.use_cases.schedule_therapy_session import (
    ScheduleTherapySessionRequest,
)
from aura.mentalhealth.application.use_cases.schedule_therapy_session import (
    ScheduleTherapySessionUseCase,
)
from aura.mentalhealth.domain.entities.therapy_session import SessionType
from aura.mentalhealth.domain.entities.therapy_session import TargetAudience
from aura.mentalhealth.domain.services.therapy_session_service import TherapySessionDomainService
from aura.mentalhealth.infrastructure.repositories.django_therapy_session_repository import (
    DjangoTherapySessionRepository,
)
from aura.mentalhealth.models import ChatbotInteraction
from aura.mentalhealth.models import Disorder
from aura.mentalhealth.models import TherapySession

from .serializers import ChatbotInteractionSerializer
from .serializers import DisorderSerializer
from .serializers import TherapySessionSerializer


class TherapySessionViewSet(viewsets.ModelViewSet):
    """
    Clean Architecture ViewSet for Therapy Sessions.
    Uses use cases and domain services for business logic.
    """

    queryset = TherapySession.objects.select_related("therapist", "patient")
    serializer_class = TherapySessionSerializer
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize dependencies using DI container
        from config.dependency_injection import get_container

        container = get_container()

        try:
            self.therapy_session_repository = container.resolve("therapy_session_repository")
            self.therapy_session_service = container.resolve("therapy_session_service")
            self.schedule_use_case = container.resolve("schedule_therapy_session_use_case")
            self.start_use_case = container.resolve("start_therapy_session_use_case")
            self.end_use_case = container.resolve("end_therapy_session_use_case")
            self.cancel_use_case = container.resolve("cancel_therapy_session_use_case")
        except ValueError:
            # Fallback to manual initialization if DI fails
            self.therapy_session_repository = DjangoTherapySessionRepository()
            self.therapy_session_service = TherapySessionDomainService(
                self.therapy_session_repository,
            )
            self.schedule_use_case = ScheduleTherapySessionUseCase(
                self.therapy_session_repository,
                self.therapy_session_service,
            )
            self.start_use_case = StartTherapySessionUseCase(
                self.therapy_session_repository,
            )
            self.end_use_case = EndTherapySessionUseCase(
                self.therapy_session_repository,
            )
            self.cancel_use_case = CancelTherapySessionUseCase(
                self.therapy_session_repository,
            )

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = self.queryset

        if not self.request.user.is_superuser:
            if hasattr(self.request.user, "therapist"):
                queryset = queryset.filter(therapist=self.request.user.therapist)
            elif hasattr(self.request.user, "patient"):
                queryset = queryset.filter(patient=self.request.user.patient)
            else:
                queryset = queryset.none()

        return queryset

    def create(self, request, *args, **kwargs):
        """Schedule a new therapy session using clean architecture."""
        try:
            # Extract data from request
            data = request.data

            # Create use case request
            use_case_request = ScheduleTherapySessionRequest(
                therapist_id=data.get("therapist_id"),
                patient_id=data.get("patient_id"),
                scheduled_at=datetime.fromisoformat(
                    data.get("scheduled_at").replace("Z", "+00:00"),
                ),
                session_type=SessionType(data.get("session_type")),
                target_audience=TargetAudience(data.get("target_audience")),
                notes=data.get("notes"),
            )

            # Execute use case
            response = self.schedule_use_case.execute(use_case_request)

            if response.success:
                serializer = self.get_serializer(
                    self._domain_to_django_model(response.session),
                )
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"error": response.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def start_session(self, request, pk=None):
        """Start a therapy session."""
        try:
            use_case_request = StartSessionRequest(
                session_id=int(pk),
                user_id=request.user.id,
            )

            response = self.start_use_case.execute(use_case_request)

            if response.success:
                return Response({"status": "Session started successfully"})
            return Response(
                {"error": response.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def end_session(self, request, pk=None):
        """End a therapy session."""
        try:
            use_case_request = EndSessionRequest(
                session_id=int(pk),
                user_id=request.user.id,
                summary=request.data.get("summary"),
                notes=request.data.get("notes"),
            )

            response = self.end_use_case.execute(use_case_request)

            if response.success:
                return Response({"status": "Session ended successfully"})
            return Response(
                {"error": response.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def cancel_session(self, request, pk=None):
        """Cancel a therapy session."""
        try:
            use_case_request = CancelSessionRequest(
                session_id=int(pk),
                user_id=request.user.id,
                reason=request.data.get("reason"),
            )

            response = self.cancel_use_case.execute(use_case_request)

            if response.success:
                return Response({"status": "Session cancelled successfully"})
            return Response(
                {"error": response.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def availability(self, request):
        """Get therapist availability."""
        try:
            therapist_id = request.query_params.get("therapist_id")
            date_str = request.query_params.get("date")

            if not therapist_id or not date_str:
                return Response(
                    {"error": "therapist_id and date are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            date = datetime.fromisoformat(date_str).date()
            available_slots = self.therapy_session_service.get_therapist_availability(
                int(therapist_id),
                date,
            )

            return Response(
                {
                    "available_slots": [slot.isoformat() for slot in available_slots],
                },
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get therapy session statistics."""
        try:
            therapist_id = request.query_params.get("therapist_id")
            patient_id = request.query_params.get("patient_id")

            stats = self.therapy_session_service.calculate_session_statistics(
                therapist_id=int(therapist_id) if therapist_id else None,
                patient_id=int(patient_id) if patient_id else None,
            )

            return Response(stats)

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _domain_to_django_model(self, domain_entity):
        """Convert domain entity to Django model for serialization."""
        try:
            return TherapySession.objects.get(id=domain_entity.id)
        except TherapySession.DoesNotExist:
            raise Http404("Session not found")


class DisorderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for mental health disorders.
    Read-only access to disorder information.
    """

    queryset = Disorder.objects.all()
    serializer_class = DisorderSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search disorders by symptoms or description."""
        try:
            query = request.query_params.get("q", "").strip()
            if not query:
                return Response(
                    {"error": 'Query parameter "q" is required'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Simple search implementation
            disorders = (
                Disorder.objects.filter(
                    name__icontains=query,
                )
                or Disorder.objects.filter(
                    description__icontains=query,
                )
                or Disorder.objects.filter(
                    symptoms__icontains=query,
                )
            )

            serializer = self.get_serializer(disorders, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatbotInteractionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chatbot interactions.
    Manages user conversations with the mental health chatbot.
    """

    queryset = ChatbotInteraction.objects.all()
    serializer_class = ChatbotInteractionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter to user's own interactions."""
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create interaction for the current user."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def recent(self, request):
        """Get recent interactions for the user."""
        try:
            limit = int(request.query_params.get("limit", 10))
            interactions = self.get_queryset().order_by("-interaction_date")[:limit]
            serializer = self.get_serializer(interactions, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
