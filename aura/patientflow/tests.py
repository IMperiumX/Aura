from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from .models import Appointment
from .models import Clinic
from .models import Notification
from .models import Patient
from .models import PatientFlowEvent
from .models import Status
from .models import UserProfile
from .signals import should_send_email
from .signals import should_send_sms

User = get_user_model()


class PatientFlowModelTests(TestCase):
    """Test cases for Patient Flow models."""

    def setUp(self):
        """Set up test data."""
        self.clinic = Clinic.objects.create(
            name="Test Clinic",
            address="123 Test St",
        )

        self.status = Status.objects.create(
            name="Checked In",
            clinic=self.clinic,
            color="#28a745",
            order=1,
        )

        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            dob=datetime(1990, 1, 1).date(),
            clinic=self.clinic,
        )

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        self.user_profile = UserProfile.objects.create(
            user=self.user,
            clinic=self.clinic,
            role="nurse",
        )

        self.appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            provider=self.user,
        )

    def test_clinic_creation(self):
        """Test clinic model creation."""
        self.assertEqual(self.clinic.name, "Test Clinic")
        self.assertTrue(self.clinic.is_active)
        self.assertIsNotNone(self.clinic.created_at)

    def test_status_ordering(self):
        """Test status ordering functionality."""
        status2 = Status.objects.create(
            name="With Provider",
            clinic=self.clinic,
            color="#17a2b8",
            order=2,
        )

        statuses = Status.objects.filter(clinic=self.clinic).order_by("order")
        self.assertEqual(list(statuses), [self.status, status2])

    def test_patient_full_name(self):
        """Test patient full name property."""
        full_name = f"{self.patient.first_name} {self.patient.last_name}"
        self.assertEqual(full_name, "John Doe")

    def test_appointment_flow_event_creation(self):
        """Test flow event creation when appointment status changes."""
        # Update appointment status
        self.appointment.status = self.status
        self.appointment.save()

        # Check if flow event was created
        flow_events = PatientFlowEvent.objects.filter(appointment=self.appointment)
        self.assertEqual(flow_events.count(), 1)

        flow_event = flow_events.first()
        self.assertEqual(flow_event.status, self.status)
        self.assertEqual(flow_event.appointment, self.appointment)

    def test_user_profile_creation_signal(self):
        """Test automatic user profile creation."""
        new_user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="newpass123",
        )

        # Check if profile was created
        self.assertTrue(hasattr(new_user, "profile"))
        self.assertIsNotNone(new_user.profile)

    def test_notification_generation(self):
        """Test notification generation on status change."""
        # Create a flow event
        flow_event = PatientFlowEvent.objects.create(
            appointment=self.appointment,
            status=self.status,
            updated_by=self.user,
        )

        # Check if notifications were generated
        notifications = Notification.objects.filter(event=flow_event)
        self.assertGreater(notifications.count(), 0)


