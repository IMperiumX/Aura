"""
Comprehensive tests for user model factories.

This module tests all factories to ensure they:
1. Create valid model instances
2. Generate realistic test data
3. Handle relationships correctly
4. Provide consistent behavior
"""

from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase

from aura.mentalhealth.models import Disorder
from aura.users.models import Coach, Patient, Physician, Therapist, User
from aura.users.tests.factories import (
    CoachFactory,
    CoachUserFactory,
    ExperiencedTherapistFactory,
    HighRatedCoachFactory,
    PatientFactory,
    PatientUserFactory,
    PatientWithDisordersFactory,
    PhysicianFactory,
    PhysicianUserFactory,
    SpecialistPhysicianFactory,
    TherapistFactory,
    TherapistUserFactory,
    UserFactory,
)


class UserFactoryTestCase(TestCase):
    """Test cases for UserFactory."""

    def test_user_factory_creates_valid_user(self):
        """Test that UserFactory creates a valid User instance."""
        user = UserFactory()

        self.assertIsInstance(user, User)
        self.assertTrue(user.email)
        self.assertTrue(user.name)
        self.assertIsNotNone(user.last_password_change)
        self.assertIsNotNone(user.last_active)
        self.assertIsNotNone(user.date_joined)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_user_factory_generates_unique_emails(self):
        """Test that UserFactory generates unique email addresses."""
        users = UserFactory.create_batch(5)
        emails = [user.email for user in users]

        self.assertEqual(len(emails), len(set(emails)))

    def test_user_factory_password_functionality(self):
        """Test that UserFactory properly handles password generation."""
        user = UserFactory()

        # Password should be set and hashed
        self.assertTrue(user.password)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))

        # Test custom password
        custom_user = UserFactory(password="custom_password123")
        self.assertTrue(custom_user.check_password("custom_password123"))


class PatientFactoryTestCase(TestCase):
    """Test cases for PatientFactory."""

    def test_patient_factory_creates_valid_patient(self):
        """Test that PatientFactory creates a valid Patient instance."""
        patient = PatientFactory()

        self.assertIsInstance(patient, Patient)
        self.assertIsInstance(patient.user, User)
        self.assertTrue(patient.medical_record_number.startswith("MRN"))
        self.assertIn(
            patient.insurance_provider,
            [
                "Blue Cross Blue Shield",
                "Aetna",
                "UnitedHealth",
                "Cigna",
                "Humana",
                "Kaiser Permanente",
                "Anthem",
            ],
        )
        self.assertTrue(patient.insurance_policy_number.startswith("POL-"))
        self.assertTrue(patient.emergency_contact_name)
        self.assertTrue(patient.emergency_contact_phone)
        self.assertIsNotNone(patient.weight)
        self.assertIsNotNone(patient.height)
        self.assertIn(patient.gender, ["m", "f"])

    def test_patient_factory_medical_history_structure(self):
        """Test that PatientFactory generates realistic medical history."""
        patient = PatientFactory()

        self.assertIsInstance(patient.medical_history, dict)
        self.assertIn("surgeries", patient.medical_history)
        self.assertIn("hospitalizations", patient.medical_history)
        self.assertIn("family_history", patient.medical_history)

        family_history = patient.medical_history["family_history"]
        self.assertIn("diabetes", family_history)
        self.assertIn("heart_disease", family_history)
        self.assertIn("cancer", family_history)
        self.assertIn("mental_health", family_history)

    def test_patient_factory_current_medications_structure(self):
        """Test that PatientFactory generates realistic medication data."""
        patient = PatientFactory()

        self.assertIsInstance(patient.current_medications, dict)
        self.assertIn("medications", patient.current_medications)
        self.assertIn("last_updated", patient.current_medications)

        medications = patient.current_medications["medications"]
        for medication in medications:
            self.assertIn("name", medication)
            self.assertIn("dosage", medication)
            self.assertIn("frequency", medication)

    def test_patient_factory_health_data_structure(self):
        """Test that PatientFactory generates realistic health data."""
        patient = PatientFactory()

        self.assertIsInstance(patient.health_data, dict)
        self.assertIn("vital_signs", patient.health_data)
        self.assertIn("lab_results", patient.health_data)

        vital_signs = patient.health_data["vital_signs"]
        self.assertIn("blood_pressure", vital_signs)
        self.assertIn("heart_rate", vital_signs)
        self.assertIn("temperature", vital_signs)
        self.assertIn("oxygen_saturation", vital_signs)

    def test_patient_factory_preferences_structure(self):
        """Test that PatientFactory generates realistic preferences."""
        patient = PatientFactory()

        self.assertIsInstance(patient.preferences, dict)
        self.assertIn("communication", patient.preferences)
        self.assertIn("appointments", patient.preferences)
        self.assertIn("accessibility", patient.preferences)

    def test_patient_factory_embedding_field(self):
        """Test that PatientFactory properly handles embedding field."""
        patient = PatientFactory()

        if hasattr(settings, "EMBEDDING_MODEL_DIMENSIONS"):
            expected_dimensions = settings.EMBEDDING_MODEL_DIMENSIONS
        else:
            expected_dimensions = 1024

        self.assertEqual(len(patient.embedding), expected_dimensions)
        for value in patient.embedding:
            self.assertIsInstance(value, float)
            self.assertTrue(-1.0 <= value <= 1.0)

    def test_patient_factory_disorders_relationship(self):
        """Test that PatientFactory handles disorders relationship."""
        patient = PatientFactory()

        # Should create some disorders (0-3)
        disorder_count = patient.disorders.count()
        self.assertTrue(0 <= disorder_count <= 3)


