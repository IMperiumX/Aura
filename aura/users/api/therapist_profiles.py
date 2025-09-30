from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Clean Architecture imports
from aura.core.application.services.therapist_profile_service import TherapistProfileService
from aura.core.infrastructure.repositories.django_therapist_profile_repository import DjangoTherapistProfileRepository
from aura.core.permissions import IsTherapist

from ..models import TherapistProfile


class TherapistProfileSerializer(serializers.ModelSerializer):
    """Serializer for Therapist Profile"""

    class Meta:
        model = TherapistProfile
        exclude = ["user", "profile_embeddings", "verification_documents"]  # Exclude sensitive data
        read_only_fields = [
            "verification_status",
            "verified_at",
            "verified_by",
            "profile_completed",
            "available_for_matching",
            "embeddings_generated",
            "created_at",
            "updated_at",
        ]

    def update(self, instance, validated_data):
        """Update therapist profile and mark as completed if all required fields are present"""
        instance = super().update(instance, validated_data)

        # Check if profile is complete
        required_fields = [
            "license_number",
            "license_state",
            "years_experience",
            "credentials",
            "specializations",
            "therapeutic_approaches",
            "session_formats",
            "base_rate",
        ]

        is_complete = all(getattr(instance, field, None) for field in required_fields)

        if is_complete and not instance.profile_completed:
            instance.profile_completed = True
            # Only enable matching if verified
            if instance.is_verified:
                instance.available_for_matching = True
            instance.save()

        return instance


class TherapistProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Therapist Profile"""

    professional_info = serializers.JSONField(write_only=True)
    practice_details = serializers.JSONField(write_only=True)
    availability = serializers.JSONField(write_only=True)
    rates = serializers.JSONField(write_only=True)

    class Meta:
        model = TherapistProfile
        fields = ["professional_info", "practice_details", "availability", "rates"]

    def create(self, validated_data):
        """Create therapist profile from nested data"""
        professional_info = validated_data.pop("professional_info")
        practice_details = validated_data.pop("practice_details")
        availability = validated_data.pop("availability")
        rates = validated_data.pop("rates")

        user = self.context["request"].user

        # Create profile with nested data
        profile = TherapistProfile.objects.create(
            user=user,
            license_number=professional_info.get("license_number"),
            license_state=professional_info.get("license_state"),
            years_experience=professional_info.get("years_experience", 0),
            credentials=professional_info.get("credentials", []),
            specializations=professional_info.get("specializations", []),
            therapeutic_approaches=practice_details.get("therapeutic_approaches", []),
            session_formats=practice_details.get("session_formats", []),
            languages=practice_details.get("languages", ["english"]),
            age_groups=practice_details.get("age_groups", []),
            timezone=availability.get("timezone", "America/New_York"),
            session_duration=availability.get("session_duration", [45, 60]),
            weekly_hours=availability.get("weekly_hours", 40),
            evening_availability=availability.get("evening_availability", False),
            weekend_availability=availability.get("weekend_availability", False),
            base_rate=str(rates.get("base_rate", 0)),
            sliding_scale_available=rates.get("sliding_scale_available", False),
            insurance_accepted=rates.get("insurance_accepted", []),
            profile_completed=True,
            verification_status="pending",
        )

        return profile


class TherapistSummarySerializer(serializers.ModelSerializer):
    """Serializer for therapist summary data (for matching results)"""

    name = serializers.SerializerMethodField()

    class Meta:
        model = TherapistProfile
        fields = ["name", "credentials", "years_experience", "specializations", "base_rate"]

    def get_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"


class TherapistProfileCreateView(APIView):
    """
    Create therapist profile using Clean Architecture
    POST /api/0/therapists/profile/
    """

    permission_classes = [IsTherapist]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        therapist_profile_repository = DjangoTherapistProfileRepository()
        self._profile_service = TherapistProfileService(therapist_profile_repository)

    def post(self, request):
        serializer = TherapistProfileCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Use the therapist profile service (Clean Architecture)
            response = self._profile_service.create_profile(
                user=request.user,
                professional_info=serializer.validated_data["professional_info"],
                practice_details=serializer.validated_data["practice_details"],
                availability=serializer.validated_data["availability"],
                rates=serializer.validated_data["rates"],
            )

            if response.success:
                profile_data = self._profile_service.serialize_profile(response.profile)
                return Response(
                    {
                        "data": {
                            "id": profile_data["id"],
                            "verification_status": profile_data["verification_status"],
                            "profile_completed": profile_data["profile_completed"],
                            "available_for_matching": profile_data["available_for_matching"],
                            "embeddings_generated": profile_data["embeddings_generated"],
                            "created_at": profile_data["created_at"],
                        },
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "error": {
                        "code": "PROFILE_CREATION_ERROR",
                        "message": response.error_message,
                        "details": {},
                    },
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
                    "message": "Invalid profile data",
                    "details": {"field_errors": serializer.errors},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class TherapistProfileDetailView(APIView):
    """
    Get or update therapist profile using Clean Architecture
    GET/PUT /api/0/therapists/profile/
    """

    permission_classes = [IsTherapist]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        therapist_profile_repository = DjangoTherapistProfileRepository()
        self._profile_service = TherapistProfileService(therapist_profile_repository)

    def get(self, request):
        # Use the therapist profile service (Clean Architecture)
        response = self._profile_service.get_profile(request.user)

        if response.success:
            profile_data = self._profile_service.serialize_profile(response.profile)
            return Response(
                {
                    "data": profile_data,
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                }
            )
        return Response(
            {
                "error": {
                    "code": "PROFILE_NOT_FOUND",
                    "message": response.error_message,
                    "details": {},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    def put(self, request):
        # Use the therapist profile service (Clean Architecture)
        response = self._profile_service.update_profile(request.user, request.data)

        if response.success:
            profile_data = self._profile_service.serialize_profile(response.profile)
            return Response(
                {
                    "data": profile_data,
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                }
            )
        return Response(
            {
                "error": {
                    "code": "PROFILE_UPDATE_ERROR",
                    "message": response.error_message,
                    "details": {},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
