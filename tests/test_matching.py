"""
Tests for the therapist matching system
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase

from aura.core.matching import MatchFeedbackProcessor
from aura.core.matching import TherapistMatcher
from aura.users.models import PatientProfile
from aura.users.models import TherapistProfile

User = get_user_model()


class TherapistMatcherTest(TestCase):
    """Test TherapistMatcher class"""

    def setUp(self):
        # Create patient
        self.patient = User.objects.create_user(
            email="patient@example.com", password="testpass123", first_name="John", last_name="Doe", user_type="patient"
        )

        self.patient_profile = PatientProfile.objects.create(
            user=self.patient,
            age_range="25-35",
            gender="male",
            location="Los Angeles, CA",
            session_format=["video"],
            frequency="weekly",
            session_duration=60,
            budget_range="100-150",
            primary_concerns=["anxiety", "depression"],
            therapy_types=["CBT"],
            profile_completed=True,
            matching_enabled=True,
        )

        # Create therapist
        self.therapist = User.objects.create_user(
            email="therapist@example.com",
            password="testpass123",
            first_name="Dr. Jane",
            last_name="Smith",
            user_type="therapist",
        )

        self.therapist_profile = TherapistProfile.objects.create(
            user=self.therapist,
            license_number="LIC123456",
            license_state="CA",
            years_experience=5,
            credentials=["LMFT"],
            specializations=["anxiety", "depression"],
            therapeutic_approaches=["CBT", "DBT"],
            session_formats=["video", "audio"],
            languages=["english"],
            age_groups=["adults"],
            base_rate="125",
            sliding_scale_available=True,
            insurance_accepted=["Aetna"],
            verification_status="approved",
            profile_completed=True,
            available_for_matching=True,
        )

    def test_find_matches_basic(self):
        """Test basic matching functionality"""
        matcher = TherapistMatcher(self.patient_profile)
        matches = matcher.find_matches(limit=5)

        self.assertEqual(len(matches), 1)
        match = matches[0]

        self.assertEqual(match["therapist_id"], str(self.therapist.id))
        self.assertGreater(match["compatibility_score"], 0.3)  # Above threshold
        self.assertIsInstance(match["match_reasons"], list)
        self.assertIn("therapist_summary", match)

    def test_find_matches_no_available_therapists(self):
        """Test matching when no therapists are available"""
        # Mark therapist as unavailable
        self.therapist_profile.available_for_matching = False
        self.therapist_profile.save()

        matcher = TherapistMatcher(self.patient_profile)
        matches = matcher.find_matches(limit=5)

        self.assertEqual(len(matches), 0)

    def test_find_matches_unverified_therapist(self):
        """Test matching excludes unverified therapists"""
        # Mark therapist as unverified
        self.therapist_profile.verification_status = "pending"
        self.therapist_profile.save()

        matcher = TherapistMatcher(self.patient_profile)
        matches = matcher.find_matches(limit=5)

        self.assertEqual(len(matches), 0)

    def test_vector_similarity_calculation(self):
        """Test vector similarity calculation"""
        matcher = TherapistMatcher(self.patient_profile)
        similarity = matcher._calculate_vector_similarity(self.therapist_profile)

        # Should have high similarity due to matching concerns/specializations
        self.assertGreater(similarity, 0.5)

    def test_availability_compatibility(self):
        """Test availability compatibility calculation"""
        matcher = TherapistMatcher(self.patient_profile)
        compatibility = matcher._calculate_availability_compatibility(self.therapist_profile)

        # Should have good compatibility
        self.assertGreater(compatibility, 0.5)

    def test_budget_compatibility_within_range(self):
        """Test budget compatibility when therapist rate is within range"""
        matcher = TherapistMatcher(self.patient_profile)
        compatibility = matcher._calculate_budget_compatibility(self.therapist_profile)

        # Therapist rate (125) is within patient budget (100-150)
        self.assertEqual(compatibility, 1.0)

    def test_budget_compatibility_outside_range(self):
        """Test budget compatibility when therapist rate is outside range"""
        # Set therapist rate too high
        self.therapist_profile.base_rate = "200"
        self.therapist_profile.save()

        matcher = TherapistMatcher(self.patient_profile)
        compatibility = matcher._calculate_budget_compatibility(self.therapist_profile)

        # Should have low compatibility
        self.assertLess(compatibility, 0.5)

    def test_get_therapist_summary(self):
        """Test getting therapist summary data"""
        matcher = TherapistMatcher(self.patient_profile)
        summary = matcher._get_therapist_summary(self.therapist_profile)

        self.assertIn("name", summary)
        self.assertIn("credentials", summary)
        self.assertIn("years_experience", summary)
        self.assertIn("specializations", summary)
        self.assertIn("session_rate", summary)
        self.assertIn("availability_preview", summary)

        self.assertEqual(summary["name"], f"Dr. {self.therapist.first_name} {self.therapist.last_name}")
        self.assertEqual(summary["years_experience"], 5)


class MatchFeedbackProcessorTest(TestCase):
    """Test MatchFeedbackProcessor class"""

    def setUp(self):
        self.patient = User.objects.create_user(
            email="patient@example.com", password="testpass123", first_name="John", last_name="Doe", user_type="patient"
        )

        self.patient_profile = PatientProfile.objects.create(
            user=self.patient,
            age_range="25-35",
            primary_concerns=["anxiety"],
            profile_completed=True,
            embeddings_generated=True,
        )

        self.therapist = User.objects.create_user(
            email="therapist@example.com",
            password="testpass123",
            first_name="Dr. Jane",
            last_name="Smith",
            user_type="therapist",
        )

    def test_process_positive_feedback(self):
        """Test processing positive feedback"""
        feedback_data = {
            "feedback_type": "positive",
            "feedback_details": {
                "liked_aspects": ["specialization_match", "availability"],
                "overall_rating": 4,
                "would_book": True,
            },
            "preference_updates": {"increase_weight": ["therapeutic_approach"]},
        }

        result = MatchFeedbackProcessor.process_feedback(
            patient_profile=self.patient_profile, therapist_id=str(self.therapist.id), feedback_data=feedback_data
        )

        self.assertTrue(result["feedback_recorded"])
        self.assertTrue(result["preferences_updated"])
        self.assertTrue(result["new_matches_available"])
        self.assertIn("improvement_summary", result)

        # Check that embeddings were marked for regeneration
        self.patient_profile.refresh_from_db()
        self.assertFalse(self.patient_profile.embeddings_generated)

    def test_process_negative_feedback(self):
        """Test processing negative feedback"""
        feedback_data = {
            "feedback_type": "negative",
            "feedback_details": {"disliked_aspects": ["location_too_far"], "overall_rating": 2, "would_book": False},
            "preference_updates": {"decrease_weight": ["location_proximity"]},
        }

        result = MatchFeedbackProcessor.process_feedback(
            patient_profile=self.patient_profile, therapist_id=str(self.therapist.id), feedback_data=feedback_data
        )

        self.assertTrue(result["feedback_recorded"])
        self.assertTrue(result["preferences_updated"])
        self.assertIn("Decreased importance of location_proximity", result["improvement_summary"])


class MatchingAPITest(APITestCase):
    """Test matching API endpoints"""

    def setUp(self):
        self.patient = User.objects.create_user(
            email="patient@example.com", password="testpass123", first_name="John", last_name="Doe", user_type="patient"
        )

        self.patient_profile = PatientProfile.objects.create(
            user=self.patient,
            age_range="25-35",
            gender="male",
            location="Los Angeles, CA",
            session_format=["video"],
            primary_concerns=["anxiety"],
            therapy_types=["CBT"],
            profile_completed=True,
            matching_enabled=True,
        )

        self.therapist = User.objects.create_user(
            email="therapist@example.com",
            password="testpass123",
            first_name="Dr. Jane",
            last_name="Smith",
            user_type="therapist",
        )

        self.therapist_profile = TherapistProfile.objects.create(
            user=self.therapist,
            license_number="LIC123456",
            license_state="CA",
            years_experience=5,
            credentials=["LMFT"],
            specializations=["anxiety"],
            therapeutic_approaches=["CBT"],
            session_formats=["video"],
            base_rate="125",
            verification_status="approved",
            profile_completed=True,
            available_for_matching=True,
        )

        instance, self.token = AuthToken.objects.create(self.patient)

        self.matches_url = "/api/0/patients/matches/"
        self.feedback_url = "/api/0/patients/matches/feedback/"

    def test_get_matches_success(self):
        """Test getting matches successfully"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("matches", response.data["data"])
        self.assertIn("total_matches", response.data["data"])
        self.assertIn("generated_at", response.data["data"])

        matches = response.data["data"]["matches"]
        self.assertGreater(len(matches), 0)

        match = matches[0]
        self.assertIn("therapist_id", match)
        self.assertIn("compatibility_score", match)
        self.assertIn("match_reasons", match)
        self.assertIn("therapist_summary", match)

    def test_get_matches_incomplete_profile(self):
        """Test getting matches with incomplete profile"""
        # Mark profile as incomplete
        self.patient_profile.profile_completed = False
        self.patient_profile.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "INCOMPLETE_PROFILE")

    def test_get_matches_with_query_params(self):
        """Test getting matches with query parameters"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

        response = self.client.get(self.matches_url, {"limit": 5, "location_radius": 50, "refresh": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("aura.core.api.matching.cache")
    def test_get_matches_caching(self, mock_cache):
        """Test that matches are cached properly"""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_cache.set.assert_called_once()

    def test_submit_match_feedback_success(self):
        """Test submitting match feedback successfully"""
        feedback_data = {
            "therapist_id": str(self.therapist.id),
            "feedback_type": "positive",
            "feedback_details": {"liked_aspects": ["specialization_match"], "overall_rating": 4, "would_book": True},
            "preference_updates": {"increase_weight": ["therapeutic_approach"]},
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.post(self.feedback_url, feedback_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertTrue(response.data["data"]["feedback_recorded"])

    def test_submit_match_feedback_invalid_data(self):
        """Test submitting invalid match feedback"""
        invalid_data = {"therapist_id": "invalid-uuid", "feedback_type": "invalid_type"}

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        response = self.client.post(self.feedback_url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_get_matches_unauthenticated(self):
        """Test getting matches without authentication"""
        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_feedback_unauthenticated(self):
        """Test submitting feedback without authentication"""
        feedback_data = {"therapist_id": str(self.therapist.id), "feedback_type": "positive", "feedback_details": {}}

        response = self.client.post(self.feedback_url, feedback_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