class PatientFlowAPITests(APITestCase):
    """Test cases for Patient Flow API endpoints."""

    def setUp(self):
        """Set up test data for API tests."""
        self.client = APIClient()

        # Create test clinic
        self.clinic = Clinic.objects.create(
            name="API Test Clinic",
            address="456 API St",
        )

        # Create test user with profile
        self.user = User.objects.create_user(
            username="apiuser",
            email="api@example.com",
            password="apipass123",
        )

        self.user_profile = UserProfile.objects.create(
            user=self.user,
            clinic=self.clinic,
            role="front_desk",
        )

        # Create test status
        self.status = Status.objects.create(
            name="Waiting",
            clinic=self.clinic,
            color="#ffc107",
            order=1,
        )

        # Create test patient
        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            dob=datetime(1985, 5, 15).date(),
            clinic=self.clinic,
        )

        # Authenticate client
        self.client.force_authenticate(user=self.user)

    def test_clinic_list_api(self):
        """Test clinic list API endpoint."""
        url = "/patientflow/api/v1/clinics/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "API Test Clinic")

    def test_status_list_api(self):
        """Test status list API endpoint."""
        url = "/patientflow/api/v1/statuses/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Waiting")

    def test_patient_creation_api(self):
        """Test patient creation via API."""
        url = "/patientflow/api/v1/patients/"
        data = {
            "first_name": "Bob",
            "last_name": "Johnson",
            "dob": "1992-03-20",
            "clinic": self.clinic.id,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], "Bob")

        # Verify patient was created in database
        patient = Patient.objects.get(id=response.data["id"])
        self.assertEqual(patient.first_name, "Bob")
        self.assertEqual(patient.clinic, self.clinic)

    def test_appointment_creation_api(self):
        """Test appointment creation via API."""
        url = "/patientflow/api/v1/appointments/"
        data = {
            "patient": self.patient.id,
            "clinic": self.clinic.id,
            "scheduled_time": timezone.now().isoformat(),
            "provider": self.user.id,
            "status": self.status.id,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify appointment was created
        appointment = Appointment.objects.get(id=response.data["id"])
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.clinic, self.clinic)

    def test_appointment_status_update_api(self):
        """Test appointment status update via API."""
        # Create appointment
        appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            provider=self.user,
            status=self.status,
        )

        # Create new status
        new_status = Status.objects.create(
            name="In Progress",
            clinic=self.clinic,
            color="#007bff",
            order=2,
        )

        url = f"/patientflow/api/v1/appointments/{appointment.id}/update_status/"
        data = {
            "status_id": new_status.id,
            "notes": "Moving to next stage",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify status was updated
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, new_status)

        # Verify flow event was created
        flow_event = PatientFlowEvent.objects.filter(
            appointment=appointment,
            status=new_status,
        ).first()
        self.assertIsNotNone(flow_event)
        self.assertEqual(flow_event.notes, "Moving to next stage")

    def test_flow_board_api(self):
        """Test flow board API endpoint."""
        # Create appointment with status
        appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            provider=self.user,
            status=self.status,
        )

        url = "/patientflow/api/v1/flow-board/current/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("clinic", response.data)
        self.assertIn("statuses", response.data)
        self.assertIn("appointments_by_status", response.data)
        self.assertIn("summary", response.data)

    def test_notification_api(self):
        """Test notification API endpoints."""
        # Create notification
        appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            provider=self.user,
            status=self.status,
        )

        flow_event = PatientFlowEvent.objects.create(
            appointment=appointment,
            status=self.status,
            updated_by=self.user,
        )

        notification = Notification.objects.create(
            recipient=self.user,
            event=flow_event,
            message="Test notification",
        )

        # Test list notifications
        url = "/patientflow/api/v1/notifications/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Test mark as read
        url = f"/patientflow/api/v1/notifications/{notification.id}/mark_read/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_analytics_api(self):
        """Test analytics API endpoints."""
        # Create some test data
        appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            provider=self.user,
            status=self.status,
        )

        url = "/patientflow/api/v1/analytics/daily_report/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_appointments", response.data)
        self.assertIn("completed_appointments", response.data)
        self.assertIn("completion_rate", response.data)


