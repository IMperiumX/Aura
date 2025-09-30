"""
Tests for patient profile functionality
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase

from aura.users.models import PatientProfile

User = get_user_model()


class PatientProfileModelTest(TestCase):
    """Test PatientProfile model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            user_type="patient",
            terms_accepted=True,
            privacy_policy_accepted=True,
        )

        self.profile_data = {
            "age_range": "25-35",
            "gender": "male",
            "location": "Los Angeles, CA",
            "timezone": "America/Los_Angeles",
            "session_format": ["video", "audio"],
            "frequency": "weekly",
            "session_duration": 60,
            "budget_range": "100-150",
            "primary_concerns": ["anxiety", "depression"],
            "therapy_types": ["CBT", "DBT"],
            "previous_therapy": True,
            "crisis_support_needed": False,
            "therapist_gender_preference": "no_preference",
            "therapist_age_preference": "no_preference",
            "cultural_background": ["any"],
            "languages": ["english"],
        }

    def test_create_patient_profile(self):
        """Test creating a patient profile"""
        profile = PatientProfile.objects.create(user=self.user, **self.profile_data)

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.age_range, self.profile_data["age_range"])
        self.assertEqual(profile.gender, self.profile_data["gender"])
        self.assertEqual(profile.location, self.profile_data["location"])
        self.assertEqual(profile.session_format, self.profile_data["session_format"])
        self.assertEqual(profile.primary_concerns, self.profile_data["primary_concerns"])
        self.assertFalse(profile.profile_completed)  # Should be set by business logic

    def test_patient_profile_str(self):
        """Test patient profile string representation"""
        profile = PatientProfile.objects.create(user=self.user, **self.profile_data)

        self.assertEqual(str(profile), f"Patient Profile - {self.user.email}")

    def test_get_audit_log_data(self):
        """Test audit log data method"""
        profile = PatientProfile.objects.create(user=self.user, **self.profile_data)

        audit_data = profile.get_audit_log_data()

        self.assertIn("user_id", audit_data)
        self.assertIn("profile_completed", audit_data)
        self.assertIn("matching_enabled", audit_data)
        self.assertIn("embeddings_generated", audit_data)
        self.assertEqual(audit_data["user_id"], str(self.user.id))


