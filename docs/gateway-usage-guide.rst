==================
API Gateway Usage Guide
==================

This guide explains how to use the API Gateway for inter-module communication in the Aura modular monolith.

.. contents::
   :local:
   :depth: 2

Overview
========

The API Gateway (`config/gateway.py`) provides:

- **Module Registry**: Manages module configurations and capabilities
- **Service Discovery**: Finds and instantiates services from other modules
- **Inter-Module Communication**: Secure method calls between modules
- **Health Monitoring**: Check module health and availability
- **Dependency Validation**: Ensures modules only call allowed dependencies

Gateway Architecture
===================

.. code-block:: text

   ┌─────────────────────────────────────────────┐
   │              API Gateway                    │
   │                                             │
   │  ┌─────────────────┐  ┌──────────────────┐  │
   │  │ Module Registry │  │ Service Cache    │  │
   │  │                 │  │                  │  │
   │  │ - Configuration │  │ - Service        │  │
   │  │ - Dependencies  │  │   Instances      │  │
   │  │ - Health Status │  │ - DI Integration │  │
   │  └─────────────────┘  └──────────────────┘  │
   └─────────────────────────────────────────────┘
                        │
      ┌─────────────────┼─────────────────┐
      │                 │                 │
   ┌──▼───┐        ┌────▼────┐        ┌──▼───┐
   │Users │        │Mental   │        │Other │
   │Module│        │Health   │        │Module│
   └──────┘        └─────────┘        └──────┘

Usage Patterns
==============

1. Getting Services from Other Modules
--------------------------------------

**Basic Service Retrieval**:

.. code-block:: python

   from config.gateway import gateway

   # Get a service from another module
   user_service = gateway.get_module_service('users', 'UserService')
   
   if user_service:
       user_profile = user_service.get_user_profile(user_id)
   else:
       # Handle service unavailable
       raise ServiceUnavailableError("User service not available")

**With Error Handling**:

.. code-block:: python

   def get_user_safely(user_id: int):
       try:
           user_service = gateway.get_module_service('users', 'UserService')
           if not user_service:
               return None
               
           return user_service.get_user_by_id(user_id)
       except Exception as e:
           logger.error(f"Failed to get user {user_id}: {e}")
           return None

2. Inter-Module Method Calls
----------------------------

**Direct Method Calls**:

.. code-block:: python

   # Mental health module calling user service
   from config.gateway import gateway

   class TherapySessionService:
       def schedule_session(self, patient_id: int, therapist_id: int):
           # Validate users exist using inter-module call
           try:
               patient = gateway.inter_module_call(
                   source_module='mentalhealth',
                   target_module='users',
                   service='UserService',
                   method='get_user_by_id',
                   patient_id
               )
               
               if not patient:
                   raise ValueError("Patient not found")
                   
               # Continue with session scheduling...
               
           except ValueError as e:
               # Handle dependency validation error
               logger.error(f"Module dependency error: {e}")
               raise

**Batch Operations**:

.. code-block:: python

   def validate_multiple_users(user_ids: List[int]) -> Dict[int, bool]:
       user_service = gateway.get_module_service('users', 'UserService')
       if not user_service:
           return {uid: False for uid in user_ids}
       
       results = {}
       for user_id in user_ids:
           try:
               user = user_service.get_user_by_id(user_id)
               results[user_id] = user is not None and user.get('is_active', False)
           except Exception:
               results[user_id] = False
       
       return results

3. Module Health Monitoring
---------------------------

**Check Single Module Health**:

.. code-block:: python

   # Check if a module is healthy
   health_status = gateway.get_module_health('users')
   
   if health_status['status'] == 'healthy':
       print(f"Module is healthy. Services: {health_status['services']}")
   else:
       print(f"Module unhealthy: {health_status['message']}")

**Monitor All Modules**:

.. code-block:: python

   def check_system_health():
       all_modules = gateway.list_modules()
       
       healthy_modules = []
       unhealthy_modules = []
       
       for module_name, health in all_modules.items():
           if health['status'] == 'healthy':
               healthy_modules.append(module_name)
           else:
               unhealthy_modules.append({
                   'module': module_name,
                   'error': health.get('message', 'Unknown error')
               })
       
       return {
           'healthy': healthy_modules,
           'unhealthy': unhealthy_modules,
           'total_modules': len(all_modules)
       }

