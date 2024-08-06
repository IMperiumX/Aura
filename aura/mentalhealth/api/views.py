from datetime import timezone

from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import permissions
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from aura.mentalhealth.api.filters import TherapySessionFilter
from aura.mentalhealth.api.serializers import ChatbotInteractionSerializer
from aura.mentalhealth.api.serializers import DisorderSerializer
from aura.mentalhealth.api.serializers import TherapyApproachSerializer
from aura.mentalhealth.api.serializers import TherapySessionSerializer
from aura.mentalhealth.models import ChatbotInteraction
from aura.mentalhealth.models import Disorder
from aura.mentalhealth.models import TherapyApproach
from aura.mentalhealth.models import TherapySession
from aura.users.api.permissions import IsPatient
from aura.users.api.permissions import IsTherapist
from aura.users.api.permissions import ReadOnly


class TherapyApproachViewSet(viewsets.ModelViewSet):
    queryset = TherapyApproach.objects.all()
    serializer_class = TherapyApproachSerializer
    permission_classes = [IsAuthenticated | ReadOnly]


class TherapySessionViewSet(viewsets.ModelViewSet):
    queryset = TherapySession.objects.select_related("therapist", "patient")
    serializer_class = TherapySessionSerializer
    permission_classes = [IsAuthenticated | ReadOnly, IsTherapist | IsPatient]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TherapySessionFilter
    ordering_fields = [
        "scheduled_at",
        "status",
    ]

    def get_queryset(self):
        if hasattr(self.request.user, "therapist_profile"):
            return self.queryset.filter(therapist__user=self.request.user)
        return self.queryset.filter(patient__user=self.request.user)

    def get_serializer_class(self):
        return TherapySessionSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = TherapySession.SessionStatus.CANCELLED
        instance.save()
        return Response(status=HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(therapist=self.request.user)

    @action(detail=True, methods=["post"])
    def cancel_session(self, request, pk=None):
        session = self.get_object()
        if session.status != TherapySession.SessionStatus.PENDING:
            return Response(
                {"status": "Session cannot be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.status = TherapySession.SessionStatus.CANCELLED
        session.save()
        return Response({"status": _("Session cancelled")})

    @action(detail=False)
    def upcoming_sessions(self, request):
        from django.db.models import Q

        upcoming = TherapySession.objects.filter(
            Q(therapist=request.user) | Q(patient=request.user),
            status=TherapySession.SessionStatus.ACCEPTED,
            scheduled_at__gt=timezone.now(),
        )
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def past_sessions(self, request):
        from django.db.models import Q

        past = TherapySession.objects.filter(
            Q(therapist=request.user) | Q(patient=request.user),
            status=TherapySession.SessionStatus.ACCEPTED,
            scheduled_at__lt=timezone.now(),
        )
        serializer = self.get_serializer(past, many=True)
        return Response(serializer.data)


class ChatbotInteractionViewSet(viewsets.ModelViewSet):
    queryset = ChatbotInteraction.objects.all()
    serializer_class = ChatbotInteractionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False)
    def recent_interactions(self, request):
        recent = ChatbotInteraction.objects.filter(
            user=request.user,
        ).order_by(
            "-created",
        )[:5]
        serializer = self.get_serializer(recent, many=True)
        return Response(serializer.data)


class DisorderViewSet(viewsets.ModelViewSet):
    queryset = Disorder.objects.all()
    serializer_class = DisorderSerializer
    permission_classes = [IsAuthenticated | ReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name"]