class PatientWithDisordersFactoryTestCase(TestCase):
    """Test cases for PatientWithDisordersFactory."""

    def test_patient_with_disorders_always_has_disorders(self):
        """Test that PatientWithDisordersFactory always creates disorders."""
        patient = PatientWithDisordersFactory()

        disorder_count = patient.disorders.count()
        self.assertTrue(1 <= disorder_count <= 3)

        for disorder in patient.disorders.all():
            self.assertIsInstance(disorder, Disorder)


class TherapistFactoryTestCase(TestCase):
    """Test cases for TherapistFactory."""

    def test_therapist_factory_creates_valid_therapist(self):
        """Test that TherapistFactory creates a valid Therapist instance."""
        therapist = TherapistFactory()

        self.assertIsInstance(therapist, Therapist)
        self.assertIsInstance(therapist.user, User)
        self.assertTrue(therapist.license_number.startswith("LIC-"))
        self.assertTrue(1 <= therapist.years_of_experience <= 35)
        self.assertIn(therapist.gender, ["m", "f"])

    def test_therapist_factory_availability_structure(self):
        """Test that TherapistFactory generates realistic availability."""
        therapist = TherapistFactory()

        self.assertIsInstance(therapist.availability, dict)
        self.assertIn("weekly_schedule", therapist.availability)
        self.assertIn("timezone", therapist.availability)
        self.assertIn("booking_buffer", therapist.availability)
        self.assertIn("session_duration", therapist.availability)
        self.assertIn("max_sessions_per_day", therapist.availability)

        schedule = therapist.availability["weekly_schedule"]
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            self.assertIn(day, schedule)
            day_schedule = schedule[day]
            self.assertIn("available", day_schedule)

    def test_therapist_factory_specialties(self):
        """Test that TherapistFactory handles specialties properly."""
        therapist = TherapistFactory()

        specialties = list(therapist.specialties.all())
        self.assertTrue(2 <= len(specialties) <= 5)

        for specialty in specialties:
            self.assertIsInstance(specialty.name, str)

    def test_experienced_therapist_factory(self):
        """Test ExperiencedTherapistFactory creates experienced therapists."""
        therapist = ExperiencedTherapistFactory()

        self.assertTrue(therapist.years_of_experience >= 10)