4. Service Caching
------------------

The gateway automatically caches service instances for performance:

.. code-block:: python

   # First call - service is instantiated and cached
   user_service1 = gateway.get_module_service('users', 'UserService')
   
   # Second call - returns cached instance (much faster)
   user_service2 = gateway.get_module_service('users', 'UserService')
   
   # user_service1 and user_service2 are the same instance
   assert user_service1 is user_service2

Integration Examples
===================

1. Mental Health Module Using Gateway
-------------------------------------

.. code-block:: python

   # aura/mentalhealth/application/use_cases/schedule_therapy_session.py
   from config.gateway import gateway
   from typing import Optional

   class ScheduleTherapySessionUseCase:
       def __init__(self):
           # Services will be resolved through gateway
           pass
       
       def execute(self, request: ScheduleSessionRequest) -> ScheduleSessionResponse:
           try:
               # Get user service through gateway
               user_service = gateway.get_module_service('users', 'UserService')
               if not user_service:
                   return ScheduleSessionResponse(
                       success=False,
                       error_message="User service unavailable"
                   )
               
               # Validate patient exists and is active
               patient = user_service.get_user_by_id(request.patient_id)
               if not patient or not patient.get('is_active'):
                   return ScheduleSessionResponse(
                       success=False,
                       error_message="Invalid or inactive patient"
                   )
               
               # Validate therapist exists
               therapist = user_service.get_user_by_id(request.therapist_id)
               if not therapist or not user_service.is_user_therapist(request.therapist_id):
                   return ScheduleSessionResponse(
                       success=False,
                       error_message="Invalid therapist"
                   )
               
               # Schedule session (business logic)
               session = self._create_session(request)
               
               # Notify other modules through event bus
               self._notify_session_scheduled(session)
               
               return ScheduleSessionResponse(success=True, session=session)
               
           except Exception as e:
               return ScheduleSessionResponse(
                   success=False,
                   error_message=f"Scheduling failed: {str(e)}"
               )

2. Notifications Module Responding to Events
--------------------------------------------

.. code-block:: python

   # aura/notifications/services.py
   from config.gateway import gateway
   from config.service_registry import event_bus

   class NotificationService:
       def __init__(self):
           # Subscribe to relevant events
           event_bus.subscribe(
               'therapy_session.scheduled',
               self.handle_session_scheduled,
               'notifications'
           )
       
       def handle_session_scheduled(self, event_data):
           """Handle therapy session scheduled event."""
           try:
               session_id = event_data.get('session_id')
               patient_id = event_data.get('patient_id')
               therapist_id = event_data.get('therapist_id')
               
               # Get user details through gateway
               user_service = gateway.get_module_service('users', 'UserService')
               if not user_service:
                   logger.error("Cannot send notifications: User service unavailable")
                   return
               
               patient = user_service.get_user_by_id(patient_id)
               therapist = user_service.get_user_by_id(therapist_id)
               
               if patient and therapist:
                   # Send confirmation emails
                   self.send_session_confirmation(patient, session_id)
                   self.send_session_notification(therapist, session_id)
               
           except Exception as e:
               logger.error(f"Failed to handle session scheduled event: {e}")

3. Health Check Endpoint
-----------------------

.. code-block:: python

   # aura/core/api/views.py
   from rest_framework.decorators import api_view
   from rest_framework.response import Response
   from config.gateway import gateway

   @api_view(['GET'])
   def system_health(request):
       """Get system health status."""
       try:
           health_data = gateway.list_modules()
           
           overall_status = 'healthy' if all(
               module['status'] == 'healthy' 
               for module in health_data.values()
           ) else 'degraded'
           
           return Response({
               'status': overall_status,
               'modules': health_data,
               'timestamp': timezone.now().isoformat()
           })
           
       except Exception as e:
           return Response({
               'status': 'error',
               'message': str(e),
               'timestamp': timezone.now().isoformat()
           }, status=500)

Configuration
=============

Module Configuration in `config/modules.py`:

.. code-block:: python

   AURA_MODULES = {
       'users': {
           'name': 'User Management',
           'services_module': 'aura.users.services',
           'dependencies': [],  # No dependencies
           'provides': ['UserService', 'AuthenticationService']
       },
       'mentalhealth': {
           'name': 'Mental Health',
           'services_module': 'aura.mentalhealth.domain.services',
           'dependencies': ['users'],  # Can call users module
           'provides': ['TherapySessionService', 'DisorderService']
       },
       'notifications': {
           'name': 'Notifications',
           'services_module': 'aura.notifications.services',
           'dependencies': ['users'],  # Can call users module
           'provides': ['EmailService', 'SMSService', 'NotificationService']
       }
   }

Service Registration
===================

Each module should register its services:

.. code-block:: python

   # aura/users/services.py
   class UserService:
       def get_user_by_id(self, user_id: int):
           # Implementation
           pass
       
       def is_user_therapist(self, user_id: int) -> bool:
           # Implementation
           pass

   class AuthenticationService:
       def authenticate_user(self, email: str, password: str):
           # Implementation
           pass

   # Registration function called by gateway
   def get_services():
       return {
           'UserService': UserService,
           'AuthenticationService': AuthenticationService
       }

Error Handling
==============

**Service Unavailability**:

.. code-block:: python

   def safe_service_call(module_name: str, service_name: str, method: str, *args, **kwargs):
       try:
           service = gateway.get_module_service(module_name, service_name)
           if not service:
               return None, f"{module_name}.{service_name} not available"
           
           if not hasattr(service, method):
               return None, f"Method {method} not found on {service_name}"
           
           result = getattr(service, method)(*args, **kwargs)
           return result, None
           
       except Exception as e:
           return None, str(e)

**Dependency Validation**:

.. code-block:: python

   # This will raise ValueError if mentalhealth module tries to call billing module
   # when billing is not in mentalhealth's dependencies
   try:
       result = gateway.inter_module_call(
           'mentalhealth', 'billing', 'BillingService', 'charge_session'
       )
   except ValueError as e:
       logger.error(f"Dependency violation: {e}")

Testing with Gateway
===================

**Unit Tests with Mocked Gateway**:

.. code-block:: python

   import pytest
   from unittest.mock import Mock, patch

   class TestScheduleSessionUseCase:
       @patch('config.gateway.gateway.get_module_service')
       def test_schedule_session_success(self, mock_get_service):
           # Setup mock
           mock_user_service = Mock()
           mock_user_service.get_user_by_id.return_value = {'id': 1, 'is_active': True}
           mock_user_service.is_user_therapist.return_value = True
           mock_get_service.return_value = mock_user_service
           
           # Test
           use_case = ScheduleTherapySessionUseCase()
           request = ScheduleSessionRequest(patient_id=1, therapist_id=2, ...)
           
           response = use_case.execute(request)
           
           # Assert
           assert response.success
           mock_get_service.assert_called_with('users', 'UserService')

**Integration Tests**:

.. code-block:: python

   class TestGatewayIntegration(TestCase):
       def test_user_service_available(self):
           user_service = gateway.get_module_service('users', 'UserService')
           self.assertIsNotNone(user_service)
           
       def test_module_health(self):
           health = gateway.get_module_health('users')
           self.assertEqual(health['status'], 'healthy')

Best Practices
==============

1. **Always Handle Service Unavailability**
   
   .. code-block:: python
   
      service = gateway.get_module_service('users', 'UserService')
      if not service:
          # Handle gracefully - don't crash
          return default_value

2. **Cache Service References in Long-Running Operations**
   
   .. code-block:: python
   
      class LongRunningProcessor:
          def __init__(self):
              # Cache at initialization
              self.user_service = gateway.get_module_service('users', 'UserService')
          
          def process_item(self, item):
              if self.user_service:
                  # Use cached service
                  user = self.user_service.get_user_by_id(item.user_id)

3. **Use Inter-Module Calls for Critical Dependencies**
   
   .. code-block:: python
   
      # This enforces dependency validation
      result = gateway.inter_module_call(
          'mentalhealth', 'users', 'UserService', 'get_user_by_id', user_id
      )

4. **Monitor Module Health in Production**
   
   .. code-block:: python
   
      # Regular health checks
      health_status = gateway.list_modules()
      for module, health in health_status.items():
          if health['status'] != 'healthy':
              alert_operations_team(module, health['message'])

The gateway provides a robust foundation for inter-module communication while maintaining proper boundaries and dependencies in your modular monolith.