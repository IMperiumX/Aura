======================
Clean Architecture Guide
======================

This guide explains how to implement Clean Architecture in Aura modules, using the Mental Health module as a reference implementation.

.. contents::
   :local:
   :depth: 2

What is Clean Architecture?
===========================

Clean Architecture is a software design philosophy that emphasizes:

- **Independence of Frameworks**: Business logic doesn't depend on frameworks
- **Testability**: Business rules can be tested without UI, database, or external services
- **Independence of UI**: The UI can change without affecting business rules
- **Independence of Database**: Business rules don't know about the database
- **Independence of External Services**: Business rules don't depend on external services

The Dependency Rule
===================

The overriding rule is the **Dependency Rule**:

   *Source code dependencies can only point inwards. Nothing in an inner circle can know anything at all about something in an outer circle.*

.. code-block:: text

   ┌─────────────────────────────────────────────┐
   │           🌐 Frameworks & Drivers           │
   │              (Django, Database)             │
   │ ┌─────────────────────────────────────────┐ │
   │ │        🔌 Interface Adapters            │ │
   │ │         (API, Repositories)             │ │
   │ │ ┌─────────────────────────────────────┐ │ │
   │ │ │       ⚙️ Application Business       │ │ │
   │ │ │            (Use Cases)              │ │ │
   │ │ │ ┌─────────────────────────────────┐ │ │ │
   │ │ │ │    🏛️ Enterprise Business      │ │ │ │
   │ │ │ │       (Entities)                │ │ │ │
   │ │ │ └─────────────────────────────────┘ │ │ │
   │ │ └─────────────────────────────────────┘ │ │
   │ └─────────────────────────────────────────┘ │
   └─────────────────────────────────────────────┘

Layer Breakdown
===============

1. Entities (Domain Layer)
--------------------------

**Location**: ``domain/entities/``

**Purpose**: Contain enterprise business logic and rules

**Characteristics**:
- Pure Python classes
- No dependencies on frameworks
- Contain business logic and validation
- Can be used across multiple applications

**Example**:

.. code-block:: python

   # domain/entities/therapy_session.py
   from dataclasses import dataclass
   from datetime import datetime
   from enum import Enum

   class SessionStatus(Enum):
       PENDING = "pending"
       ACCEPTED = "accepted"
       COMPLETED = "completed"
       CANCELLED = "cancelled"

   @dataclass
   class TherapySession:
       id: int
       therapist_id: int
       patient_id: int
       scheduled_at: datetime
       status: SessionStatus = SessionStatus.PENDING

       def start_session(self) -> None:
           """Business rule: Only accepted sessions can be started."""
           if self.status != SessionStatus.ACCEPTED:
               raise ValueError("Session must be accepted before starting")

           self.started_at = datetime.now()

       def complete_session(self, summary: str) -> None:
           """Business rule: Only started sessions can be completed."""
           if not hasattr(self, 'started_at'):
               raise ValueError("Session must be started before completing")

           self.status = SessionStatus.COMPLETED
           self.summary = summary
           self.ended_at = datetime.now()

2. Use Cases (Application Layer)
--------------------------------

**Location**: ``application/use_cases/``

**Purpose**: Contain application-specific business logic

**Characteristics**:
- Orchestrate data flow between entities
- Implement application-specific business rules
- Independent of UI and database concerns
- Define interfaces for external services

**Example**:

.. code-block:: python

   # application/use_cases/schedule_therapy_session.py
   from dataclasses import dataclass
   from typing import Optional
   from datetime import datetime

   @dataclass
   class ScheduleSessionRequest:
       therapist_id: int
       patient_id: int
       scheduled_at: datetime
       session_type: str

   @dataclass
   class ScheduleSessionResponse:
       success: bool
       session: Optional[TherapySession] = None
       error_message: Optional[str] = None

   class ScheduleTherapySessionUseCase:
       def __init__(self,
                    session_repository: TherapySessionRepository,
                    user_service: UserService,
                    notification_service: NotificationService):
           self._session_repository = session_repository
           self._user_service = user_service
           self._notification_service = notification_service

       def execute(self, request: ScheduleSessionRequest) -> ScheduleSessionResponse:
           try:
               # Validate business rules
               if not self._user_service.is_therapist_available(
                   request.therapist_id, request.scheduled_at):
                   raise ValueError("Therapist not available at requested time")

               # Create entity
               session = TherapySession(
                   therapist_id=request.therapist_id,
                   patient_id=request.patient_id,
                   scheduled_at=request.scheduled_at
               )

               # Validate entity business rules
               session.validate()

               # Persist
               saved_session = self._session_repository.save(session)

               # Side effects
               self._notification_service.notify_session_scheduled(saved_session)

               return ScheduleSessionResponse(success=True, session=saved_session)

           except ValueError as e:
               return ScheduleSessionResponse(success=False, error_message=str(e))

3. Interface Adapters (Infrastructure Layer)
--------------------------------------------

**Location**: ``infrastructure/`` and ``api/``

**Purpose**: Convert data between use cases and external services

**Characteristics**:
- Implement repository interfaces
- Handle framework-specific concerns
- Convert between entity and database models
- Implement external service adapters

**Repository Implementation**:

.. code-block:: python

   # infrastructure/repositories/django_therapy_session_repository.py
   from typing import List, Optional
   from aura.mentalhealth.domain.repositories.therapy_session_repository import TherapySessionRepository
   from aura.mentalhealth.domain.entities.therapy_session import TherapySession as SessionEntity
   from aura.mentalhealth.models import TherapySession as DjangoSession

   class DjangoTherapySessionRepository(TherapySessionRepository):
       def save(self, session: SessionEntity) -> SessionEntity:
           if session.id:
               django_session = DjangoSession.objects.get(id=session.id)
               self._update_model(django_session, session)
           else:
               django_session = self._create_model(session)

           django_session.save()
           return self._to_entity(django_session)

       def find_by_id(self, session_id: int) -> Optional[SessionEntity]:
           try:
               django_session = DjangoSession.objects.get(id=session_id)
               return self._to_entity(django_session)
           except DjangoSession.DoesNotExist:
               return None

       def _to_entity(self, django_model: DjangoSession) -> SessionEntity:
           """Convert Django model to domain entity."""
           return SessionEntity(
               id=django_model.id,
               therapist_id=django_model.therapist_id,
               patient_id=django_model.patient_id,
               scheduled_at=django_model.scheduled_at,
               status=SessionStatus(django_model.status)
           )

**API Adapter**:

.. code-block:: python

   # api/views.py
   from rest_framework import viewsets, status
   from rest_framework.response import Response
   from ..application.use_cases.schedule_therapy_session import (
       ScheduleTherapySessionUseCase,
       ScheduleSessionRequest
   )

   class TherapySessionViewSet(viewsets.ModelViewSet):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           # Dependency injection would happen here
           self.schedule_use_case = container.resolve('schedule_session_use_case')

       def create(self, request, *args, **kwargs):
           """Convert HTTP request to use case request."""
           use_case_request = ScheduleSessionRequest(
               therapist_id=request.data.get('therapist_id'),
               patient_id=request.data.get('patient_id'),
               scheduled_at=datetime.fromisoformat(request.data.get('scheduled_at')),
               session_type=request.data.get('session_type')
           )

           response = self.schedule_use_case.execute(use_case_request)

           if response.success:
               serializer = self.get_serializer(response.session)
               return Response(serializer.data, status=status.HTTP_201_CREATED)
           else:
               return Response(
                   {'error': response.error_message},
                   status=status.HTTP_400_BAD_REQUEST
               )

4. Frameworks & Drivers (External Layer)
----------------------------------------

**Location**: Django models, external APIs, databases

