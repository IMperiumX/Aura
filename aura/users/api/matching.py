from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from aura.core.matching import MatchFeedbackProcessor
from aura.core.matching import TherapistMatcher
from aura.core.permissions import IsPatient

from ..models import PatientProfile


class MatchFeedbackSerializer(serializers.Serializer):
    """Serializer for match feedback"""

    FEEDBACK_TYPE_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("neutral", "Neutral"),
    ]

    therapist_id = serializers.UUIDField()
    feedback_type = serializers.ChoiceField(choices=FEEDBACK_TYPE_CHOICES)
    feedback_details = serializers.JSONField()
    preference_updates = serializers.JSONField(required=False)


class PatientMatchesView(APIView):
    """
    Get therapist matches for patient
    GET /api/0/patients/matches/
    """

    permission_classes = [IsPatient]

    def get(self, request):
        patient_profile = get_object_or_404(PatientProfile, user=request.user)

        # Check if profile is complete
        if not patient_profile.profile_completed:
            return Response(
                {
                    "error": {
                        "code": "INCOMPLETE_PROFILE",
                        "message": "Patient profile must be completed before matching",
                        "details": {},
                    },
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get query parameters
        limit = min(int(request.GET.get("limit", 10)), 20)
        refresh = request.GET.get("refresh", "false").lower() == "true"
        location_radius = int(request.GET.get("location_radius", 25))

        # Check cache first (unless refresh requested)
        cache_key = f"patient_matches_{request.user.id}_{limit}_{location_radius}"

        if not refresh:
            cached_matches = cache.get(cache_key)
            if cached_matches:
                return Response(
                    {
                        "data": {
                            "matches": cached_matches["matches"],
                            "total_matches": cached_matches["total_matches"],
                            "generated_at": cached_matches["generated_at"],
                            "next_refresh_available": cached_matches["next_refresh_available"],
                        },
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    }
                )

        # Generate new matches
        matcher = TherapistMatcher(patient_profile)
        matches = matcher.find_matches(limit=limit, location_radius=location_radius)

        # Prepare response data
        now = timezone.now()
        next_refresh = now + timezone.timedelta(hours=1)

        match_data = {
            "matches": matches,
            "total_matches": len(matches),
            "generated_at": now.isoformat(),
            "next_refresh_available": next_refresh.isoformat(),
        }

        # Cache for 1 hour
        cache.set(cache_key, match_data, 3600)

        return Response(
            {
                "data": match_data,
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            }
        )


class MatchFeedbackView(APIView):
    """
    Submit feedback on therapist matches
    POST /api/0/patients/matches/feedback/
    """

    permission_classes = [IsPatient]

    def post(self, request):
        patient_profile = get_object_or_404(PatientProfile, user=request.user)

        serializer = MatchFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            # Process the feedback
            result = MatchFeedbackProcessor.process_feedback(
                patient_profile=patient_profile,
                therapist_id=str(serializer.validated_data["therapist_id"]),
                feedback_data=serializer.validated_data,
            )

            # Clear cached matches since preferences may have changed
            cache_pattern = f"patient_matches_{request.user.id}_*"
            cache.delete_many([cache_pattern])

            return Response(
                {
                    "data": result,
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid feedback data",
                    "details": {"field_errors": serializer.errors},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
