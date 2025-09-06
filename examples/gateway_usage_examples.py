"""
Gateway Usage Examples
=====================

This file contains practical examples of how to use the API Gateway
for inter-module communication in the Aura modular monolith.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from config.gateway import gateway
from config.service_registry import event_bus

logger = logging.getLogger(__name__)


# Example 1: Mental Health Module Using Gateway for User Validation
# =================================================================

class TherapySessionService:
    """Service that uses gateway to communicate with other modules."""

    def schedule_session(self, patient_id: int, therapist_id: int,
                        scheduled_at: datetime) -> Dict[str, Any]:
        """Schedule a therapy session with user validation."""

        # Method 1: Direct service access
        user_service = gateway.get_module_service('users', 'UserService')

        if not user_service:
            return {
                'success': False,
                'error': 'User service temporarily unavailable'
            }

        try:
            # Validate patient
            patient = user_service.get_user_by_id(patient_id)
            if not patient or not patient.get('is_active'):
                return {
                    'success': False,
                    'error': 'Invalid or inactive patient'
                }

            # Validate therapist using inter-module call (with dependency validation)
            therapist = gateway.inter_module_call(
                source_module='mentalhealth',
                target_module='users',
                service='UserService',
                method='get_user_by_id',
                therapist_id
            )

            if not therapist or not user_service.is_user_therapist(therapist_id):
                return {
                    'success': False,
                    'error': 'Invalid therapist'
                }

            # Create session (business logic)
            session = self._create_session(patient_id, therapist_id, scheduled_at)

            # Publish event for other modules
            event_bus.publish(
                'therapy_session.scheduled',
                {
                    'session_id': session['id'],
                    'patient_id': patient_id,
                    'therapist_id': therapist_id,
                    'scheduled_at': scheduled_at.isoformat()
                },
                'mentalhealth'
            )

            return {
                'success': True,
                'session': session
            }

        except ValueError as e:
            # This catches dependency validation errors
            logger.error(f"Module dependency error: {e}")
            return {
                'success': False,
                'error': 'Service communication error'
            }
        except Exception as e:
            logger.error(f"Unexpected error scheduling session: {e}")
            return {
                'success': False,
                'error': 'Internal error occurred'
            }

    def _create_session(self, patient_id: int, therapist_id: int,
                       scheduled_at: datetime) -> Dict[str, Any]:
        """Mock session creation."""
        return {
            'id': 123,
            'patient_id': patient_id,
            'therapist_id': therapist_id,
            'scheduled_at': scheduled_at,
            'status': 'pending'
        }


# Example 2: Notifications Module Responding to Events
# ====================================================

class NotificationService:
    """Service that handles notifications across modules."""

    def __init__(self):
        # Subscribe to events from other modules
        event_bus.subscribe(
            'therapy_session.scheduled',
            self.handle_session_scheduled,
            'notifications'
        )

        event_bus.subscribe(
            'user.registered',
            self.handle_user_registered,
            'notifications'
        )

    def handle_session_scheduled(self, event_data: Dict[str, Any]):
        """Handle therapy session scheduled event."""
        try:
            session_id = event_data.get('session_id')
            patient_id = event_data.get('patient_id')
            therapist_id = event_data.get('therapist_id')

            # Get user details through gateway
            user_service = gateway.get_module_service('users', 'UserService')
            if not user_service:
                logger.error("Cannot send session notifications: User service unavailable")
                return

            # Get user details
            patient = user_service.get_user_by_id(patient_id)
            therapist = user_service.get_user_by_id(therapist_id)

            if not patient or not therapist:
                logger.error(f"Cannot find users for session {session_id}")
                return

            # Send notifications
            self._send_session_confirmation_email(patient, session_id)
            self._send_session_alert_email(therapist, session_id)

            logger.info(f"Sent notifications for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to handle session scheduled event: {e}")

    def handle_user_registered(self, event_data: Dict[str, Any]):
        """Handle user registration event."""
        try:
            user_id = event_data.get('user_id')
            user_email = event_data.get('email')

            if user_id and user_email:
                self._send_welcome_email(user_email, user_id)
                logger.info(f"Sent welcome email to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to handle user registration event: {e}")

    def _send_session_confirmation_email(self, patient: Dict, session_id: int):
        """Send session confirmation email to patient."""
        print(f"📧 Sending confirmation email to {patient.get('email')} for session {session_id}")

    def _send_session_alert_email(self, therapist: Dict, session_id: int):
        """Send session alert email to therapist."""
        print(f"📧 Sending alert email to {therapist.get('email')} for session {session_id}")

    def _send_welcome_email(self, email: str, user_id: int):
        """Send welcome email to new user."""
        print(f"📧 Sending welcome email to {email} (user {user_id})")


# Example 3: Robust Service Calling with Error Handling
# =====================================================

class RobustServiceCaller:
    """Example of robust inter-module service calling."""

    @staticmethod
    def safe_get_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Safely get user with comprehensive error handling."""
        try:
            user_service = gateway.get_module_service('users', 'UserService')

            if not user_service:
                logger.warning("User service not available")
                return None

            user = user_service.get_user_by_id(user_id)
            return user

        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    @staticmethod
    def batch_get_users(user_ids: List[int]) -> Dict[int, Optional[Dict[str, Any]]]:
        """Get multiple users efficiently."""
        results = {}

        # Get service once for batch operation
        user_service = gateway.get_module_service('users', 'UserService')

        if not user_service:
            # Return None for all users if service unavailable
            return {uid: None for uid in user_ids}

        for user_id in user_ids:
            try:
                user = user_service.get_user_by_id(user_id)
                results[user_id] = user
            except Exception as e:
                logger.error(f"Error getting user {user_id}: {e}")
                results[user_id] = None

        return results

    @staticmethod
    def validate_user_permissions(user_id: int, required_permission: str) -> bool:
        """Validate user has required permission."""
        try:
            # Use inter-module call for critical security checks
            auth_service = gateway.get_module_service('users', 'AuthenticationService')

            if not auth_service:
                # Fail secure - deny if auth service unavailable
                return False

            permissions = auth_service.get_user_permissions(user_id)
            return required_permission in permissions

        except Exception as e:
            logger.error(f"Error checking permissions for user {user_id}: {e}")
            # Fail secure
            return False


