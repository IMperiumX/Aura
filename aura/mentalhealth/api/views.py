from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from aura.mentalhealth.api.serializers import TherapySessionSerializer
from aura.mentalhealth.models import TherapySession
from aura.users.api.permissions import (IsAdmin, IsOwnerOrAdmin,
                                        IsTherapistOrAdmin)
from aura.users.models import User


class TherapySessionViewSet(viewsets.ModelViewSet):
    queryset = TherapySession.objects.select_related("therapist", "patient")
    serializer_class = TherapySessionSerializer
    permission_classes = [IsOwnerOrAdmin | IsTherapistOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        "status",
        "scheduled_at",
        "therapist",
        "patient",
    ]
    ordering_fields = [
        "scheduled_at",
        "status",
    ]

    def get_serializer_class(self):
        return TherapySessionSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = TherapySession.SessionStatus.CANCELLED
        instance.save()
        return Response(status=HTTP_204_NO_CONTENT)
