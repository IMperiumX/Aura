"""
Tests for PatientFlow serializers.

This module tests the serializers to ensure they work correctly with
the custom User model and provide proper validation and error handling.
"""

from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from aura.patientflow.models import (
    Appointment,
    Clinic,
    Notification,
    Patient,
    PatientFlowEvent,
    Status,
    UserProfile,
)
from aura.patientflow.serializers import (
    AppointmentCreateUpdateSerializer,
    AppointmentDetailSerializer,
    AppointmentListSerializer,
    ClinicSerializer,
    NotificationSerializer,
    PatientFlowPatientSerializer,
    PatientFlowUserSerializer,
    StatusSerializer,
    UserProfileSerializer,
)

User = get_user_model()


class PatientFlowUserSerializerTest(TestCase):
    """Test PatientFlowUserSerializer with custom User model."""

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "name": "Dr. John Smith",
            "password": "testpass123",
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_serializer_fields(self):
        """Test that serializer contains the correct fields."""
        serializer = PatientFlowUserSerializer(instance=self.user)
        data = serializer.data

        expected_fields = {"id", "name", "full_name", "email"}
        self.assertEqual(set(data.keys()), expected_fields)

    def test_full_name_with_name_field(self):
        """Test full_name method when name field is populated."""
        serializer = PatientFlowUserSerializer(instance=self.user)
        data = serializer.data

        self.assertEqual(data["full_name"], "Dr. John Smith")

    def test_full_name_fallback_to_email(self):
        """Test full_name falls back to email when name is empty."""
        self.user.name = ""
        self.user.save()

        serializer = PatientFlowUserSerializer(instance=self.user)
        data = serializer.data

        self.assertEqual(data["full_name"], "test@example.com")

    def test_read_only_fields(self):
        """Test that id field is read-only."""
        serializer = PatientFlowUserSerializer()
        self.assertIn("id", serializer.fields)
        self.assertTrue(serializer.fields["id"].read_only)


class AppointmentCreateUpdateSerializerTest(TestCase):
    """Test AppointmentCreateUpdateSerializer validation and creation."""

    def setUp(self):
        # Create test data
        self.clinic = Clinic.objects.create(name="Test Clinic", address="123 Test St")
        self.status = Status.objects.create(
            clinic=self.clinic, name="Waiting", color="#FF0000"
        )
        self.patient = Patient.objects.create(
            first_name="Jane", last_name="Doe", clinic=self.clinic
        )
        self.provider = User.objects.create_user(
            email="provider@example.com", name="Dr. Provider", password="testpass123"
        )

        # Create user profile for provider
        UserProfile.objects.create(
            user=self.provider, clinic=self.clinic, role="provider"
        )

        self.valid_data = {
            "patient": self.patient.id,
            "clinic": self.clinic.id,
            "scheduled_time": timezone.now() + timedelta(hours=1),
            "provider": self.provider.id,
            "status": self.status.id,
            "external_id": "EXT123",
        }

    def test_valid_appointment_creation(self):
        """Test creating a valid appointment."""
        serializer = AppointmentCreateUpdateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        appointment = serializer.save()
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.clinic, self.clinic)
        self.assertEqual(appointment.provider, self.provider)

    def test_patient_clinic_mismatch_validation(self):
        """Test validation fails when patient doesn't belong to clinic."""
        other_clinic = Clinic.objects.create(name="Other Clinic")
        other_patient = Patient.objects.create(
            first_name="John", last_name="Other", clinic=other_clinic
        )

        invalid_data = self.valid_data.copy()
        invalid_data["patient"] = other_patient.id

        serializer = AppointmentCreateUpdateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("patient", serializer.errors)

    def test_status_clinic_mismatch_validation(self):
        """Test validation fails when status doesn't belong to clinic."""
        other_clinic = Clinic.objects.create(name="Other Clinic")
        other_status = Status.objects.create(
            clinic=other_clinic, name="Other Status", color="#00FF00"
        )

        invalid_data = self.valid_data.copy()
        invalid_data["status"] = other_status.id

        serializer = AppointmentCreateUpdateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_past_scheduled_time_validation(self):
        """Test validation fails for appointments scheduled in the past."""
        invalid_data = self.valid_data.copy()
        invalid_data["scheduled_time"] = timezone.now() - timedelta(hours=1)

        serializer = AppointmentCreateUpdateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("scheduled_time", serializer.errors)

    def test_provider_scheduling_conflict_validation(self):
        """Test validation fails when provider has scheduling conflict."""
        # Create first appointment
        first_appointment = Appointment.objects.create(
            **{
                "patient": self.patient,
                "clinic": self.clinic,
                "scheduled_time": self.valid_data["scheduled_time"],
                "provider": self.provider,
                "status": self.status,
            }
        )

        # Try to create second appointment at same time
        serializer = AppointmentCreateUpdateSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("scheduled_time", serializer.errors)

    def test_appointment_creation_creates_flow_event(self):
        """Test that creating appointment automatically creates initial flow event."""
        serializer = AppointmentCreateUpdateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

        appointment = serializer.save()

        # Check that flow event was created
        flow_events = PatientFlowEvent.objects.filter(appointment=appointment)
        self.assertEqual(flow_events.count(), 1)

        flow_event = flow_events.first()
        self.assertEqual(flow_event.status, self.status)
        self.assertEqual(flow_event.notes, "Initial appointment creation")