**Purpose**: Handle framework-specific implementations

**Characteristics**:
- Django models and ORM
- External API clients
- File system operations
- Database-specific code

Repository Interfaces
====================

Define clear contracts between layers:

.. code-block:: python

   # domain/repositories/therapy_session_repository.py
   from abc import ABC, abstractmethod
   from typing import List, Optional
   from ..entities.therapy_session import TherapySession

   class TherapySessionRepository(ABC):
       @abstractmethod
       def save(self, session: TherapySession) -> TherapySession:
           """Save a therapy session."""
           pass

       @abstractmethod
       def find_by_id(self, session_id: int) -> Optional[TherapySession]:
           """Find session by ID."""
           pass

       @abstractmethod
       def find_by_therapist(self, therapist_id: int) -> List[TherapySession]:
           """Find sessions by therapist."""
           pass

Domain Services
===============

For complex business logic that doesn't belong in entities:

.. code-block:: python

   # domain/services/therapy_session_service.py
   from typing import List
   from datetime import datetime, timedelta
   from ..entities.therapy_session import TherapySession
   from ..repositories.therapy_session_repository import TherapySessionRepository

   class TherapySessionDomainService:
       def __init__(self, repository: TherapySessionRepository):
           self._repository = repository

       def can_schedule_session(self, therapist_id: int,
                               scheduled_at: datetime) -> bool:
           """Complex business rule: Check if session can be scheduled."""

           # Rule 1: Cannot schedule in the past
           if scheduled_at <= datetime.now():
               return False

           # Rule 2: Therapist cannot have overlapping sessions
           existing_sessions = self._repository.find_by_therapist(therapist_id)

           for session in existing_sessions:
               if self._sessions_overlap(session.scheduled_at, scheduled_at):
                   return False

           # Rule 3: Maximum sessions per day
           daily_sessions = self._count_daily_sessions(therapist_id, scheduled_at.date())
           if daily_sessions >= 8:
               return False

           return True

       def _sessions_overlap(self, existing_time: datetime,
                           new_time: datetime) -> bool:
           """Check if two sessions overlap (assuming 1-hour sessions)."""
           time_diff = abs((existing_time - new_time).total_seconds())
           return time_diff < 3600  # Less than 1 hour apart

Dependency Inversion
===================

High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Wrong Way** (violates dependency inversion):

.. code-block:: python

   # Use case directly depends on Django model
   class ScheduleSessionUseCase:
       def execute(self, request):
           # Direct dependency on Django ORM
           session = DjangoTherapySession.objects.create(
               therapist_id=request.therapist_id,
               patient_id=request.patient_id
           )

**Right Way** (follows dependency inversion):

.. code-block:: python

   # Use case depends on abstraction
   class ScheduleSessionUseCase:
       def __init__(self, repository: TherapySessionRepository):
           self._repository = repository  # Depends on interface, not implementation

       def execute(self, request):
           session = TherapySession(
               therapist_id=request.therapist_id,
               patient_id=request.patient_id
           )
           return self._repository.save(session)

Testing in Clean Architecture
=============================

Clean Architecture makes testing easy because you can test each layer independently.

**Entity Tests** (Fast, No Dependencies):

.. code-block:: python

   # tests/domain/test_therapy_session.py
   import pytest
   from datetime import datetime
   from aura.mentalhealth.domain.entities.therapy_session import TherapySession, SessionStatus

   class TestTherapySession:
       def test_start_session_when_accepted(self):
           session = TherapySession(
               id=1,
               therapist_id=1,
               patient_id=1,
               scheduled_at=datetime.now(),
               status=SessionStatus.ACCEPTED
           )

           session.start_session()

           assert hasattr(session, 'started_at')
           assert session.started_at is not None

       def test_start_session_fails_when_not_accepted(self):
           session = TherapySession(
               id=1,
               therapist_id=1,
               patient_id=1,
               scheduled_at=datetime.now(),
               status=SessionStatus.PENDING
           )

           with pytest.raises(ValueError, match="Session must be accepted"):
               session.start_session()

