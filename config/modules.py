"""
Module configuration for the modular monolith.
Defines module boundaries and their configurations.
"""

from typing import Any

# Module configurations
AURA_MODULES: dict[str, dict[str, Any]] = {
    "mentalhealth": {
        "name": "Mental Health",
        "description": "Mental health services, therapy sessions, and disorders management",
        "api_prefix": "mental-health",
        "api_module": "aura.mentalhealth.api.urls",
        "services_module": "aura.mentalhealth.domain.services",
        "architecture": "clean",
        "boundaries": {
            "domain": "aura.mentalhealth.domain",
            "infrastructure": "aura.mentalhealth.infrastructure",
            "application": "aura.mentalhealth.application",
            "presentation": "aura.mentalhealth.api",
        },
        "dependencies": ["users"],  # Can depend on users module
        "provides": [
            "TherapySessionService",
            "DisorderService",
            "ChatbotService",
        ],
    },
    "users": {
        "name": "User Management",
        "description": "User authentication, profiles, and role management",
        "api_prefix": "users",
        "api_module": "aura.users.api.urls",
        "services_module": "aura.users.services",
        "architecture": "layered",
        "boundaries": {
            "models": "aura.users.models",
            "services": "aura.users.services",
            "api": "aura.users.api",
        },
        "dependencies": [],  # Core module with no dependencies
        "provides": [
            "UserService",
            "AuthenticationService",
            "ProfileService",
        ],
    },
    "notifications": {
        "name": "Notifications",
        "description": "Email, SMS, and push notification services",
        "api_prefix": "notifications",
        "api_module": "aura.notifications.api.urls",
        "services_module": "aura.notifications.services",
        "architecture": "hexagonal",
        "boundaries": {
            "core": "aura.notifications.core",
            "adapters": "aura.notifications.adapters",
            "ports": "aura.notifications.ports",
        },
        "dependencies": ["users"],
        "provides": [
            "EmailService",
            "SMSService",
            "PushNotificationService",
        ],
    },
    "billing": {
        "name": "Billing & Payments",
        "description": "Payment processing, billing, and subscription management",
        "api_prefix": "billing",
        "api_module": "aura.billing.api.urls",
        "services_module": "aura.billing.services",
        "architecture": "clean",
        "boundaries": {
            "domain": "aura.billing.domain",
            "infrastructure": "aura.billing.infrastructure",
            "application": "aura.billing.application",
            "presentation": "aura.billing.api",
        },
        "dependencies": ["users"],
        "provides": [
            "PaymentService",
            "BillingService",
            "SubscriptionService",
        ],
    },
}


# Module dependency validation
def validate_module_dependencies():  # noqa: C901
    """Validate that module dependencies are properly configured."""
    errors = []

    for module_name, config in AURA_MODULES.items():
        dependencies = config.get("dependencies", [])

        for dep in dependencies:
            if dep not in AURA_MODULES:
                errors.extend([f"Module '{module_name}' depends on unknown module '{dep}'"])

    # Check for circular dependencies (simple check)
    def has_circular_dep(module, visited, path):
        if module in path:
            return True
        if module in visited:
            return False

        visited.add(module)
        path.append(module)

        for dep in AURA_MODULES.get(module, {}).get("dependencies", []):
            if has_circular_dep(dep, visited, path):
                return True

        path.pop()
        return False

    for module_name in AURA_MODULES:
        if has_circular_dep(module_name, set(), []):
            errors.extend([f"Circular dependency detected involving module '{module_name}'"])

    return errors


# Architecture patterns for different modules
ARCHITECTURE_PATTERNS = {
    "clean": {
        "layers": ["domain", "application", "infrastructure", "presentation"],
        "dependencies": {
            "domain": [],
            "application": ["domain"],
            "infrastructure": ["domain", "application"],
            "presentation": ["application"],
        },
    },
    "hexagonal": {
        "components": ["core", "ports", "adapters"],
        "dependencies": {
            "core": [],
            "ports": ["core"],
            "adapters": ["core", "ports"],
        },
    },
    "layered": {
        "layers": ["models", "services", "api"],
        "dependencies": {
            "models": [],
            "services": ["models"],
            "api": ["services", "models"],
        },
    },
}
