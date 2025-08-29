=============================================
Creating a New Module in Aura Modular Monolith
=============================================

This guide walks you through creating a new module in the Aura modular monolith architecture. Each module can follow its own architectural pattern while integrating seamlessly with the existing system.

.. contents::
   :local:
   :depth: 3

Overview
========

The Aura platform uses a modular monolith architecture where:

- Each module is a self-contained business domain
- Modules communicate through well-defined interfaces
- Different architectural patterns can be used per module
- Modules can be easily extracted to microservices later

Step-by-Step Guide
==================

1. Planning Your Module
-----------------------

Before creating a module, define:

**Business Domain**
  What business capability will this module handle?

**Architecture Pattern**
  Choose from:
  - **Clean Architecture** (recommended for complex domains)
  - **Hexagonal Architecture** (good for external integrations)
  - **Layered Architecture** (simple CRUD operations)

**Dependencies**
  Which existing modules will this module depend on?

**Provided Services**
  What services will this module expose to other modules?

**Example: Creating a Notifications Module**

Let's create a notifications module that handles email, SMS, and push notifications.

2. Create Directory Structure
-----------------------------

Create the base module directory:

.. code-block:: bash

   mkdir aura/notifications
   cd aura/notifications

For **Clean Architecture** (recommended):

.. code-block:: bash

   mkdir -p {domain/{entities,repositories,services},application/{use_cases,interfaces},infrastructure/{repositories,external},api}
   touch __init__.py domain/__init__.py application/__init__.py infrastructure/__init__.py api/__init__.py
   touch domain/entities/__init__.py domain/repositories/__init__.py domain/services/__init__.py
   touch application/use_cases/__init__.py application/interfaces/__init__.py
   touch infrastructure/repositories/__init__.py infrastructure/external/__init__.py
   touch api/{__init__.py,views.py,serializers.py,urls.py}

For **Hexagonal Architecture**:

.. code-block:: bash

   mkdir -p {core,ports,adapters/{repositories,external,api}}
   touch __init__.py core/__init__.py ports/__init__.py adapters/__init__.py
   touch adapters/repositories/__init__.py adapters/external/__init__.py adapters/api/__init__.py

For **Layered Architecture**:

.. code-block:: bash

   mkdir -p {models,services,api}
   touch __init__.py models/__init__.py services/__init__.py api/__init__.py
   touch {models.py,services.py,admin.py,apps.py}
   touch api/{views.py,serializers.py,urls.py}

3. Configure Module Registration
--------------------------------

Add your module to ``config/modules.py``:

.. code-block:: python

   # config/modules.py
   AURA_MODULES = {
       # ... existing modules ...
       'notifications': {
           'name': 'Notifications',
           'description': 'Email, SMS, and push notification services',
           'api_prefix': 'notifications',
           'api_module': 'aura.notifications.api.urls',
           'services_module': 'aura.notifications.domain.services',
           'architecture': 'clean',  # or 'hexagonal', 'layered'
           'boundaries': {
               'domain': 'aura.notifications.domain',
               'infrastructure': 'aura.notifications.infrastructure',
               'application': 'aura.notifications.application',
               'presentation': 'aura.notifications.api'
           },
           'dependencies': ['users'],  # modules this depends on
           'provides': [
               'EmailService',
               'SMSService',
               'PushNotificationService'
           ]
       }
   }

4. Implement Clean Architecture Layers
--------------------------------------

**Domain Layer (Business Logic)**

Create domain entities:

.. code-block:: python

   # domain/entities/notification.py
   from dataclasses import dataclass
   from datetime import datetime
   from enum import Enum
   from typing import Optional, Dict, Any

   class NotificationType(Enum):
       EMAIL = "email"
       SMS = "sms"
       PUSH = "push"

   class NotificationStatus(Enum):
       PENDING = "pending"
       SENT = "sent"
       FAILED = "failed"
       DELIVERED = "delivered"

   @dataclass
   class Notification:
       id: Optional[int] = None
       type: NotificationType = NotificationType.EMAIL
       recipient: str = ""
       subject: str = ""
       message: str = ""
       status: NotificationStatus = NotificationStatus.PENDING
       metadata: Dict[str, Any] = None
       created_at: Optional[datetime] = None
       sent_at: Optional[datetime] = None
       
       def mark_as_sent(self) -> None:
           """Mark notification as sent."""
           if self.status != NotificationStatus.PENDING:
               raise ValueError("Only pending notifications can be marked as sent")
           
           self.status = NotificationStatus.SENT
           self.sent_at = datetime.now()
       
       def mark_as_failed(self, error_message: str = "") -> None:
           """Mark notification as failed."""
           self.status = NotificationStatus.FAILED
           if not self.metadata:
               self.metadata = {}
           self.metadata['error'] = error_message
       
       def validate(self) -> None:
           """Validate notification data."""
           errors = []
           
           if not self.recipient:
               errors.append("Recipient is required")
           
           if not self.message:
               errors.append("Message is required")
           
           if errors:
               raise ValueError(f"Validation failed: {', '.join(errors)}")

Create repository interfaces:

.. code-block:: python

   # domain/repositories/notification_repository.py
   from abc import ABC, abstractmethod
   from typing import List, Optional
   from datetime import datetime
   
   from ..entities.notification import Notification, NotificationStatus, NotificationType

   class NotificationRepository(ABC):
       """Abstract repository for notifications."""
       
       @abstractmethod
       def save(self, notification: Notification) -> Notification:
           """Save a notification."""
           pass
       
       @abstractmethod
       def find_by_id(self, notification_id: int) -> Optional[Notification]:
           """Find notification by ID."""
           pass
       
       @abstractmethod
       def find_by_recipient(self, recipient: str) -> List[Notification]:
           """Find notifications by recipient."""
           pass
       
       @abstractmethod
       def find_by_status(self, status: NotificationStatus) -> List[Notification]:
           """Find notifications by status."""
           pass
       
       @abstractmethod
       def find_pending_notifications(self, limit: int = 100) -> List[Notification]:
           """Find pending notifications for processing."""
           pass

Create domain services:

.. code-block:: python

   # domain/services/notification_service.py
   from typing import List, Dict, Any
   from ..entities.notification import Notification, NotificationType, NotificationStatus
   from ..repositories.notification_repository import NotificationRepository

   class NotificationDomainService:
       """Domain service for notification business logic."""
       
       def __init__(self, notification_repository: NotificationRepository):
           self._repository = notification_repository
       
       def create_notification(self, type: NotificationType, recipient: str,
                             subject: str, message: str, 
                             metadata: Dict[str, Any] = None) -> Notification:
           """Create a new notification with validation."""
           
           # Business rules
           self._validate_recipient(type, recipient)
           self._validate_message_content(message)
           
           notification = Notification(
               type=type,
               recipient=recipient,
               subject=subject,
               message=message,
               metadata=metadata or {}
           )
           
           notification.validate()
           return self._repository.save(notification)
       
       def _validate_recipient(self, type: NotificationType, recipient: str):
           """Validate recipient based on notification type."""
           if type == NotificationType.EMAIL:
               if '@' not in recipient:
                   raise ValueError("Invalid email address")
           elif type == NotificationType.SMS:
               if not recipient.startswith(('+', '0')) or len(recipient) < 10:
                   raise ValueError("Invalid phone number")
       
       def _validate_message_content(self, message: str):
           """Validate message content."""
           if len(message) > 1000:
               raise ValueError("Message too long (max 1000 characters)")
           
           # Add spam/content filtering logic here
           forbidden_words = ['spam', 'phishing']
           if any(word in message.lower() for word in forbidden_words):
               raise ValueError("Message contains forbidden content")

**Application Layer (Use Cases)**

