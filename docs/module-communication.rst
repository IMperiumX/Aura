==================
Module Communication
==================

This document explains how modules communicate with each other in the Aura modular monolith architecture.

.. contents::
   :local:
   :depth: 2

Communication Principles
========================

**Loose Coupling**
  Modules should not directly depend on each other's implementation details.

**Interface-Based**
  Communication happens through well-defined interfaces and contracts.

**Event-Driven**
  Use events for notifications and side effects to maintain loose coupling.

**Fail-Safe**
  Communication should be resilient to failures in other modules.

Communication Mechanisms
========================

1. Service Registry
------------------

The Service Registry provides service discovery and direct method calls between modules.

**Location**: ``config/service_registry.py``

**Usage Example**:

.. code-block:: python

   from config.service_registry import service_registry

   # Get a service from another module
   user_service = service_registry.get_service('users', 'UserService')
   user_profile = user_service.get_user_profile(user_id)

**Registration Example**:

.. code-block:: python

   # In your module's __init__.py
   def register_services(service_registry):
       service_registry.register_service(
           module_name='notifications',
           service_name='EmailService',
           service_class=EmailService
       )

2. Event Bus
------------

The Event Bus enables publish/subscribe messaging between modules.

**Location**: ``config/service_registry.py`` (InterModuleEventBus class)

**Publishing Events**:

.. code-block:: python

   from config.service_registry import event_bus

   # Publish an event
   event_bus.publish(
       'therapy_session.scheduled',
       {
           'session_id': session.id,
           'patient_id': session.patient_id,
           'therapist_id': session.therapist_id,
           'scheduled_at': session.scheduled_at.isoformat()
       },
       'mentalhealth'  # source module
   )

**Subscribing to Events**:

.. code-block:: python

   def handle_session_scheduled(data):
       """Send notification when therapy session is scheduled."""
       session_id = data.get('session_id')
       patient_id = data.get('patient_id')
       
       # Send notification logic here
       print(f"Sending notification for session {session_id}")

   # Subscribe to event
   event_bus.subscribe(
       'therapy_session.scheduled',
       handle_session_scheduled,
       'notifications'  # subscriber module
   )

3. API Gateway
--------------

The API Gateway handles external API routing and inter-module HTTP communication.

**Location**: ``config/gateway.py``

**Features**:
- Centralized API routing
- Module service discovery
- Request/response transformation

4. Dependency Injection
-----------------------

The DI Container manages service lifecycle and dependencies.

**Location**: ``config/dependency_injection.py``

**Usage**:

.. code-block:: python

   from config.dependency_injection import get_container

   container = get_container()
   
   # Resolve a service
   user_service = container.resolve('user_service')
   notification_service = container.resolve('notification_service')

Event Types
===========

Standard Events
---------------

**User Events**
  - ``user.registered`` - New user registration
  - ``user.updated`` - User profile updated
  - ``user.deactivated`` - User account deactivated

**Therapy Session Events**
  - ``therapy_session.scheduled`` - New session scheduled
  - ``therapy_session.started`` - Session started
  - ``therapy_session.completed`` - Session completed
  - ``therapy_session.cancelled`` - Session cancelled

**Payment Events**
  - ``payment.completed`` - Payment successful
  - ``payment.failed`` - Payment failed
  - ``subscription.activated`` - Subscription activated

**Notification Events**
  - ``notification.sent`` - Notification sent successfully
  - ``notification.failed`` - Notification failed

Event Data Format
-----------------

All events should follow this structure:

.. code-block:: python

   {
       'event_id': 'uuid-string',
       'timestamp': 'ISO-8601-timestamp',
       'source_module': 'module-name',
       'event_type': 'event.type',
       'data': {
           # Event-specific data
       },
       'metadata': {
           'correlation_id': 'uuid-string',
           'user_id': 'user-id-if-applicable'
       }
   }

Communication Patterns
======================

1. Request/Response Pattern
---------------------------

Used for synchronous operations where you need an immediate response.

**Example**: Getting user profile information

.. code-block:: python

   # Mental Health module needs user info
   from config.service_registry import service_registry

   class TherapySessionService:
       def schedule_session(self, patient_id, therapist_id):
           # Get user service
           user_service = service_registry.get_service('users', 'UserService')
           
           # Validate users exist
           patient = user_service.get_user_by_id(patient_id)
           therapist = user_service.get_user_by_id(therapist_id)
           
           if not patient or not therapist:
               raise ValueError("Invalid user IDs")
           
           # Continue with session scheduling...

2. Publish/Subscribe Pattern
---------------------------

Used for asynchronous notifications and side effects.

**Example**: Sending notifications after session scheduling

.. code-block:: python

   # Mental Health module publishes event
   def schedule_session(self, session_data):
       # Create session...
       session = self.repository.save(session)
       
       # Publish event
       event_bus.publish(
           'therapy_session.scheduled',
           {
               'session_id': session.id,
               'patient_id': session.patient_id,
               'therapist_id': session.therapist_id,
               'scheduled_at': session.scheduled_at.isoformat()
           },
           'mentalhealth'
       )

   # Notifications module subscribes
   def handle_session_scheduled(data):
       session_id = data.get('session_id')
       patient_id = data.get('patient_id')
       
       # Send confirmation email to patient
       email_service.send_session_confirmation(patient_id, session_id)

3. Event Sourcing Pattern
-------------------------

For audit trails and complex state management.