class ClinicSerializerTest(TestCase):
    """Test ClinicSerializer computed fields and validation."""

    def setUp(self):
        self.clinic = Clinic.objects.create(name="Test Clinic", address="123 Test St")

        # Create some test data for computed fields
        self.patient = Patient.objects.create(
            first_name="Jane", last_name="Doe", clinic=self.clinic
        )

        self.provider = User.objects.create_user(
            email="provider@example.com", name="Dr. Provider", password="testpass123"
        )

        UserProfile.objects.create(
            user=self.provider, clinic=self.clinic, role="provider"
        )

    def test_computed_fields(self):
        """Test that computed fields return correct values."""
        # Create appointment for today
        today = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)
        Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=today,
            provider=self.provider,
        )

        serializer = ClinicSerializer(instance=self.clinic)
        data = serializer.data

        self.assertEqual(data["patient_count"], 1)
        self.assertEqual(data["active_appointments_count"], 1)
        self.assertEqual(data["staff_count"], 1)

    def test_name_validation(self):
        """Test clinic name validation."""
        # Test empty name
        invalid_data = {"name": "   ", "address": "Test Address"}
        serializer = ClinicSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_name_trimming(self):
        """Test that clinic name gets trimmed."""
        data = {"name": "  Test Clinic  ", "address": "Test Address"}
        serializer = ClinicSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        clinic = serializer.save()
        self.assertEqual(clinic.name, "Test Clinic")


class UserProfileSerializerTest(TestCase):
    """Test UserProfileSerializer validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", name="Test User", password="testpass123"
        )
        self.clinic = Clinic.objects.create(name="Test Clinic")

    def test_role_validation(self):
        """Test that role validation works correctly."""
        # Test valid role
        valid_data = {"clinic": self.clinic.id, "role": "provider"}
        serializer = UserProfileSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        # Test invalid role
        invalid_data = {"clinic": self.clinic.id, "role": "invalid_role"}
        serializer = UserProfileSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)


# Performance and integration tests
class SerializerPerformanceTest(TestCase):
    """Test serializer performance with larger datasets."""

    def setUp(self):
        self.clinic = Clinic.objects.create(name="Performance Test Clinic")

        # Create multiple patients, providers, and appointments
        self.patients = []
        self.providers = []

        for i in range(10):
            patient = Patient.objects.create(
                first_name=f"Patient{i}", last_name=f"Last{i}", clinic=self.clinic
            )
            self.patients.append(patient)

            provider = User.objects.create_user(
                email=f"provider{i}@example.com",
                name=f"Dr. Provider {i}",
                password="testpass123",
            )
            self.providers.append(provider)

    def test_appointment_list_serializer_performance(self):
        """Test that AppointmentListSerializer performs reasonably with multiple appointments."""
        # Create appointments
        appointments = []
        for i, (patient, provider) in enumerate(zip(self.patients, self.providers)):
            appointment = Appointment.objects.create(
                patient=patient,
                clinic=self.clinic,
                scheduled_time=timezone.now() + timedelta(hours=i),
                provider=provider,
            )
            appointments.append(appointment)

        # Serialize all appointments
        serializer = AppointmentListSerializer(appointments, many=True)
        data = serializer.data

        self.assertEqual(len(data), 10)
        # Ensure all required fields are present
        for appointment_data in data:
            required_fields = {
                "id",
                "patient_name",
                "patient_last_name",
                "clinic_name",
                "provider_name",
                "scheduled_time",
            }
            self.assertTrue(required_fields.issubset(set(appointment_data.keys())))


if __name__ == "__main__":
    pytest.main([__file__])

if __name__ == "__main__":
    pytest.main([__file__])