class PatientFlowPermissionTests(APITestCase):
    """Test cases for Patient Flow permissions."""

    def setUp(self):
        """Set up test data for permission tests."""
        self.client = APIClient()

        # Create two clinics
        self.clinic1 = Clinic.objects.create(name="Clinic 1")
        self.clinic2 = Clinic.objects.create(name="Clinic 2")

        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            clinic=self.clinic1,
            role="admin",
        )

        self.nurse_user = User.objects.create_user(
            username="nurse",
            email="nurse@test.com",
            password="pass",
        )
        UserProfile.objects.create(
            user=self.nurse_user,
            clinic=self.clinic1,
            role="nurse",
        )

        self.other_clinic_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="pass",
        )
        UserProfile.objects.create(
            user=self.other_clinic_user,
            clinic=self.clinic2,
            role="nurse",
        )

        # Create patient in clinic1
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            clinic=self.clinic1,
        )

    def test_admin_access(self):
        """Test admin user access."""
        self.client.force_authenticate(user=self.admin_user)

        # Admin should see all patients
        url = "/patientflow/api/v1/patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_clinic_isolation(self):
        """Test that users can only see data from their clinic."""
        self.client.force_authenticate(user=self.other_clinic_user)

        # Should not see patient from clinic1
        url = "/patientflow/api/v1/patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_unauthenticated_access(self):
        """Test unauthenticated access is denied."""
        url = "/patientflow/api/v1/patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PatientFlowSignalTests(TestCase):
    """Test cases for Patient Flow signals and business logic."""

    def setUp(self):
        """Set up test data."""
        self.clinic = Clinic.objects.create(name="Signal Test Clinic")
        self.user = User.objects.create_user(
            username="signaluser",
            email="signal@test.com",
            password="pass",
        )
        UserProfile.objects.create(
            user=self.user,
            clinic=self.clinic,
            role="provider",
        )

        self.status = Status.objects.create(
            name="Emergency",
            clinic=self.clinic,
            color="#dc3545",
            order=1,
        )

        self.patient = Patient.objects.create(
            first_name="Signal",
            last_name="Test",
            clinic=self.clinic,
        )

        self.appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            provider=self.user,
        )

    def test_email_notification_rules(self):
        """Test email notification business rules."""
        flow_event = PatientFlowEvent.objects.create(
            appointment=self.appointment,
            status=self.status,
            updated_by=self.user,
        )

        # Emergency status should trigger email
        self.assertTrue(should_send_email(self.user, flow_event))

    def test_sms_notification_rules(self):
        """Test SMS notification business rules."""
        flow_event = PatientFlowEvent.objects.create(
            appointment=self.appointment,
            status=self.status,
            updated_by=self.user,
        )

        # Emergency status should trigger SMS
        self.assertTrue(should_send_sms(self.user, flow_event))

    @patch("aura.patientflow.tasks.send_notification_email.delay")
    @patch("aura.patientflow.tasks.send_notification_sms.delay")
    def test_notification_generation(self, mock_sms, mock_email):
        """Test notification generation and task scheduling."""
        flow_event = PatientFlowEvent.objects.create(
            appointment=self.appointment,
            status=self.status,
            updated_by=self.user,
        )

        # Should create notifications
        notifications = Notification.objects.filter(event=flow_event)
        self.assertGreater(notifications.count(), 0)

        # Should schedule email/SMS tasks for emergency status
        self.assertTrue(mock_email.called or mock_sms.called)


class PatientFlowFilterTests(APITestCase):
    """Test cases for Patient Flow API filters."""

    def setUp(self):
        """Set up test data for filter tests."""
        self.client = APIClient()

        self.clinic = Clinic.objects.create(name="Filter Test Clinic")
        self.user = User.objects.create_user(
            username="filteruser",
            email="filter@test.com",
            password="pass",
        )
        UserProfile.objects.create(
            user=self.user,
            clinic=self.clinic,
            role="nurse",
        )

        self.status1 = Status.objects.create(
            name="Waiting",
            clinic=self.clinic,
            color="#ffc107",
            order=1,
        )
        self.status2 = Status.objects.create(
            name="Complete",
            clinic=self.clinic,
            color="#28a745",
            order=2,
        )

        self.patient = Patient.objects.create(
            first_name="Filter",
            last_name="Test",
            clinic=self.clinic,
        )

        # Create appointments for today and yesterday
        self.today_appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=timezone.now(),
            status=self.status1,
        )

        yesterday = timezone.now() - timedelta(days=1)
        self.yesterday_appointment = Appointment.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            scheduled_time=yesterday,
            status=self.status2,
        )

        self.client.force_authenticate(user=self.user)

    def test_appointment_today_filter(self):
        """Test filtering appointments for today."""
        url = "/patientflow/api/v1/appointments/?today=true"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.today_appointment.id)

    def test_appointment_status_filter(self):
        """Test filtering appointments by status."""
        url = f"/patientflow/api/v1/appointments/?status={self.status1.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], self.status1.id)

    def test_patient_name_search(self):
        """Test searching patients by name."""
        url = "/patientflow/api/v1/patients/?search=Filter"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["first_name"], "Filter")


if __name__ == "__main__":
    pytest.main([__file__])