.. code-block:: python

   # Store events for audit trail
   class EventStore:
       def store_event(self, event_type, data, source_module):
           event = Event(
               event_type=event_type,
               data=data,
               source_module=source_module,
               timestamp=datetime.now()
           )
           self.repository.save(event)
           
           # Also publish to event bus
           event_bus.publish(event_type, data, source_module)

Inter-Module Contracts
======================

Service Contracts
-----------------

Define clear interfaces for services:

.. code-block:: python

   # contracts/user_service_contract.py
   from abc import ABC, abstractmethod
   from typing import Optional, Dict, Any

   class UserServiceContract(ABC):
       @abstractmethod
       def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
           """Get user by ID."""
           pass
       
       @abstractmethod
       def is_user_active(self, user_id: int) -> bool:
           """Check if user is active."""
           pass

Event Contracts
---------------

Define event schemas:

.. code-block:: python

   # contracts/events.py
   from dataclasses import dataclass
   from typing import Optional
   from datetime import datetime

   @dataclass
   class TherapySessionScheduledEvent:
       session_id: int
       patient_id: int
       therapist_id: int
       scheduled_at: datetime
       session_type: str
       correlation_id: Optional[str] = None

Error Handling
==============

1. Service Unavailability
-------------------------

Handle cases where a service is not available:

.. code-block:: python

   def get_user_service():
       try:
           return service_registry.get_service('users', 'UserService')
       except ServiceNotAvailableError:
           # Fallback behavior or raise appropriate error
           raise UserServiceUnavailableError("User service is currently unavailable")

2. Event Delivery Failures
---------------------------

Handle event delivery failures gracefully:

.. code-block:: python

   def publish_event_safely(event_type, data, source_module):
       try:
           event_bus.publish(event_type, data, source_module)
       except EventDeliveryError as e:
           # Log error and potentially retry
           logger.error(f"Failed to publish event {event_type}: {e}")
           
           # Store for retry later
           failed_events_store.store(event_type, data, source_module)

3. Circuit Breaker Pattern
--------------------------

Prevent cascading failures:

.. code-block:: python

   class CircuitBreaker:
       def __init__(self, failure_threshold=5, timeout=60):
           self.failure_threshold = failure_threshold
           self.timeout = timeout
           self.failure_count = 0
           self.last_failure_time = None
           self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
       
       def call(self, func, *args, **kwargs):
           if self.state == 'OPEN':
               if time.time() - self.last_failure_time > self.timeout:
                   self.state = 'HALF_OPEN'
               else:
                   raise CircuitBreakerOpenError()
           
           try:
               result = func(*args, **kwargs)
               if self.state == 'HALF_OPEN':
                   self.state = 'CLOSED'
                   self.failure_count = 0
               return result
           except Exception as e:
               self.failure_count += 1
               self.last_failure_time = time.time()
               
               if self.failure_count >= self.failure_threshold:
                   self.state = 'OPEN'
               
               raise e

Best Practices
==============

1. **Design for Failure**
   - Always handle service unavailability
   - Implement timeouts for service calls
   - Use circuit breakers for resilience

2. **Keep Events Simple**
   - Include only necessary data in events
   - Use immutable event structures
   - Version your events for backward compatibility

3. **Avoid Chatty Communication**
   - Batch related operations
   - Use caching for frequently accessed data
   - Consider data locality

4. **Monitor Communication**
   - Log all inter-module calls
   - Track event publishing and consumption
   - Monitor communication latency

5. **Use Correlation IDs**
   - Track requests across modules
   - Enable distributed tracing
   - Simplify debugging

Example: Complete Communication Flow
====================================

Here's a complete example of how modules communicate when a therapy session is scheduled:

.. code-block:: python

   # 1. Mental Health Module - Schedule Session
   class ScheduleTherapySessionUseCase:
       def execute(self, request):
           # Validate users exist (synchronous call)
           user_service = service_registry.get_service('users', 'UserService')
           
           if not user_service.is_user_active(request.patient_id):
               raise ValueError("Patient is not active")
           
           if not user_service.is_user_active(request.therapist_id):
               raise ValueError("Therapist is not active")
           
           # Create session
           session = self.session_service.create_session(request)
           
           # Publish event (asynchronous)
           event_bus.publish(
               'therapy_session.scheduled',
               {
                   'session_id': session.id,
                   'patient_id': request.patient_id,
                   'therapist_id': request.therapist_id,
                   'scheduled_at': session.scheduled_at.isoformat()
               },
               'mentalhealth'
           )
           
           return session

   # 2. Notifications Module - Handle Event
   def handle_session_scheduled(data):
       session_id = data.get('session_id')
       patient_id = data.get('patient_id')
       therapist_id = data.get('therapist_id')
       
       # Get user details for notification
       user_service = service_registry.get_service('users', 'UserService')
       patient = user_service.get_user_by_id(patient_id)
       therapist = user_service.get_user_by_id(therapist_id)
       
       # Send notifications
       email_service = container.resolve('email_service')
       email_service.send_session_confirmation(patient, session_id)
       email_service.send_session_notification(therapist, session_id)

   # 3. Billing Module - Handle Event
   def handle_session_scheduled(data):
       session_id = data.get('session_id')
       patient_id = data.get('patient_id')
       
       # Create billing record
       billing_service = container.resolve('billing_service')
       billing_service.create_session_charge(patient_id, session_id)

This communication pattern ensures loose coupling while enabling rich interactions between modules.