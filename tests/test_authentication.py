"""
Comprehensive tests for authentication system
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserModelTest(TestCase):
    """Test the User model"""

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "user_type": "patient",
            "terms_accepted": True,
            "privacy_policy_accepted": True,
        }

    def test_create_user(self):
        """Test creating a user"""
        user = User.objects.create_user(**self.user_data)

        self.assertEqual(user.email, self.user_data["email"])
        self.assertEqual(user.first_name, self.user_data["first_name"])
        self.assertEqual(user.last_name, self.user_data["last_name"])
        self.assertEqual(user.user_type, self.user_data["user_type"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertTrue(user.terms_accepted)
        self.assertTrue(user.privacy_policy_accepted)
        self.assertFalse(user.is_verified)

    def test_create_therapist_user(self):
        """Test creating a therapist user"""
        therapist_data = self.user_data.copy()
        therapist_data["user_type"] = "therapist"

        user = User.objects.create_user(**therapist_data)
        self.assertEqual(user.user_type, "therapist")

    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), user.email)

    def test_profile_completed_property_patient(self):
        """Test profile_completed property for patient"""
        user = User.objects.create_user(**self.user_data)
        self.assertFalse(user.profile_completed)

        # Would be True after creating patient profile
        # This would require importing PatientProfile and creating one

    def test_profile_completed_property_therapist(self):
        """Test profile_completed property for therapist"""
        therapist_data = self.user_data.copy()
        therapist_data["user_type"] = "therapist"

        user = User.objects.create_user(**therapist_data)
        self.assertFalse(user.profile_completed)


class AuthenticationAPITest(APITestCase):
    """Test authentication API endpoints"""

    def setUp(self):
        self.register_url = "/api/0/auth/register/"
        self.login_url = "/api/0/auth/login/"
        self.logout_url = "/api/0/auth/logout/"
        self.profile_url = "/api/0/auth/profile/"

        self.user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "user_type": "patient",
            "terms_accepted": True,
            "privacy_policy_accepted": True,
        }

    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(self.register_url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertIn("user_id", response.data["data"])
        self.assertIn("email", response.data["data"])
        self.assertEqual(response.data["data"]["email"], self.user_data["email"])
        self.assertEqual(response.data["data"]["user_type"], self.user_data["user_type"])
        self.assertTrue(response.data["data"]["verification_required"])

        # Check user was created
        self.assertTrue(User.objects.filter(email=self.user_data["email"]).exists())

    def test_user_registration_invalid_password(self):
        """Test registration with invalid password"""
        invalid_data = self.user_data.copy()
        invalid_data["password"] = "123"  # Too short
        invalid_data["password_confirm"] = "123"

        response = self.client.post(self.register_url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch"""
        invalid_data = self.user_data.copy()
        invalid_data["password_confirm"] = "DifferentPassword123!"

        response = self.client.post(self.register_url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_user_registration_terms_not_accepted(self):
        """Test registration without accepting terms"""
        invalid_data = self.user_data.copy()
        invalid_data["terms_accepted"] = False

        response = self.client.post(self.register_url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_user_login_success(self):
        """Test successful user login"""
        # Create user first
        user = User.objects.create_user(
            email=self.user_data["email"],
            password=self.user_data["password"],
            first_name=self.user_data["first_name"],
            last_name=self.user_data["last_name"],
            user_type=self.user_data["user_type"],
            terms_accepted=True,
            privacy_policy_accepted=True,
        )

        login_data = {"email": self.user_data["email"], "password": self.user_data["password"]}

        response = self.client.post(self.login_url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("token", response.data["data"])
        self.assertIn("user", response.data["data"])
        self.assertIn("expires", response.data["data"])

        # Check token was created
        self.assertTrue(AuthToken.objects.filter(user=user).exists())

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        response = self.client.post(self.login_url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_user_logout_success(self):
        """Test successful user logout"""
        # Create user and login first
        user = User.objects.create_user(
            email=self.user_data["email"],
            password=self.user_data["password"],
            first_name=self.user_data["first_name"],
            last_name=self.user_data["last_name"],
            user_type=self.user_data["user_type"],
            terms_accepted=True,
            privacy_policy_accepted=True,
        )

        instance, token = AuthToken.objects.create(user)

        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("message", response.data["data"])

    def test_get_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        user = User.objects.create_user(
            email=self.user_data["email"],
            password=self.user_data["password"],
            first_name=self.user_data["first_name"],
            last_name=self.user_data["last_name"],
            user_type=self.user_data["user_type"],
            terms_accepted=True,
            privacy_policy_accepted=True,
        )

        instance, token = AuthToken.objects.create(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["email"], user.email)
        self.assertEqual(response.data["data"]["user_type"], user.user_type)

    def test_get_profile_unauthenticated(self):
        """Test getting user profile when not authenticated"""
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestUserManagerMethods:
    """Test User manager methods"""

    def test_create_user(self):
        """Test create_user method"""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.check_password("testpass123")
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Test create_superuser method"""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )

        assert user.email == "admin@example.com"
        assert user.is_staff
        assert user.is_superuser

    def test_create_user_without_email_raises_error(self):
        """Test that creating user without email raises error"""
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="testpass123")
