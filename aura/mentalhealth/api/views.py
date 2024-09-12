from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from aura.mentalhealth.api.filters import TherapySessionFilter
from aura.mentalhealth.api.serializers import ChatbotInteractionSerializer
from aura.mentalhealth.api.serializers import DisorderSerializer
from aura.mentalhealth.api.serializers import TherapyApproachSerializer
from aura.mentalhealth.api.serializers import TherapySessionSerializer
from aura.mentalhealth.models import ChatbotInteraction
from aura.mentalhealth.models import Disorder
from aura.mentalhealth.models import TherapyApproach
from aura.mentalhealth.models import TherapySession
from aura.users.api.permissions import ReadOnly


class TherapyApproachViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TherapyApproach.objects.all()
    serializer_class = TherapyApproachSerializer
    permission_classes = [IsAuthenticated | ReadOnly]


class TherapySessionViewSet(viewsets.ModelViewSet):
    queryset = TherapySession.objects.all()
    serializer_class = TherapySessionSerializer
    filterset_class = TherapySessionFilter
    search_fields = ["summary", "notes"]
    ordering_fields = ["scheduled_at", "started_at", "ended_at"]

    @action(detail=True, methods=["post"])
    def start_session(self, request, pk=None):
        session = self.get_object()
        session.start()
        session.save()
        return Response({"status": "Session started"})

    @action(detail=True, methods=["post"])
    def complete_session(self, request, pk=None):
        session = self.get_object()
        session.complete()
        session.save()
        return Response({"status": "Session completed"})

    @action(detail=True, methods=["post"])
    def cancel_session(self, request, pk=None):
        session = self.get_object()
        session.cancel()
        session.save()
        return Response({"status": "Session cancelled"})


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