.. code-block:: python

   # application/use_cases/send_notification.py
   from dataclasses import dataclass
   from typing import Optional, Dict, Any
   
   from ...domain.entities.notification import Notification, NotificationType
   from ...domain.repositories.notification_repository import NotificationRepository
   from ...domain.services.notification_service import NotificationDomainService

   @dataclass
   class SendNotificationRequest:
       type: NotificationType
       recipient: str
       subject: str
       message: str
       metadata: Optional[Dict[str, Any]] = None

   @dataclass
   class SendNotificationResponse:
       success: bool
       notification: Optional[Notification] = None
       error_message: Optional[str] = None

   class SendNotificationUseCase:
       """Use case for sending notifications."""
       
       def __init__(self, 
                    notification_repository: NotificationRepository,
                    notification_service: NotificationDomainService,
                    email_gateway,  # External service
                    sms_gateway):   # External service
           self._repository = notification_repository
           self._service = notification_service
           self._email_gateway = email_gateway
           self._sms_gateway = sms_gateway
       
       def execute(self, request: SendNotificationRequest) -> SendNotificationResponse:
           """Execute the send notification use case."""
           try:
               # Create notification
               notification = self._service.create_notification(
                   type=request.type,
                   recipient=request.recipient,
                   subject=request.subject,
                   message=request.message,
                   metadata=request.metadata
               )
               
               # Send through appropriate gateway
               if notification.type == NotificationType.EMAIL:
                   self._send_email(notification)
               elif notification.type == NotificationType.SMS:
                   self._send_sms(notification)
               elif notification.type == NotificationType.PUSH:
                   self._send_push(notification)
               
               # Mark as sent
               notification.mark_as_sent()
               updated_notification = self._repository.save(notification)
               
               return SendNotificationResponse(
                   success=True,
                   notification=updated_notification
               )
               
           except Exception as e:
               return SendNotificationResponse(
                   success=False,
                   error_message=str(e)
               )
       
       def _send_email(self, notification: Notification):
           """Send email notification."""
           return self._email_gateway.send(
               to=notification.recipient,
               subject=notification.subject,
               body=notification.message
           )
       
       def _send_sms(self, notification: Notification):
           """Send SMS notification."""
           return self._sms_gateway.send(
               to=notification.recipient,
               message=notification.message
           )
       
       def _send_push(self, notification: Notification):
           """Send push notification."""
           # Implementation for push notifications
           pass

**Infrastructure Layer**

.. code-block:: python

   # infrastructure/repositories/django_notification_repository.py
   from typing import List, Optional
   from datetime import datetime
   
   from ...domain.entities.notification import Notification as NotificationEntity, NotificationStatus, NotificationType
   from ...domain.repositories.notification_repository import NotificationRepository
   from ...models import Notification as DjangoNotification

   class DjangoNotificationRepository(NotificationRepository):
       """Django ORM implementation of notification repository."""
       
       def save(self, notification: NotificationEntity) -> NotificationEntity:
           """Save notification to database."""
           if notification.id:
               django_notification = DjangoNotification.objects.get(id=notification.id)
               self._update_django_model(django_notification, notification)
           else:
               django_notification = self._create_django_model(notification)
           
           django_notification.save()
           return self._to_domain_entity(django_notification)
       
       def find_by_id(self, notification_id: int) -> Optional[NotificationEntity]:
           """Find notification by ID."""
           try:
               django_notification = DjangoNotification.objects.get(id=notification_id)
               return self._to_domain_entity(django_notification)
           except DjangoNotification.DoesNotExist:
               return None
       
       def find_by_recipient(self, recipient: str) -> List[NotificationEntity]:
           """Find notifications by recipient."""
           django_notifications = DjangoNotification.objects.filter(
               recipient=recipient
           ).order_by('-created')
           
           return [self._to_domain_entity(n) for n in django_notifications]
       
       def find_by_status(self, status: NotificationStatus) -> List[NotificationEntity]:
           """Find notifications by status."""
           django_notifications = DjangoNotification.objects.filter(
               status=status.value
           ).order_by('-created')
           
           return [self._to_domain_entity(n) for n in django_notifications]
       
       def find_pending_notifications(self, limit: int = 100) -> List[NotificationEntity]:
           """Find pending notifications."""
           django_notifications = DjangoNotification.objects.filter(
               status=NotificationStatus.PENDING.value
           ).order_by('created')[:limit]
           
           return [self._to_domain_entity(n) for n in django_notifications]
       
       def _create_django_model(self, entity: NotificationEntity) -> DjangoNotification:
           """Create Django model from domain entity."""
           return DjangoNotification(
               type=entity.type.value,
               recipient=entity.recipient,
               subject=entity.subject,
               message=entity.message,
               status=entity.status.value,
               metadata=entity.metadata or {}
           )
       
       def _update_django_model(self, django_model: DjangoNotification, 
                               entity: NotificationEntity) -> None:
           """Update Django model with entity data."""
           django_model.type = entity.type.value
           django_model.recipient = entity.recipient
           django_model.subject = entity.subject
           django_model.message = entity.message
           django_model.status = entity.status.value
           django_model.metadata = entity.metadata or {}
           django_model.sent_at = entity.sent_at
       
       def _to_domain_entity(self, django_model: DjangoNotification) -> NotificationEntity:
           """Convert Django model to domain entity."""
           return NotificationEntity(
               id=django_model.id,
               type=NotificationType(django_model.type),
               recipient=django_model.recipient,
               subject=django_model.subject,
               message=django_model.message,
               status=NotificationStatus(django_model.status),
               metadata=django_model.metadata,
               created_at=django_model.created,
               sent_at=django_model.sent_at
           )

