from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Clean Architecture imports
from aura.core.application.services.patient_profile_service import PatientProfileService
from aura.core.infrastructure.repositories.django_patient_profile_repository import DjangoPatientProfileRepository
from aura.core.permissions import IsPatient

from ..models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    """Serializer for Patient Profile"""

    class Meta:
        model = PatientProfile
        exclude = ["user", "profile_embeddings"]  # Exclude sensitive embedding data
        read_only_fields = ["profile_completed", "matching_enabled", "embeddings_generated", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        """Update patient profile and mark as completed if all required fields are present"""
        instance = super().update(instance, validated_data)

        # Check if profile is complete
        required_fields = [
            "age_range",
            "gender",
            "location",
            "session_format",
            "frequency",
            "budget_range",
            "primary_concerns",
            "therapy_types",
        ]

        is_complete = all(getattr(instance, field, None) for field in required_fields)

        if is_complete and not instance.profile_completed:
            instance.profile_completed = True
            instance.matching_enabled = True
            instance.save()

        return instance


class PatientProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Patient Profile"""

    personal_info = serializers.JSONField(write_only=True)
    therapy_preferences = serializers.JSONField(write_only=True)
    therapeutic_needs = serializers.JSONField(write_only=True)
    therapist_preferences = serializers.JSONField(write_only=True)

    class Meta:
        model = PatientProfile
        fields = ["personal_info", "therapy_preferences", "therapeutic_needs", "therapist_preferences"]

    def create(self, validated_data):
        """Create patient profile from nested data"""
        personal_info = validated_data.pop("personal_info")
        therapy_preferences = validated_data.pop("therapy_preferences")
        therapeutic_needs = validated_data.pop("therapeutic_needs")
        therapist_preferences = validated_data.pop("therapist_preferences")

        user = self.context["request"].user

        # Create profile with nested data
        profile = PatientProfile.objects.create(
            user=user,
            age_range=personal_info.get("age_range"),
            gender=personal_info.get("gender"),
            location=personal_info.get("location"),
            timezone=personal_info.get("timezone", "America/New_York"),
            session_format=therapy_preferences.get("session_format", []),
            frequency=therapy_preferences.get("frequency", "weekly"),
            session_duration=therapy_preferences.get("duration", 60),
            budget_range=therapy_preferences.get("budget_range"),
            primary_concerns=therapeutic_needs.get("primary_concerns", []),
            therapy_types=therapeutic_needs.get("therapy_types", []),
            previous_therapy=therapeutic_needs.get("previous_therapy", False),
            crisis_support_needed=therapeutic_needs.get("crisis_support_needed", False),
            therapist_gender_preference=therapist_preferences.get("gender_preference", "no_preference"),
            therapist_age_preference=therapist_preferences.get("age_preference", "no_preference"),
            cultural_background=therapist_preferences.get("cultural_background", []),
            languages=therapist_preferences.get("languages", ["english"]),
            profile_completed=True,
            matching_enabled=True,
        )

        return profile


class PatientProfileCreateView(APIView):
    """
    Create patient profile using Clean Architecture
    POST /api/0/patients/profile/
    """

    permission_classes = [IsPatient]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        patient_profile_repository = DjangoPatientProfileRepository()
        self._profile_service = PatientProfileService(patient_profile_repository)

    def post(self, request):
        serializer = PatientProfileCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Use the patient profile service (Clean Architecture)
            response = self._profile_service.create_profile(
                user=request.user,
                personal_info=serializer.validated_data["personal_info"],
                therapy_preferences=serializer.validated_data["therapy_preferences"],
                therapeutic_needs=serializer.validated_data["therapeutic_needs"],
                therapist_preferences=serializer.validated_data["therapist_preferences"],
            )

            if response.success:
                profile_data = self._profile_service.serialize_profile(response.profile)
                return Response(
                    {
                        "data": {
                            "id": profile_data["id"],
                            "profile_completed": profile_data["profile_completed"],
                            "matching_enabled": profile_data["matching_enabled"],
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


class PatientProfileDetailView(APIView):
    """
    Get or update patient profile using Clean Architecture
    GET/PUT /api/0/patients/profile/
    """

    permission_classes = [IsPatient]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        patient_profile_repository = DjangoPatientProfileRepository()
        self._profile_service = PatientProfileService(patient_profile_repository)

    def get(self, request):
        # Use the patient profile service (Clean Architecture)
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
        # Use the patient profile service (Clean Architecture)
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