class CoachFactoryTestCase(TestCase):
    """Test cases for CoachFactory."""

    def test_coach_factory_creates_valid_coach(self):
        """Test that CoachFactory creates a valid Coach instance."""
        coach = CoachFactory()

        self.assertIsInstance(coach, Coach)
        self.assertIsInstance(coach.user, User)
        self.assertTrue(coach.certification)
        self.assertTrue(coach.areas_of_expertise)
        self.assertTrue(coach.coaching_philosophy)
        self.assertTrue(coach.specialization)
        self.assertIsInstance(coach.rating, Decimal)
        self.assertTrue(Decimal("3.00") <= coach.rating <= Decimal("5.00"))
        self.assertIsNotNone(coach.weight)
        self.assertIsNotNone(coach.height)

    def test_coach_factory_availability_structure(self):
        """Test that CoachFactory generates realistic availability."""
        coach = CoachFactory()

        self.assertIsInstance(coach.availability, dict)
        self.assertIn("weekly_schedule", coach.availability)
        self.assertIn("session_types", coach.availability)
        self.assertIn("booking_advance_days", coach.availability)
        self.assertIn("cancellation_policy", coach.availability)

    def test_high_rated_coach_factory(self):
        """Test HighRatedCoachFactory creates high-rated coaches."""
        coach = HighRatedCoachFactory()

        self.assertTrue(coach.rating >= Decimal("4.70"))
        self.assertTrue(coach.years_of_experience >= 5)


class PhysicianFactoryTestCase(TestCase):
    """Test cases for PhysicianFactory."""

    def test_physician_factory_creates_valid_physician(self):
        """Test that PhysicianFactory creates a valid Physician instance."""
        physician = PhysicianFactory()

        self.assertIsInstance(physician, Physician)
        self.assertIsInstance(physician.user, User)
        self.assertTrue(physician.license_number.startswith("MD-"))
        self.assertTrue(3 <= physician.years_of_experience <= 40)
        self.assertTrue(physician.specialties)

    def test_physician_factory_availability_structure(self):
        """Test that PhysicianFactory generates realistic availability."""
        physician = PhysicianFactory()

        self.assertIsInstance(physician.availability, dict)
        self.assertIn("weekly_schedule", physician.availability)
        self.assertIn("emergency_on_call", physician.availability)
        self.assertIn("hospital_rounds", physician.availability)
        self.assertIn("consultation_types", physician.availability)

    def test_specialist_physician_factory(self):
        """Test SpecialistPhysicianFactory creates specialist physicians."""
        physician = SpecialistPhysicianFactory()

        self.assertTrue(physician.years_of_experience >= 8)
        self.assertIn(
            physician.specialties,
            [
                "Cardiology",
                "Endocrinology",
                "Neurology",
                "Oncology",
                "Psychiatry",
                "Orthopedics",
                "Surgery",
            ],
        )


class UserTypeFactoriesTestCase(TestCase):
    """Test cases for user type factories that create User + Profile."""

    def test_patient_user_factory(self):
        """Test PatientUserFactory creates User with Patient profile."""
        user = PatientUserFactory()

        self.assertIsInstance(user, User)
        self.assertTrue(hasattr(user, "patient_profile"))
        self.assertIsInstance(user.patient_profile.first(), Patient)

    def test_therapist_user_factory(self):
        """Test TherapistUserFactory creates User with Therapist profile."""
        user = TherapistUserFactory()

        self.assertIsInstance(user, User)
        self.assertTrue(hasattr(user, "therapist_profile"))
        self.assertIsInstance(user.therapist_profile.first(), Therapist)

    def test_coach_user_factory(self):
        """Test CoachUserFactory creates User with Coach profile."""
        user = CoachUserFactory()

        self.assertIsInstance(user, User)
        self.assertTrue(hasattr(user, "coach_profile"))
        self.assertIsInstance(user.coach_profile.first(), Coach)

    def test_physician_user_factory(self):
        """Test PhysicianUserFactory creates User with Physician profile."""
        user = PhysicianUserFactory()

        self.assertIsInstance(user, User)
        self.assertTrue(hasattr(user, "physician_profile"))
        self.assertIsInstance(user.physician_profile.first(), Physician)