Create Django models:

.. code-block:: python

   # models.py
   from django.db import models
   from django.contrib.postgres.fields import JSONField
   from model_utils.models import TimeStampedModel

   class Notification(TimeStampedModel):
       class NotificationType(models.TextChoices):
           EMAIL = "email", "Email"
           SMS = "sms", "SMS"
           PUSH = "push", "Push Notification"

       class NotificationStatus(models.TextChoices):
           PENDING = "pending", "Pending"
           SENT = "sent", "Sent"
           FAILED = "failed", "Failed"
           DELIVERED = "delivered", "Delivered"

       type = models.CharField(max_length=10, choices=NotificationType.choices)
       recipient = models.CharField(max_length=255)
       subject = models.CharField(max_length=255, blank=True)
       message = models.TextField()
       status = models.CharField(
           max_length=20, 
           choices=NotificationStatus.choices,
           default=NotificationStatus.PENDING
       )
       metadata = JSONField(default=dict, blank=True)
       sent_at = models.DateTimeField(null=True, blank=True)

       class Meta:
           ordering = ['-created']
           indexes = [
               models.Index(fields=['recipient', 'status']),
               models.Index(fields=['status', 'created']),
           ]

       def __str__(self):
           return f"{self.get_type_display()} to {self.recipient}"

**Presentation Layer (API)**

.. code-block:: python

   # api/views.py
   from rest_framework import viewsets, status
   from rest_framework.decorators import action
   from rest_framework.response import Response
   from rest_framework.permissions import IsAuthenticated
   from datetime import datetime
   
   from ..application.use_cases.send_notification import (
       SendNotificationUseCase,
       SendNotificationRequest
   )
   from ..domain.entities.notification import NotificationType
   from ..infrastructure.repositories.django_notification_repository import DjangoNotificationRepository
   from ..domain.services.notification_service import NotificationDomainService
   
   from .serializers import NotificationSerializer
   from ..models import Notification

   class NotificationViewSet(viewsets.ModelViewSet):
       """API endpoints for notifications."""
       
       queryset = Notification.objects.all()
       serializer_class = NotificationSerializer
       permission_classes = [IsAuthenticated]
       
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           # Initialize dependencies using DI container
           from config.dependency_injection import get_container
           container = get_container()
           
           try:
               self.send_use_case = container.resolve('send_notification_use_case')
           except ValueError:
               # Fallback initialization
               repository = DjangoNotificationRepository()
               service = NotificationDomainService(repository)
               self.send_use_case = SendNotificationUseCase(
                   repository, service, None, None  # Gateways would be injected
               )
       
       def create(self, request, *args, **kwargs):
           """Send a new notification."""
           try:
               data = request.data
               
               use_case_request = SendNotificationRequest(
                   type=NotificationType(data.get('type')),
                   recipient=data.get('recipient'),
                   subject=data.get('subject', ''),
                   message=data.get('message'),
                   metadata=data.get('metadata')
               )
               
               response = self.send_use_case.execute(use_case_request)
               
               if response.success:
                   serializer = self.get_serializer(
                       self._domain_to_django_model(response.notification)
                   )
                   return Response(
                       serializer.data,
                       status=status.HTTP_201_CREATED
                   )
               else:
                   return Response(
                       {'error': response.error_message},
                       status=status.HTTP_400_BAD_REQUEST
                   )
                   
           except Exception as e:
               return Response(
                   {'error': f'An error occurred: {str(e)}'},
                   status=status.HTTP_500_INTERNAL_SERVER_ERROR
               )
       
       @action(detail=False, methods=['post'])
       def send_bulk(self, request):
           """Send multiple notifications."""
           # Implementation for bulk sending
           pass
       
       @action(detail=False, methods=['get'])
       def statistics(self, request):
           """Get notification statistics."""
           # Implementation for statistics
           pass
       
       def _domain_to_django_model(self, domain_entity):
           """Convert domain entity to Django model."""
           try:
               return Notification.objects.get(id=domain_entity.id)
           except Notification.DoesNotExist:
               raise Http404("Notification not found")