# Example 4: Module Health Monitoring
# ===================================

class SystemHealthMonitor:
    """Monitor system health using gateway."""

    @staticmethod
    def check_all_modules() -> Dict[str, Any]:
        """Check health of all modules."""
        try:
            module_health = gateway.list_modules()

            healthy_count = sum(1 for health in module_health.values()
                              if health['status'] == 'healthy')
            total_count = len(module_health)

            overall_status = 'healthy' if healthy_count == total_count else 'degraded'
            if healthy_count == 0:
                overall_status = 'critical'

            return {
                'overall_status': overall_status,
                'healthy_modules': healthy_count,
                'total_modules': total_count,
                'modules': module_health,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    @staticmethod
    def check_specific_module(module_name: str) -> Dict[str, Any]:
        """Check health of a specific module."""
        try:
            health = gateway.get_module_health(module_name)
            return {
                'module': module_name,
                'health': health,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'module': module_name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    @staticmethod
    def get_module_dependencies() -> Dict[str, List[str]]:
        """Get dependency graph of all modules."""
        try:
            all_modules = gateway.registry.get_all_modules()
            dependencies = {}

            for module_name, config in all_modules.items():
                dependencies[module_name] = config.get('dependencies', [])

            return dependencies
        except Exception as e:
            logger.error(f"Error getting module dependencies: {e}")
            return {}


# Example 5: Event-Driven Billing Integration
# ===========================================

class BillingService:
    """Billing service that responds to therapy session events."""

    def __init__(self):
        # Subscribe to billing-relevant events
        event_bus.subscribe(
            'therapy_session.completed',
            self.handle_session_completed,
            'billing'
        )

    def handle_session_completed(self, event_data: Dict[str, Any]):
        """Handle completed therapy session for billing."""
        try:
            session_id = event_data.get('session_id')
            patient_id = event_data.get('patient_id')
            therapist_id = event_data.get('therapist_id')
            duration_minutes = event_data.get('duration_minutes', 60)

            # Get user details for billing
            user_service = gateway.get_module_service('users', 'UserService')
            if not user_service:
                logger.error("Cannot process billing: User service unavailable")
                return

            patient = user_service.get_user_by_id(patient_id)
            therapist = user_service.get_user_by_id(therapist_id)

            if not patient or not therapist:
                logger.error(f"Cannot find users for billing session {session_id}")
                return

            # Calculate charge based on therapist rate and session duration
            charge_amount = self._calculate_session_charge(therapist, duration_minutes)

            # Create billing record
            billing_record = self._create_billing_record(
                session_id, patient_id, therapist_id, charge_amount
            )

            # Publish billing event
            event_bus.publish(
                'billing.charge_created',
                {
                    'billing_id': billing_record['id'],
                    'session_id': session_id,
                    'patient_id': patient_id,
                    'amount': charge_amount
                },
                'billing'
            )

            logger.info(f"Created billing record for session {session_id}: ${charge_amount}")

        except Exception as e:
            logger.error(f"Failed to handle session completed event: {e}")

    def _calculate_session_charge(self, therapist: Dict[str, Any],
                                duration_minutes: int) -> float:
        """Calculate charge for therapy session."""
        # Get therapist's hourly rate (default $100/hour)
        hourly_rate = therapist.get('hourly_rate', 100.0)

        # Calculate pro-rated charge
        charge = (duration_minutes / 60.0) * hourly_rate

        return round(charge, 2)

    def _create_billing_record(self, session_id: int, patient_id: int,
                             therapist_id: int, amount: float) -> Dict[str, Any]:
        """Create billing record (mock implementation)."""
        return {
            'id': 456,
            'session_id': session_id,
            'patient_id': patient_id,
            'therapist_id': therapist_id,
            'amount': amount,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }


# Example 6: API Controller Using Gateway
# =======================================

class TherapySessionAPIController:
    """API controller that uses gateway for business operations."""

    def create_session(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create therapy session via API."""
        try:
            # Extract request data
            patient_id = request_data.get('patient_id')
            therapist_id = request_data.get('therapist_id')
            scheduled_at_str = request_data.get('scheduled_at')

            if not all([patient_id, therapist_id, scheduled_at_str]):
                return {
                    'success': False,
                    'error': 'Missing required fields'
                }

            scheduled_at = datetime.fromisoformat(scheduled_at_str)

            # Use therapy session service through gateway
            therapy_service = gateway.get_module_service(
                'mentalhealth',
                'TherapySessionService'
            )

            if not therapy_service:
                return {
                    'success': False,
                    'error': 'Therapy service temporarily unavailable'
                }

            # Schedule session
            result = therapy_service.schedule_session(
                patient_id, therapist_id, scheduled_at
            )

            return result

        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid data: {str(e)}'
            }
        except Exception as e:
            logger.error(f"API error creating session: {e}")
            return {
                'success': False,
                'error': 'Internal server error'
            }

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health for admin dashboard."""
        return SystemHealthMonitor.check_all_modules()


# Usage Examples
# ==============

def example_usage():
    """Demonstrate gateway usage patterns."""

    # Example 1: Schedule a therapy session
    print("=== Scheduling Therapy Session ===")
    therapy_service = TherapySessionService()
    result = therapy_service.schedule_session(
        patient_id=1,
        therapist_id=2,
        scheduled_at=datetime.now()
    )
    print(f"Session scheduling result: {result}")

    # Example 2: Check system health
    print("\n=== System Health Check ===")
    health = SystemHealthMonitor.check_all_modules()
    print(f"System health: {health['overall_status']}")
    print(f"Healthy modules: {health['healthy_modules']}/{health['total_modules']}")

    # Example 3: Robust user retrieval
    print("\n=== User Retrieval ===")
    user = RobustServiceCaller.safe_get_user(1)
    if user:
        print(f"User found: {user.get('email', 'unknown')}")
    else:
        print("User not found or service unavailable")

    # Example 4: Batch user operations
    print("\n=== Batch User Operations ===")
    users = RobustServiceCaller.batch_get_users([1, 2, 3])
    for user_id, user_data in users.items():
        status = "Found" if user_data else "Not found"
        print(f"User {user_id}: {status}")


if __name__ == '__main__':
    example_usage()