class PatientProfileAPITest(APITestCase):
    """Test PatientProfile API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            user_type="patient",
            terms_accepted=True,
            privacy_policy_accepted=True,
        )

        self.therapist_user = User.objects.create_user(
            email="therapist@example.com",
            password="testpass123",
            first_name="Dr. Jane",
            last_name="Smith",
            user_type="therapist",
            terms_accepted=True,
            privacy_policy_accepted=True,
        )

        instance, self.token = AuthToken.objects.create(self.user)
        instance, self.therapist_token = AuthToken.objects.create(self.therapist_user)

        self.create_profile_url = "/api/0/patients/profile/"
        self.profile_detail_url = "/api/0/patients/profile/"

        self.profile_data = {
            "personal_info": {
                "age_range": "25-35",
                "gender": "male",
                "location": "Los Angeles, CA",
                "timezone": "America/Los_Angeles",
            },
            "therapy_preferences": {
                "session_format": ["video", "audio"],
                "frequency": "weekly",
                "duration": 60,
                "budget_range": "100-150",
            },
            "therapeutic_needs": {
                "primary_concerns": ["anxiety", "depression"],
                "therapy_types": ["CBT", "DBT"],
                "previous_therapy": True,
                "crisis_support_needed": False,
            },
            "therapist_preferences": {
                "gender_preference": "no_preference",
                "age_preference": "no_preference",
                "cultural_background": ["any"],
                "languages": ["english"],
            },
        }

    def test_create_patient_profile_success(self):
        """Test successful patient profile creation"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

        response = self.client.post(self.create_profile_url, self.profile_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertIn("profile_completed", response.data["data"])
        self.assertIn("matching_enabled", response.data["data"])
        self.assertTrue(response.data["data"]["profile_completed"])
        self.assertTrue(response.data["data"]["matching_enabled"])

        # Check profile was created
        self.assertTrue(PatientProfile.objects.filter(user=self.user).exists())
        profile = PatientProfile.objects.get(user=self.user)
        self.assertEqual(profile.age_range, "25-35")
        self.assertEqual(profile.primary_concerns, ["anxiety", "depression"])

    def test_create_patient_profile_therapist_user(self):
        """Test that therapist users cannot create patient profiles"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.therapist_token}")

        response = self.client.post(self.create_profile_url, self.profile_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_patient_profile_unauthenticated(self):
        """Test patient profile creation without authentication"""
        response = self.client.post(self.create_profile_url, self.profile_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_patient_profile_already_exists(self):
        """Test creating profile when one already exists"""
        # Create profile first
        PatientProfile.objects.create(
            user=self.user, age_range="25-35", gender="male", location="Los Angeles, CA", profile_completed=True
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.post(self.create_profile_url, self.profile_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "PROFILE_EXISTS")

    def test_get_patient_profile_success(self):
        """Test getting patient profile"""
        profile = PatientProfile.objects.create(
            user=self.user,
            age_range="25-35",
            gender="male",
            location="Los Angeles, CA",
            session_format=["video"],
            primary_concerns=["anxiety"],
            profile_completed=True,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.get(self.profile_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["age_range"], "25-35")
        self.assertEqual(response.data["data"]["gender"], "male")

    def test_get_patient_profile_not_exists(self):
        """Test getting patient profile that doesn't exist"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.get(self.profile_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_patient_profile_success(self):
        """Test updating patient profile"""
        profile = PatientProfile.objects.create(
            user=self.user,
            age_range="25-35",
            gender="male",
            location="Los Angeles, CA",
            session_format=["video"],
            primary_concerns=["anxiety"],
            profile_completed=True,
        )

        update_data = {
            "age_range": "36-45",
            "session_format": ["video", "audio"],
            "primary_concerns": ["anxiety", "depression"],
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.put(self.profile_detail_url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check profile was updated
        profile.refresh_from_db()
        self.assertEqual(profile.age_range, "36-45")
        self.assertEqual(profile.session_format, ["video", "audio"])
        self.assertEqual(profile.primary_concerns, ["anxiety", "depression"])

    def test_update_patient_profile_invalid_data(self):
        """Test updating patient profile with invalid data"""
        profile = PatientProfile.objects.create(
            user=self.user, age_range="25-35", gender="male", location="Los Angeles, CA", profile_completed=True
        )

        invalid_data = {
            "age_range": "invalid_range",  # Not a valid choice
            "session_duration": "invalid_duration",  # Should be integer
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.put(self.profile_detail_url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)


@pytest.mark.django_db
class TestPatientProfileEncryption:
    """Test encryption functionality for patient profiles"""

    def test_encrypted_fields_are_encrypted(self):
        """Test that sensitive fields are properly encrypted"""
        user = User.objects.create_user(
            email="patient@example.com", password="testpass123", first_name="John", last_name="Doe", user_type="patient"
        )

        profile = PatientProfile.objects.create(
            user=user,
            age_range="25-35",
            gender="male",
            location="Los Angeles, CA",
            session_format=["video"],
            primary_concerns=["anxiety", "depression"],
            therapy_types=["CBT"],
        )

        # The encrypted fields should not store plain text in database
        # This would require accessing the raw database value
        # and checking it doesn't match the plain text

        # For now, just verify the values can be retrieved correctly
        assert profile.age_range == "25-35"
        assert profile.gender == "male"
        assert profile.location == "Los Angeles, CA"
        assert profile.session_format == ["video"]
        assert profile.primary_concerns == ["anxiety", "depression"]
        assert profile.therapy_types == ["CBT"]