class FactoryPerformanceTestCase(TestCase):
    """Test cases to ensure factories perform well in batch operations."""

    def test_batch_creation_performance(self):
        """Test that factories work efficiently in batch operations."""
        # Test batch creation doesn't raise errors
        users = UserFactory.create_batch(10)
        self.assertEqual(len(users), 10)

        patients = PatientFactory.create_batch(5)
        self.assertEqual(len(patients), 5)

        therapists = TherapistFactory.create_batch(5)
        self.assertEqual(len(therapists), 5)

        coaches = CoachFactory.create_batch(3)
        self.assertEqual(len(coaches), 3)

        physicians = PhysicianFactory.create_batch(3)
        self.assertEqual(len(physicians), 3)

    def test_build_vs_create(self):
        """Test that factories work with both build and create."""
        # Build without saving to database
        built_patient = PatientFactory.build()
        self.assertIsInstance(built_patient, Patient)
        self.assertIsNone(built_patient.pk)

        # Create and save to database
        created_patient = PatientFactory.create()
        self.assertIsInstance(created_patient, Patient)
        self.assertIsNotNone(created_patient.pk)


class FactoryCustomizationTestCase(TestCase):
    """Test cases for factory customization capabilities."""

    def test_factory_with_custom_attributes(self):
        """Test that factories accept custom attributes."""
        custom_email = "test@example.com"
        user = UserFactory(email=custom_email)
        self.assertEqual(user.email, custom_email)

        custom_weight = 75.5
        patient = PatientFactory(weight=custom_weight)
        self.assertEqual(patient.weight, custom_weight)

    def test_factory_with_custom_relationships(self):
        """Test that factories handle custom relationships."""
        user = UserFactory()
        patient = PatientFactory(user=user)
        self.assertEqual(patient.user, user)

    def test_factory_with_custom_many_to_many(self):
        """Test that factories handle custom many-to-many relationships."""
        from aura.mentalhealth.tests.factories import DisorderFactory

        disorders = DisorderFactory.create_batch(2)
        patient = PatientFactory(disorders=disorders)

        self.assertEqual(patient.disorders.count(), 2)
        for disorder in disorders:
            self.assertIn(disorder, patient.disorders.all())


@pytest.mark.django_db
class FactoryIntegrationTestCase(TestCase):
    """Integration tests to ensure factories work with Django ORM and constraints."""

    def test_factories_respect_unique_constraints(self):
        """Test that factories respect unique database constraints."""
        # Email should be unique
        user1 = UserFactory()
        user2 = UserFactory()
        self.assertNotEqual(user1.email, user2.email)

        # Medical record numbers should be unique
        patient1 = PatientFactory()
        patient2 = PatientFactory()
        self.assertNotEqual(
            patient1.medical_record_number, patient2.medical_record_number
        )

    def test_factories_work_with_django_signals(self):
        """Test that factories work properly with Django model signals."""
        # The AbstractProfile model has a post-save signal to add users to groups
        patient = PatientFactory()
        therapist = TherapistFactory()
        coach = CoachFactory()

        # Verify the instances were created successfully
        self.assertIsInstance(patient, Patient)
        self.assertIsInstance(therapist, Therapist)
        self.assertIsInstance(coach, Coach)

    def test_factories_work_with_lifecycle_hooks(self):
        """Test that factories work with django-lifecycle hooks."""
        # The models use lifecycle hooks for certain operations
        patient = PatientFactory()

        # Verify the patient was created and saved properly
        self.assertIsNotNone(patient.pk)
        self.assertIsNotNone(patient.created)
        self.assertIsNotNone(patient.updated)
