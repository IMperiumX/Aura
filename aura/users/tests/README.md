# User Model Factories Documentation

This document provides comprehensive guidance on using the user model factories in the Aura application for testing purposes.

## Overview

The user model factories provide production-ready, realistic test data for all user types in the Aura system:

- **User**: Base user model
- **Patient**: Healthcare patients with medical data
- **Therapist**: Mental health therapists with specialties
- **Coach**: Life/wellness coaches with ratings
- **Physician**: Medical doctors with specializations

## Quick Start

```python
from aura.users.tests.factories import (
    UserFactory,
    PatientFactory,
    TherapistFactory,
    CoachFactory,
    PhysicianFactory,
)

# Create basic instances
user = UserFactory()
patient = PatientFactory()
therapist = TherapistFactory()
coach = CoachFactory()
physician = PhysicianFactory()
```

## Factory Classes

### UserFactory

Creates base user instances with realistic data.

**Fields Generated:**
- `email`: Unique email address
- `name`: Random name
- `password`: Secure password (hashed)
- `last_password_change`: Recent datetime
- `last_active`: Recent activity
- `date_joined`: Historical join date
- `is_active`: True by default
- `is_password_expired`: 10% chance of being true

**Usage:**
```python
# Basic user
user = UserFactory()

# User with custom email
user = UserFactory(email="test@example.com")

# User with custom password
user = UserFactory(password="my_secure_password")

# Batch creation
users = UserFactory.create_batch(10)
```

### PatientFactory

Creates patient profiles with comprehensive medical data.

**Key Features:**
- Medical record numbers (MRN format)
- Insurance information
- Emergency contacts
- Realistic medical history JSON
- Current medications data
- Vital signs and lab results
- Patient preferences
- Vector embeddings for AI features
- Many-to-many relationships with disorders

**Usage:**
```python
# Basic patient
patient = PatientFactory()

# Patient with specific weight/height
patient = PatientFactory(weight=70.5, height=175)

# Patient with custom disorders
from aura.mentalhealth.tests.factories import DisorderFactory
disorders = DisorderFactory.create_batch(2)
patient = PatientFactory(disorders=disorders)

# Patient with custom medical history
custom_history = {
    "surgeries": [],
    "hospitalizations": [],
    "family_history": {"diabetes": True}
}
patient = PatientFactory(medical_history=custom_history)
```

**Medical Data Structure:**

The factory generates realistic JSON structures:

```python
# medical_history structure
{
    "surgeries": [
        {
            "procedure": "Appendectomy",
            "date": "2020-03-15",
            "hospital": "General Hospital"
        }
    ],
    "hospitalizations": [...],
    "family_history": {
        "diabetes": True,
        "heart_disease": False,
        "cancer": False,
        "mental_health": True
    }
}

# current_medications structure
{
    "medications": [
        {
            "name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "Once daily"
        }
    ],
    "last_updated": "2024-01-15T10:30:00Z"
}

# health_data structure
{
    "vital_signs": {
        "blood_pressure": {
            "systolic": 120,
            "diastolic": 80,
            "last_reading": "2024-01-15"
        },
        "heart_rate": 72,
        "temperature": 98.6,
        "oxygen_saturation": 98
    },
    "lab_results": {
        "cholesterol": {...},
        "blood_sugar": {...}
    }
}
```

### TherapistFactory

Creates therapist profiles with professional credentials and availability.

**Key Features:**
- License numbers (LIC format)
- Years of experience (1-35)
- Multiple therapy specialties (TaggableManager)
- Weekly availability schedules
- Vector embeddings for matching

**Usage:**
```python
# Basic therapist
therapist = TherapistFactory()

# Experienced therapist (10+ years)
therapist = ExperiencedTherapistFactory()

# Therapist with specific specialties
specialties = ["CBT", "Trauma Therapy", "Family Therapy"]
therapist = TherapistFactory(specialties=specialties)

# Therapist with custom availability
custom_schedule = {
    "weekly_schedule": {
        "monday": {"available": True, "start_time": "09:00", "end_time": "17:00"}
    },
    "timezone": "UTC",
    "session_duration": 50
}
therapist = TherapistFactory(availability=custom_schedule)
```

### CoachFactory

Creates coach profiles with certifications and ratings.

**Key Features:**
- Professional certifications
- Areas of expertise
- Coaching philosophy
- Decimal ratings (3.0-5.0)
- Availability schedules
- Physical measurements

**Usage:**
```python
# Basic coach
coach = CoachFactory()

# High-rated coach (4.7+ rating)
coach = HighRatedCoachFactory()

# Coach with specific certification
coach = CoachFactory(certification="International Coach Federation (ICF)")

# Coach with custom rating
coach = CoachFactory(rating=Decimal("4.85"))
```

### PhysicianFactory

Creates physician profiles with medical specializations.

**Key Features:**
- Medical license numbers (MD format)
- Medical specialties
- Years of experience (3-40)
- Comprehensive availability schedules
- Hospital rounds information
- Emergency on-call status

**Usage:**
```python
# Basic physician
physician = PhysicianFactory()

# Specialist physician
physician = SpecialistPhysicianFactory()

# Physician with specific specialty
physician = PhysicianFactory(specialties="Cardiology")

# Physician with custom experience
physician = PhysicianFactory(years_of_experience=15)
```

## Specialized Factories

### Combined User + Profile Factories

Create a user with an associated profile in one step:

```python
from aura.users.tests.factories import (
    PatientUserFactory,
    TherapistUserFactory,
    CoachUserFactory,
    PhysicianUserFactory,
)

# Creates User + Patient profile
patient_user = PatientUserFactory()

# Creates User + Therapist profile
therapist_user = TherapistUserFactory()

# Creates User + Coach profile
coach_user = CoachUserFactory()

# Creates User + Physician profile
physician_user = PhysicianUserFactory()
```

### Specialized Variant Factories

```python
# Patient guaranteed to have disorders
patient = PatientWithDisordersFactory()

# Experienced therapist (10+ years)
therapist = ExperiencedTherapistFactory()

# High-rated coach (4.7+ rating)
coach = HighRatedCoachFactory()

# Specialist physician with 8+ years experience
physician = SpecialistPhysicianFactory()
```

## Advanced Usage

### Batch Operations

```python
# Create multiple instances efficiently
patients = PatientFactory.create_batch(10)
therapists = TherapistFactory.create_batch(5)

# Build without saving to database
unsaved_patients = PatientFactory.build_batch(5)
```

### Customization

```python
# Override specific fields
patient = PatientFactory(
    weight=75.0,
    height=180.0,
    gender='m',
    allergies="No known allergies"
)

# Use custom related objects
user = UserFactory(email="specific@email.com")
patient = PatientFactory(user=user)

# Custom many-to-many relationships
disorders = DisorderFactory.create_batch(3)
patient = PatientFactory(disorders=disorders)
```

### Relationships

```python
# Create interconnected test data
therapist = TherapistFactory()
patient = PatientFactory()

# Use in therapy session factory
from aura.mentalhealth.tests.factories import TherapySessionFactory
session = TherapySessionFactory(
    therapist=therapist,
    patient=patient
)
```

## Best Practices

### 1. Use Appropriate Factories

```python
# Good: Use specific factory for your test needs
patient = PatientWithDisordersFactory()  # When you need disorders

# Better than: Creating patient then manually adding disorders
patient = PatientFactory()
disorder = DisorderFactory()
patient.disorders.add(disorder)
```

### 2. Leverage Traits and Variants

```python
# Use specialized factories for specific scenarios
experienced_therapist = ExperiencedTherapistFactory()
high_rated_coach = HighRatedCoachFactory()
specialist_physician = SpecialistPhysicianFactory()
```

### 3. Batch Creation for Performance

```python
# Efficient for setup methods
def setUp(self):
    self.patients = PatientFactory.create_batch(10)
    self.therapists = TherapistFactory.create_batch(5)
```

### 4. Custom Data When Needed

```python
# Override only what you need to test
def test_patient_with_diabetes(self):
    patient = PatientFactory(
        medical_conditions="Type 2 Diabetes",
        medical_history={
            "family_history": {"diabetes": True}
        }
    )
    # Test diabetes-specific logic
```

### 5. Use Build for Unit Tests

```python
# When you don't need database persistence
def test_patient_bmi_calculation(self):
    patient = PatientFactory.build(weight=70, height=175)
    self.assertEqual(patient.calculate_bmi(), 22.86)
```

## Testing with Factories

### Unit Tests

```python
from django.test import TestCase
from aura.users.tests.factories import PatientFactory

class PatientTestCase(TestCase):
    def test_patient_age_calculation(self):
        patient = PatientFactory(date_of_birth=date(1990, 1, 1))
        self.assertEqual(patient.age, 34)  # Assuming current year is 2024
```

### Integration Tests

```python
from django.test import TransactionTestCase
from aura.users.tests.factories import TherapistFactory, PatientFactory

class TherapySessionTestCase(TransactionTestCase):
    def setUp(self):
        self.therapist = TherapistFactory()
        self.patient = PatientFactory()

    def test_session_creation(self):
        # Test with realistic therapist and patient data
        session = TherapySession.objects.create(
            therapist=self.therapist,
            patient=self.patient,
            session_type='video'
        )
        self.assertTrue(session.pk)
```

### API Tests

```python
from rest_framework.test import APITestCase
from aura.users.tests.factories import PatientUserFactory

class PatientAPITestCase(APITestCase):
    def setUp(self):
        self.user = PatientUserFactory()
        self.client.force_authenticate(user=self.user)

    def test_patient_profile_endpoint(self):
        response = self.client.get('/api/patients/')
        self.assertEqual(response.status_code, 200)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all required factories are imported
2. **Relationship Errors**: Use `create()` instead of `build()` for ForeignKey relationships
3. **Unique Constraint Violations**: Factories handle this automatically, but custom data might conflict

### Performance Considerations

- Use `build()` when database persistence isn't needed
- Use `create_batch()` for multiple instances
- Consider using `factory.SubFactory` instead of creating related objects separately

### Debugging Factory Issues

```python
# Check what data is being generated
patient = PatientFactory.build()
print(f"Medical History: {patient.medical_history}")
print(f"Current Medications: {patient.current_medications}")

# Validate factory-generated data
patient = PatientFactory()
patient.full_clean()  # Raises ValidationError if invalid
```

## Contributing

When extending factories:

1. Follow the existing patterns and naming conventions
2. Include comprehensive tests for new fields
3. Update this documentation
4. Consider backward compatibility
5. Add realistic default values for new fields

## Examples

See `test_factories.py` for comprehensive examples of factory usage patterns and validation tests.