Create URL routing:

.. code-block:: python

   # api/urls.py
   from django.urls import path, include
   from rest_framework.routers import DefaultRouter
   from .views import NotificationViewSet

   router = DefaultRouter()
   router.register(r'notifications', NotificationViewSet, basename='notification')

   app_name = 'notifications'

   urlpatterns = [
       path('', include(router.urls)),
   ]

   def register_routes(gateway_router, prefix='notifications'):
       """Register routes with the API gateway."""
       for pattern in router.urls:
           gateway_router.register(f'{prefix}/{pattern.pattern}', pattern.callback, basename=pattern.name)

5. Set Up Dependency Injection
------------------------------

Update ``config/dependency_injection.py``:

.. code-block:: python

   def setup_notifications_dependencies():
       """Set up dependency injection for notifications module."""
       from aura.notifications.infrastructure.repositories.django_notification_repository import DjangoNotificationRepository
       from aura.notifications.domain.services.notification_service import NotificationDomainService
       from aura.notifications.application.use_cases.send_notification import SendNotificationUseCase
       
       # Register repositories
       container.register('notification_repository', DjangoNotificationRepository)
       
       # Register domain services
       container.register_factory(
           'notification_service',
           lambda c: NotificationDomainService(c.resolve('notification_repository'))
       )
       
       # Register use cases
       container.register_factory(
           'send_notification_use_case',
           lambda c: SendNotificationUseCase(
               c.resolve('notification_repository'),
               c.resolve('notification_service'),
               None,  # Email gateway would be injected
               None   # SMS gateway would be injected
           )
       )

   # Add to initialization
   try:
       setup_notifications_dependencies()
   except ImportError:
       pass

6. Register Services for Inter-Module Communication
--------------------------------------------------

Create service registration:

.. code-block:: python

   # domain/services/__init__.py
   def register_services(service_registry):
       """Register notification services."""
       from ..repositories.django_notification_repository import DjangoNotificationRepository
       from .notification_service import NotificationDomainService
       
       service_registry.register_service(
           module_name='notifications',
           service_name='NotificationService',
           service_class=NotificationDomainService,
           dependencies=[DjangoNotificationRepository()]
       )

   def subscribe_to_events(event_bus, module_name):
       """Subscribe to inter-module events."""
       
       def handle_therapy_session_scheduled(data):
           """Send notification when therapy session is scheduled."""
           # Implementation for sending notification
           pass
       
       def handle_user_registered(data):
           """Send welcome notification when user registers."""
           # Implementation for welcome email
           pass
       
       event_bus.subscribe('therapy_session.scheduled', handle_therapy_session_scheduled, module_name)
       event_bus.subscribe('user.registered', handle_user_registered, module_name)

7. Update Main Configuration
---------------------------

Add to Django settings:

.. code-block:: python

   # config/settings/base.py
   LOCAL_APPS = [
       "aura.users",
       "aura.mentalhealth", 
       "aura.notifications",  # Add new module
       # Your stuff: custom apps go here
   ]

Update API router:

.. code-block:: python

   # config/api_router.py
   from aura.notifications.api.views import NotificationViewSet

   # Add notification routes
   router.register("notifications/notifications", NotificationViewSet)

Create and run migrations:

.. code-block:: bash

   python manage.py makemigrations notifications
   python manage.py migrate

8. Testing Your Module
----------------------

**Unit Tests**