**Use Case Tests** (Mock Dependencies):

.. code-block:: python

   # tests/application/test_schedule_session_use_case.py
   import pytest
   from unittest.mock import Mock
   from aura.mentalhealth.application.use_cases.schedule_therapy_session import (
       ScheduleTherapySessionUseCase, ScheduleSessionRequest
   )

   class TestScheduleTherapySessionUseCase:
       def test_schedule_session_success(self):
           # Setup mocks
           repository = Mock()
           user_service = Mock()
           notification_service = Mock()

           user_service.is_therapist_available.return_value = True
           repository.save.return_value = Mock(id=1)

           use_case = ScheduleTherapySessionUseCase(
               repository, user_service, notification_service
           )

           # Execute
           request = ScheduleSessionRequest(
               therapist_id=1,
               patient_id=1,
               scheduled_at=datetime.now(),
               session_type="video"
           )

           response = use_case.execute(request)

           # Assert
           assert response.success
           repository.save.assert_called_once()
           notification_service.notify_session_scheduled.assert_called_once()

**Integration Tests** (Real Dependencies):

.. code-block:: python

   # tests/integration/test_therapy_session_repository.py
   import pytest
   from django.test import TestCase
   from aura.mentalhealth.infrastructure.repositories.django_therapy_session_repository import (
       DjangoTherapySessionRepository
   )
   from aura.mentalhealth.domain.entities.therapy_session import TherapySession

   class TestDjangoTherapySessionRepository(TestCase):
       def setUp(self):
           self.repository = DjangoTherapySessionRepository()

       def test_save_and_find_session(self):
           # Create entity
           session = TherapySession(
               therapist_id=1,
               patient_id=1,
               scheduled_at=datetime.now()
           )

           # Save through repository
           saved_session = self.repository.save(session)

           # Find through repository
           found_session = self.repository.find_by_id(saved_session.id)

           # Assert
           assert found_session is not None
           assert found_session.therapist_id == 1
           assert found_session.patient_id == 1

Benefits of Clean Architecture
==============================

**Testability**
  - Easy to test business logic in isolation
  - Fast tests with no external dependencies
  - Clear separation of concerns

**Maintainability**
  - Business rules are centralized
  - Framework changes don't affect business logic
  - Easy to understand and modify

**Flexibility**
  - Can change databases without affecting business rules
  - Can change UI frameworks easily
  - Can swap external services

**Scalability**
  - Clear boundaries make it easy to extract to microservices
  - Domain logic can be reused across different applications
  - Easy to add new features without breaking existing ones

Common Pitfalls
===============

**Entities Depending on Frameworks**

.. code-block:: python

   # Wrong - Entity depends on Django
   from django.db import models

   class TherapySession(models.Model):  # Violates clean architecture
       pass

**Use Cases Depending on Implementation Details**

.. code-block:: python

   # Wrong - Use case depends on Django ORM
   class ScheduleSessionUseCase:
       def execute(self, request):
           session = DjangoTherapySession.objects.create(...)  # Violation

**Circular Dependencies**

.. code-block:: python

   # Wrong - Circular dependency
   from infrastructure.repositories import SomeRepository  # In domain layer

Migration from Existing Code
============================

If you have existing Django code, here's how to migrate to Clean Architecture:

1. **Extract Entities**
   - Move business logic from Django models to pure Python classes
   - Keep Django models for data persistence only

2. **Create Repository Interfaces**
   - Define abstractions for data access
   - Implement interfaces using Django ORM

3. **Extract Use Cases**
   - Move business logic from views to use case classes
   - Make views thin adapters that call use cases

4. **Implement Dependency Injection**
   - Wire up dependencies at the application boundary
   - Use interfaces instead of concrete implementations

This approach allows you to gradually refactor existing code while maintaining functionality.
