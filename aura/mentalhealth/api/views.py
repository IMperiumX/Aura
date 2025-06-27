import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from aura.analytics import AnalyticsRecordingMixin
from aura.mentalhealth.api.filters import TherapySessionFilter
from aura.mentalhealth.api.serializers import (
    ChatbotInteractionSerializer,
    DisorderSerializer,
    TherapyApproachSerializer,
    TherapySessionSerializer,
)
from aura.mentalhealth.models import (
    ChatbotInteraction,
    Disorder,
    TherapyApproach,
    TherapySession,
)
from aura.users.api.permissions import ReadOnly

logger = logging.getLogger(__name__)


class TherapyApproachViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TherapyApproach.objects.all()
    serializer_class = TherapyApproachSerializer
    permission_classes = [IsAuthenticated | ReadOnly]


class TherapySessionViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
    queryset = TherapySession.objects.all()
    serializer_class = TherapySessionSerializer
    filterset_class = TherapySessionFilter
    search_fields = ["summary", "notes"]
    ordering_fields = ["scheduled_at", "started_at", "ended_at"]

    def perform_create(self, serializer):
        """Create therapy session with analytics tracking."""
        session = serializer.save()

        try:
            self.record_analytics_event(
                "therapy_session.created",
                instance=session,
                request=self.request,
                session_id=session.id,
                therapist_id=session.therapist.id,
                patient_id=session.patient.id,
                session_type=session.session_type,
                target_audience=session.target_audience,
                scheduled_at=session.scheduled_at.isoformat(),
                recurrence_pattern=(
                    str(session.recurrences) if session.recurrences else None
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record therapy session creation event: {e}")

    def perform_update(self, serializer):
        """Update therapy session with analytics tracking."""
        old_instance = self.get_object()
        session = serializer.save()

        # Track status changes
        if old_instance.status != session.status:
            try:
                if session.status == TherapySession.SessionStatus.ACCEPTED:
                    self.record_analytics_event(
                        "therapy_session.accepted",
                        instance=session,
                        request=self.request,
                        session_id=session.id,
                        therapist_id=session.therapist.id,
                        patient_id=session.patient.id,
                    )
                elif session.status == TherapySession.SessionStatus.CANCELLED:
                    notice_hours = None
                    if session.scheduled_at > timezone.now():
                        notice_delta = session.scheduled_at - timezone.now()
                        notice_hours = int(notice_delta.total_seconds() / 3600)

                    self.record_analytics_event(
                        "therapy_session.cancelled",
                        instance=session,
                        request=self.request,
                        session_id=session.id,
                        therapist_id=session.therapist.id,
                        patient_id=session.patient.id,
                        cancelled_by="therapist",  # Assuming therapist is making the change
                        notice_hours=notice_hours,
                        reason=getattr(session, "cancellation_reason", None),
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to record therapy session status change event: {e}"
                )

    @action(detail=True, methods=["post"])
    def start_session(self, request, pk=None):
        """Start a therapy session with analytics tracking."""
        session = self.get_object()

        if session.started_at:
            return Response({"error": "Session already started"}, status=400)

        session.started_at = timezone.now()
        session.status = TherapySession.SessionStatus.ACCEPTED
        session.save()

        try:
            # Calculate delay if any
            delay_minutes = None
            if session.started_at > session.scheduled_at:
                delay = session.started_at - session.scheduled_at
                delay_minutes = int(delay.total_seconds() / 60)

            self.record_analytics_event(
                "therapy_session.started",
                instance=session,
                request=request,
                session_id=session.id,
                therapist_id=session.therapist.id,
                patient_id=session.patient.id,
                session_type=session.session_type,
                actual_start_time=session.started_at.isoformat(),
                scheduled_start_time=session.scheduled_at.isoformat(),
                delay_minutes=delay_minutes,
            )
        except Exception as e:
            logger.warning(f"Failed to record therapy session start event: {e}")

        return Response({"status": "Session started"})

    @action(detail=True, methods=["post"])
    def complete_session(self, request, pk=None):
        """Complete a therapy session with analytics tracking."""
        session = self.get_object()

        if not session.started_at:
            return Response({"error": "Session not started"}, status=400)

        if session.ended_at:
            return Response({"error": "Session already completed"}, status=400)

        session.ended_at = timezone.now()
        session.status = TherapySession.SessionStatus.COMPLETED
        session.save()

        try:
            # Calculate duration
            duration = session.ended_at - session.started_at
            duration_minutes = int(duration.total_seconds() / 60)

            self.record_analytics_event(
                "therapy_session.completed",
                instance=session,
                request=request,
                session_id=session.id,
                therapist_id=session.therapist.id,
                patient_id=session.patient.id,
                session_type=session.session_type,
                duration_minutes=duration_minutes,
                has_notes=bool(session.notes),
                has_summary=bool(session.summary),
            )
        except Exception as e:
            logger.warning(f"Failed to record therapy session completion event: {e}")

        return Response({"status": "Session completed"})

    @action(detail=True, methods=["post"])
    def cancel_session(self, request, pk=None):
        """Cancel a therapy session with analytics tracking."""
        session = self.get_object()
        reason = request.data.get("reason", "")

        session.status = TherapySession.SessionStatus.CANCELLED
        session.save()

        try:
            # Calculate notice hours
            notice_hours = None
            if session.scheduled_at > timezone.now():
                notice_delta = session.scheduled_at - timezone.now()
                notice_hours = int(notice_delta.total_seconds() / 3600)

            # Determine who cancelled (therapist vs patient)
            cancelled_by = "therapist"  # Default assumption
            if hasattr(request.user, "patient_profile"):
                cancelled_by = "patient"

            self.record_analytics_event(
                "therapy_session.cancelled",
                instance=session,
                request=request,
                session_id=session.id,
                therapist_id=session.therapist.id,
                patient_id=session.patient.id,
                cancelled_by=cancelled_by,
                notice_hours=notice_hours,
                reason=reason,
            )
        except Exception as e:
            logger.warning(f"Failed to record therapy session cancellation event: {e}")

        return Response({"status": "Session cancelled"})


class ChatbotInteractionViewSet(viewsets.ModelViewSet, AnalyticsRecordingMixin):
    queryset = ChatbotInteraction.objects.all()
    serializer_class = ChatbotInteractionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Create chatbot interaction with analytics tracking."""
        interaction = serializer.save()

        try:
            self.record_analytics_event(
                "chatbot.interaction",
                instance=interaction,
                request=self.request,
                interaction_id=interaction.id,
                patient_id=(
                    interaction.patient.id if hasattr(interaction, "patient") else None
                ),
                message_count=getattr(interaction, "message_count", 1),
                session_duration_seconds=getattr(
                    interaction, "session_duration_seconds", None
                ),
                satisfaction_score=getattr(interaction, "satisfaction_score", None),
            )
        except Exception as e:
            logger.warning(f"Failed to record chatbot interaction event: {e}")


class DisorderViewSet(viewsets.ModelViewSet):
    queryset = Disorder.objects.all()
    serializer_class = DisorderSerializer
    permission_classes = [IsAuthenticated | ReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name"]
