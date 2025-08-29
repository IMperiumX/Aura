import random
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import factory
from django.conf import settings
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker()


class UserFactory(DjangoModelFactory):
    """Factory for User model with comprehensive field coverage."""

    email = factory.Faker("email")
    name = factory.Faker("name")
    last_password_change = factory.Faker(
        "date_time_this_month",
        tzinfo=timezone.get_current_timezone(),
    )
    last_active = factory.Faker(
        "date_time_between",
        start_date="-30d",
        end_date="now",
        tzinfo=timezone.get_current_timezone(),
    )
    is_password_expired = factory.Faker("boolean", chance_of_getting_true=10)
    date_joined = factory.Faker(
        "date_time_between",
        start_date="-2y",
        end_date="now",
        tzinfo=timezone.get_current_timezone(),
    )
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(
        self,
        create,
        extracted: Sequence[Any],
        **kwargs,
    ):
        password = (
            extracted
            if extracted
            else factory.Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = "users.User"
        django_get_or_create = ["email"]


class AbstractProfileFactoryMixin:
    """Mixin for common AbstractProfile fields."""

    avatar_url = factory.Faker("image_url")
    bio = factory.Faker("paragraph", nb_sentences=3)
    date_of_birth = factory.Faker("date_of_birth", minimum_age=18, maximum_age=80)
    gender = factory.Faker("random_element", elements=["m", "f"])

    @factory.lazy_attribute
    def embedding(self):
        """Generate a realistic embedding vector."""
        if hasattr(settings, "EMBEDDING_MODEL_DIMENSIONS"):
            dimensions = settings.EMBEDDING_MODEL_DIMENSIONS
        else:
            dimensions = 1024  # fallback default
        return [random.uniform(-1.0, 1.0) for _ in range(dimensions)]

    user = factory.SubFactory(UserFactory)


class PatientFactory(AbstractProfileFactoryMixin, DjangoModelFactory):
    """Comprehensive factory for Patient model."""

    # Medical information
    medical_record_number = factory.Sequence(lambda n: f"MRN{n:06d}")
    insurance_provider = factory.Faker(
        "random_element",
        elements=[
            "Blue Cross Blue Shield",
            "Aetna",
            "UnitedHealth",
            "Cigna",
            "Humana",
            "Kaiser Permanente",
            "Anthem",
        ],
    )
    insurance_policy_number = factory.Faker("bothify", text="POL-####-????-###")

    # Emergency contact
    emergency_contact_name = factory.Faker("name")
    emergency_contact_phone = factory.Faker("phone_number")

    # Medical conditions
    allergies = factory.Faker(
        "random_element",
        elements=[
            "Penicillin, Shellfish",
            "Peanuts, Tree nuts",
            "Latex, Iodine",
            "No known allergies",
            "Sulfa drugs, Aspirin",
            "Dust mites, Pollen",
        ],
    )
    medical_conditions = factory.Faker(
        "random_element",
        elements=[
            "Hypertension, Type 2 Diabetes",
            "Asthma, Seasonal allergies",
            "Depression, Anxiety disorder",
            "Migraine headaches",
            "No significant medical history",
            "Hypothyroidism, High cholesterol",
        ],
    )

    # Physical measurements
    weight = factory.Faker("random_int", min=45, max=150)  # kg
    height = factory.Faker("random_int", min=150, max=200)  # cm

    @factory.lazy_attribute
    def medical_history(self):
        """Generate realistic medical history JSON."""
        return {
            "surgeries": [
                {
                    "procedure": fake.random_element(
                        elements=[
                            "Appendectomy",
                            "Cholecystectomy",
                            "Tonsillectomy",
                            "Arthroscopic knee surgery",
                            "Cesarean section",
                        ],
                    ),
                    "date": fake.date_between(
                        start_date="-10y",
                        end_date="today",
                    ).isoformat(),
                    "hospital": fake.company() + " Hospital",
                }
                for _ in range(fake.random_int(min=0, max=3))
            ],
            "hospitalizations": [
                {
                    "reason": fake.random_element(
                        elements=[
                            "Pneumonia",
                            "Chest pain evaluation",
                            "Diabetic ketoacidosis",
                            "Stroke",
                            "Heart attack",
                            "Broken bone",
                        ],
                    ),
                    "date": fake.date_between(
                        start_date="-5y",
                        end_date="today",
                    ).isoformat(),
                    "duration_days": fake.random_int(min=1, max=14),
                }
                for _ in range(fake.random_int(min=0, max=2))
            ],
            "family_history": {
                "diabetes": fake.boolean(),
                "heart_disease": fake.boolean(),
                "cancer": fake.boolean(),
                "mental_health": fake.boolean(),
            },
        }

    @factory.lazy_attribute
    def current_medications(self):
        """Generate realistic current medications JSON."""
        medications = [
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "Once daily"},
            {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily"},
            {"name": "Sertraline", "dosage": "50mg", "frequency": "Once daily"},
            {"name": "Atorvastatin", "dosage": "20mg", "frequency": "Once daily"},
            {"name": "Levothyroxine", "dosage": "75mcg", "frequency": "Once daily"},
            {"name": "Omeprazole", "dosage": "20mg", "frequency": "Once daily"},
        ]

        selected_meds = fake.random_elements(
            elements=medications,
            length=fake.random_int(min=0, max=4),
            unique=True,
        )

        return {
            "medications": list(selected_meds),
            "last_updated": timezone.now().isoformat(),
        }

    @factory.lazy_attribute
    def health_data(self):
        """Generate realistic health data JSON."""
        return {
            "vital_signs": {
                "blood_pressure": {
                    "systolic": fake.random_int(min=110, max=140),
                    "diastolic": fake.random_int(min=70, max=90),
                    "last_reading": fake.date_between(
                        start_date="-30d",
                        end_date="today",
                    ).isoformat(),
                },
                "heart_rate": fake.random_int(min=60, max=100),
                "temperature": round(fake.random_int(min=970, max=990) / 10, 1),
                "oxygen_saturation": fake.random_int(min=95, max=100),
            },
            "lab_results": {
                "cholesterol": {
                    "total": fake.random_int(min=150, max=250),
                    "ldl": fake.random_int(min=70, max=160),
                    "hdl": fake.random_int(min=35, max=80),
                    "date": fake.date_between(
                        start_date="-6m",
                        end_date="today",
                    ).isoformat(),
                },
                "blood_sugar": {
                    "fasting": fake.random_int(min=80, max=130),
                    "hba1c": round(fake.random_int(min=50, max=80) / 10, 1),
                    "date": fake.date_between(
                        start_date="-3m",
                        end_date="today",
                    ).isoformat(),
                },
            },
        }

    @factory.lazy_attribute
    def preferences(self):
        """Generate realistic patient preferences JSON."""
        return {
            "communication": {
                "preferred_method": fake.random_element(
                    elements=["email", "phone", "text", "portal"],
                ),
                "language": fake.random_element(elements=["en", "es", "fr", "ar"]),
                "best_time_to_contact": fake.random_element(
                    elements=["morning", "afternoon", "evening"],
                ),
            },
            "appointments": {
                "preferred_day": fake.random_element(
                    elements=["monday", "tuesday", "wednesday", "thursday", "friday"],
                ),
                "preferred_time": fake.random_element(
                    elements=["morning", "afternoon", "evening"],
                ),
                "reminder_preference": fake.random_element(
                    elements=["24h", "2h", "1h", "none"],
                ),
            },
            "accessibility": {
                "mobility_assistance": fake.boolean(chance_of_getting_true=10),
                "hearing_assistance": fake.boolean(chance_of_getting_true=5),
                "visual_assistance": fake.boolean(chance_of_getting_true=5),
                "interpreter_needed": fake.boolean(chance_of_getting_true=15),
            },
        }

    @factory.post_generation
    def disorders(self, create, extracted, **kwargs):
        """Handle ManyToMany relationship for disorders."""
        if not create:
            return

        if extracted:
            for disorder in extracted:
                self.disorders.add(disorder)
        else:
            # Add 0-3 random disorders
            from aura.mentalhealth.tests.factories import DisorderFactory

            disorder_count = fake.random_int(min=0, max=3)
            for _ in range(disorder_count):
                disorder = DisorderFactory()
                self.disorders.add(disorder)

    class Meta:
        model = "users.Patient"


class TherapistFactory(AbstractProfileFactoryMixin, DjangoModelFactory):
    """Comprehensive factory for Therapist model."""

    license_number = factory.Sequence(lambda n: f"LIC-{n:05d}")
    years_of_experience = factory.Faker("random_int", min=1, max=35)

    @factory.lazy_attribute
    def availability(self):
        """Generate realistic availability schedule JSON."""
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        schedule = {}

        for day in days:
            # 70% chance therapist works on any given day
            if fake.boolean(chance_of_getting_true=70):
                start_hour = fake.random_int(min=8, max=10)
                end_hour = fake.random_int(min=16, max=18)
                schedule[day] = {
                    "available": True,
                    "start_time": f"{start_hour:02d}:00",
                    "end_time": f"{end_hour:02d}:00",
                    "break_time": {"start": "12:00", "end": "13:00"},
                }
            else:
                schedule[day] = {"available": False}

        return {
            "weekly_schedule": schedule,
            "timezone": "UTC",
            "booking_buffer": 24,  # hours in advance
            "session_duration": 50,  # minutes
            "max_sessions_per_day": fake.random_int(min=6, max=12),
        }

    @factory.post_generation
    def specialties(self, create, extracted, **kwargs):
        """Handle TaggableManager for specialties."""
        if not create:
            return

        if extracted:
            self.specialties.add(*extracted)
        else:
            # Add 2-5 random specialties
            therapy_specialties = [
                "Cognitive Behavioral Therapy",
                "Psychodynamic Therapy",
                "Dialectical Behavior Therapy",
                "EMDR",
                "Family Therapy",
                "Couples Therapy",
                "Trauma Therapy",
                "Anxiety Disorders",
                "Depression",
                "PTSD",
                "Eating Disorders",
                "Addiction",
                "Grief Counseling",
                "Child Psychology",
                "Adolescent Therapy",
            ]
            specialty_count = fake.random_int(min=2, max=5)
            selected_specialties = fake.random_elements(
                elements=therapy_specialties,
                length=specialty_count,
                unique=True,
            )
            self.specialties.add(*selected_specialties)

    class Meta:
        model = "users.Therapist"


class CoachFactory(AbstractProfileFactoryMixin, DjangoModelFactory):
    """Comprehensive factory for Coach model."""

    certification = factory.Faker(
        "random_element",
        elements=[
            "International Coach Federation (ICF)",
            "Certified Professional Coach (CPC)",
            "Associate Certified Coach (ACC)",
            "Professional Certified Coach (PCC)",
            "Master Certified Coach (MCC)",
            "Certified Life Coach",
            "Certified Executive Coach",
        ],
    )

    areas_of_expertise = factory.Faker(
        "random_element",
        elements=[
            "Life Coaching",
            "Executive Coaching",
            "Career Coaching",
            "Health Coaching",
            "Relationship Coaching",
            "Performance Coaching",
            "Leadership Coaching",
            "Business Coaching",
            "Wellness Coaching",
        ],
    )

    coaching_philosophy = factory.Faker("paragraph", nb_sentences=4)

    rating = factory.Faker(
        "pydecimal",
        left_digits=1,
        right_digits=2,
        min_value=Decimal("3.00"),
        max_value=Decimal("5.00"),
    )

    specialization = factory.Faker(
        "random_element",
        elements=[
            "Stress Management",
            "Work-Life Balance",
            "Goal Setting",
            "Confidence Building",
            "Communication Skills",
            "Time Management",
            "Leadership Development",
            "Career Transition",
            "Personal Growth",
        ],
    )

    weight = factory.Faker("random_int", min=50, max=120)  # kg
    height = factory.Faker("random_int", min=155, max=195)  # cm

    @factory.lazy_attribute
    def availability(self):
        """Generate realistic coach availability schedule JSON."""
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        schedule = {}

        for day in days:
            # 80% chance coach works on any given day
            if fake.boolean(chance_of_getting_true=80):
                start_hour = fake.random_int(min=7, max=9)
                end_hour = fake.random_int(min=17, max=20)
                schedule[day] = {
                    "available": True,
                    "start_time": f"{start_hour:02d}:00",
                    "end_time": f"{end_hour:02d}:00",
                    "break_slots": [
                        {"start": "12:00", "end": "13:00"},
                        {"start": "15:30", "end": "15:45"},
                    ],
                }
            else:
                schedule[day] = {"available": False}

        return {
            "weekly_schedule": schedule,
            "timezone": "UTC",
            "session_types": [
                {"type": "individual", "duration": 60},
                {"type": "group", "duration": 90},
                {"type": "intensive", "duration": 120},
            ],
            "booking_advance_days": fake.random_int(min=1, max=14),
            "cancellation_policy": "24 hours notice required",
        }

    class Meta:
        model = "users.Coach"


class PhysicianFactory(AbstractProfileFactoryMixin, DjangoModelFactory):
    """Comprehensive factory for Physician model."""

    license_number = factory.Sequence(lambda n: f"MD-{n:06d}")
    years_of_experience = factory.Faker("random_int", min=3, max=40)

    specialties = factory.Faker(
        "random_element",
        elements=[
            "Internal Medicine",
            "Family Medicine",
            "Cardiology",
            "Endocrinology",
            "Psychiatry",
            "Neurology",
            "Dermatology",
            "Orthopedics",
            "Pediatrics",
            "Gynecology",
            "Emergency Medicine",
            "Radiology",
            "Anesthesiology",
            "Surgery",
            "Oncology",
        ],
    )

    @factory.lazy_attribute
    def availability(self):
        """Generate realistic physician availability schedule JSON."""
        days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        schedule = {}

        for day in days:
            # 90% chance physician works on weekdays
            if fake.boolean(chance_of_getting_true=90):
                # Physicians often have longer days
                start_hour = fake.random_int(min=7, max=8)
                end_hour = fake.random_int(min=17, max=19)
                schedule[day] = {
                    "available": True,
                    "clinic_hours": {
                        "start": f"{start_hour:02d}:00",
                        "end": f"{end_hour:02d}:00",
                    },
                    "appointment_slots": {
                        "duration": fake.random_int(min=15, max=30),
                        "buffer_time": 5,
                    },
                    "lunch_break": {"start": "12:00", "end": "13:00"},
                }
            else:
                schedule[day] = {"available": False}

        # Some weekend availability
        for day in ["saturday", "sunday"]:
            if fake.boolean(chance_of_getting_true=20):
                schedule[day] = {
                    "available": True,
                    "clinic_hours": {"start": "09:00", "end": "14:00"},
                    "appointment_slots": {"duration": 20, "buffer_time": 5},
                }
            else:
                schedule[day] = {"available": False}

        return {
            "weekly_schedule": schedule,
            "timezone": "UTC",
            "emergency_on_call": fake.boolean(chance_of_getting_true=30),
            "hospital_rounds": {
                "days": list(
                    fake.random_elements(
                        elements=["monday", "wednesday", "friday"],
                        length=fake.random_int(min=1, max=3),
                        unique=True,
                    ),
                ),
                "time": "06:00-08:00",
            },
            "consultation_types": [
                {"type": "routine_checkup", "duration": 20},
                {"type": "follow_up", "duration": 15},
                {"type": "new_patient", "duration": 30},
                {"type": "urgent_care", "duration": 25},
            ],
        }

    class Meta:
        model = "users.Physician"


# Trait factories for creating specific user types more easily
class PatientUserFactory(UserFactory):
    """Factory that creates a User with a Patient profile."""

    @factory.post_generation
    def create_patient_profile(self, create, extracted, **kwargs):
        if create:
            PatientFactory(user=self, **kwargs)


class TherapistUserFactory(UserFactory):
    """Factory that creates a User with a Therapist profile."""

    @factory.post_generation
    def create_therapist_profile(self, create, extracted, **kwargs):
        if create:
            TherapistFactory(user=self, **kwargs)


class CoachUserFactory(UserFactory):
    """Factory that creates a User with a Coach profile."""

    @factory.post_generation
    def create_coach_profile(self, create, extracted, **kwargs):
        if create:
            CoachFactory(user=self, **kwargs)


class PhysicianUserFactory(UserFactory):
    """Factory that creates a User with a Physician profile."""

    @factory.post_generation
    def create_physician_profile(self, create, extracted, **kwargs):
        if create:
            PhysicianFactory(user=self, **kwargs)


# Additional specialized factories
class PatientWithDisordersFactory(PatientFactory):
    """Patient factory that ensures disorders are created."""

    @factory.post_generation
    def disorders(self, create, extracted, **kwargs):
        if not create:
            return

        from aura.mentalhealth.tests.factories import DisorderFactory

        if extracted:
            for disorder in extracted:
                self.disorders.add(disorder)
        else:
            # Always create 1-3 disorders for this factory
            disorder_count = fake.random_int(min=1, max=3)
            for _ in range(disorder_count):
                disorder = DisorderFactory()
                self.disorders.add(disorder)


class ExperiencedTherapistFactory(TherapistFactory):
    """Therapist factory for highly experienced therapists."""

    years_of_experience = factory.Faker("random_int", min=10, max=35)
    rating = factory.Faker(
        "pydecimal",
        left_digits=1,
        right_digits=2,
        min_value=Decimal("4.50"),
        max_value=Decimal("5.00"),
    )


class HighRatedCoachFactory(CoachFactory):
    """Coach factory for highly rated coaches."""

    rating = factory.Faker(
        "pydecimal",
        left_digits=1,
        right_digits=2,
        min_value=Decimal("4.70"),
        max_value=Decimal("5.00"),
    )
    years_of_experience = factory.Faker("random_int", min=5, max=25)


class SpecialistPhysicianFactory(PhysicianFactory):
    """Physician factory for specialists with significant experience."""

    years_of_experience = factory.Faker("random_int", min=8, max=30)
    specialties = factory.Faker(
        "random_element",
        elements=[
            "Cardiology",
            "Endocrinology",
            "Neurology",
            "Oncology",
            "Psychiatry",
            "Orthopedics",
            "Surgery",
        ],
    )