.. code-block:: python

   # tests/test_domain/test_notification_entity.py
   import pytest
   from datetime import datetime
   from aura.notifications.domain.entities.notification import (
       Notification, NotificationType, NotificationStatus
   )

   class TestNotificationEntity:
       def test_create_notification(self):
           notification = Notification(
               type=NotificationType.EMAIL,
               recipient="test@example.com",
               subject="Test",
               message="Test message"
           )
           
           assert notification.type == NotificationType.EMAIL
           assert notification.status == NotificationStatus.PENDING
       
       def test_mark_as_sent(self):
           notification = Notification(
               type=NotificationType.EMAIL,
               recipient="test@example.com",
               message="Test"
           )
           
           notification.mark_as_sent()
           
           assert notification.status == NotificationStatus.SENT
           assert notification.sent_at is not None
       
       def test_validation_fails_without_recipient(self):
           notification = Notification(message="Test")
           
           with pytest.raises(ValueError, match="Recipient is required"):
               notification.validate()

**Integration Tests**

.. code-block:: python

   # tests/test_use_cases/test_send_notification.py
   import pytest
   from unittest.mock import Mock
   
   from aura.notifications.application.use_cases.send_notification import (
       SendNotificationUseCase, SendNotificationRequest
   )
   from aura.notifications.domain.entities.notification import NotificationType

   class TestSendNotificationUseCase:
       def test_send_email_notification_success(self):
           # Setup mocks
           repository = Mock()
           service = Mock()
           email_gateway = Mock()
           sms_gateway = Mock()
           
           use_case = SendNotificationUseCase(
               repository, service, email_gateway, sms_gateway
           )
           
           # Test data
           request = SendNotificationRequest(
               type=NotificationType.EMAIL,
               recipient="test@example.com",
               subject="Test",
               message="Test message"
           )
           
           # Execute
           response = use_case.execute(request)
           
           # Assert
           assert response.success
           service.create_notification.assert_called_once()
           email_gateway.send.assert_called_once()

**API Tests**

.. code-block:: python

   # tests/test_api/test_notification_views.py
   import pytest
   from django.test import TestCase
   from rest_framework.test import APIClient
   from rest_framework import status
   from django.contrib.auth import get_user_model

   User = get_user_model()

   class TestNotificationAPI(TestCase):
       def setUp(self):
           self.client = APIClient()
           self.user = User.objects.create_user(
               email='test@example.com',
               password='testpass123'
           )
           self.client.force_authenticate(user=self.user)
       
       def test_create_notification(self):
           data = {
               'type': 'email',
               'recipient': 'recipient@example.com',
               'subject': 'Test Subject',
               'message': 'Test message'
           }
           
           response = self.client.post('/api/notifications/notifications/', data)
           
           assert response.status_code == status.HTTP_201_CREATED

9. Documentation
---------------

Create module-specific documentation:

.. code-block:: rst

   # docs/notifications-module.rst
   Notifications Module
   ==================
   
   The notifications module handles all outbound communications including:
   
   - Email notifications
   - SMS notifications  
   - Push notifications
   
   Architecture
   -----------
   
   This module follows Clean Architecture with:
   
   - Domain layer for business logic
   - Application layer for use cases
   - Infrastructure layer for external services
   - Presentation layer for APIs
   
   APIs
   ----
   
   POST /api/notifications/notifications/
       Send a notification
   
   GET /api/notifications/notifications/
       List notifications
   
   POST /api/notifications/notifications/send_bulk/
       Send multiple notifications

10. Best Practices
-----------------

**Domain Layer**
- Keep entities pure (no framework dependencies)
- Use value objects for complex data types
- Implement business rules in domain services
- Define clear repository interfaces

**Application Layer**
- One use case per business operation
- Handle cross-cutting concerns (logging, validation)
- Coordinate between domain and infrastructure

**Infrastructure Layer**
- Implement repository interfaces
- Handle external service integration
- Keep framework-specific code isolated

**Testing**
- Test business logic in isolation
- Use mocks for external dependencies
- Write integration tests for use cases
- Test API endpoints with real HTTP calls

**Inter-Module Communication**
- Use events for loose coupling
- Avoid direct imports between modules
- Define clear service contracts
- Handle failures gracefully

Conclusion
==========

Following this guide, you've created a new module that:

- Follows clean architecture principles
- Integrates with the modular monolith system
- Supports inter-module communication
- Is fully tested and documented
- Can be easily extracted to a microservice later

The module is now ready for development and can be extended with additional features as needed.