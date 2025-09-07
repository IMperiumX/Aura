# Aura - Modular Monolith Architecture

This document describes the modular monolith architecture implemented in the Aura mental health platform.

## Architecture Overview

Aura is built as a modular monolith where each module can follow its own architectural pattern while communicating through well-defined interfaces.

```text
┌─────────────────────────────────────────────────────┐
│                API Gateway                          │
│              (config/gateway.py)                    │
└─────────────────────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼───┐            ┌─────▼─────┐         ┌─────▼─────┐
│ Users │            │ Mental    │         │ Billing   │
│Module │            │ Health    │         │ Module    │
│       │            │ Module    │         │           │
└───────┘            └───────────┘         └───────────┘
```

## Module Structure

### 1. Users Module (`aura/users/`)

- **Architecture**: Layered Architecture
- **Responsibilities**: User authentication, profiles, role management
- **Structure**:

  ```bash
  users/
  ├── models.py          # Django models
  ├── services.py        # Business logic services
  ├── api/
  │   ├── views.py       # API endpoints
  │   └── serializers.py # Data serialization
  └── migrations/        # Database migrations
  ```

### 2. Mental Health Module (`aura/mentalhealth/`)

- **Architecture**: Clean Architecture
- **Responsibilities**: Therapy sessions, disorders, chatbot interactions
- **Structure**:

  ```bash
  mentalhealth/
  ├── models.py                    # Django models (legacy)
  ├── domain/                      # Business logic (Clean Architecture)
  │   ├── entities/               # Domain entities
  │   ├── repositories/           # Repository interfaces
  │   └── services/              # Domain services
  ├── application/                # Application layer
  │   ├── use_cases/             # Use cases
  │   └── interfaces/            # Application interfaces
  ├── infrastructure/            # Infrastructure layer
  │   └── repositories/          # Repository implementations
  └── api/                       # Presentation layer
      ├── views.py              # API endpoints
      ├── serializers.py        # Data serialization
      └── urls.py               # URL routing
  ```

## Clean Architecture in Mental Health Module

The mental health module follows clean architecture principles:

```text
┌─────────────────────────────────────────────────────┐
│                 Presentation Layer                  │
│              (api/views.py)                         │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                Application Layer                    │
│              (application/use_cases/)               │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                 Domain Layer                        │
│         (domain/entities/ & domain/services/)       │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│              Infrastructure Layer                   │
│           (infrastructure/repositories/)            │
└─────────────────────────────────────────────────────┘
```

### Key Components

1. **Entities** (`domain/entities/`): Core business objects with business logic
2. **Repositories** (`domain/repositories/`): Interfaces for data persistence
3. **Domain Services** (`domain/services/`): Complex business logic
4. **Use Cases** (`application/use_cases/`): Application-specific business rules
5. **Infrastructure** (`infrastructure/`): External concerns (Django ORM, APIs)
6. **Presentation** (`api/`): API endpoints and data transformation

## Inter-Module Communication

### 1. Service Registry

Located in `config/service_registry.py`, provides:

- Service discovery between modules
- Event-driven communication
- Loose coupling between modules

### 2. API Gateway

Located in `config/gateway.py`, provides:

- Centralized API routing
- Request/response transformation
- Module-to-module communication

### 3. Dependency Injection

Located in `config/dependency_injection.py`, provides:

- Service lifecycle management
- Dependency resolution
- Testability through interface injection

## Module Configuration

Modules are configured in `config/modules.py`:

```python
AURA_MODULES = {
    'mentalhealth': {
        'name': 'Mental Health',
        'api_prefix': 'mental-health',
        'architecture': 'clean',
        'dependencies': ['users'],
        'provides': ['TherapySessionService', 'DisorderService']
    },
    'users': {
        'name': 'User Management',
        'api_prefix': 'users',
        'architecture': 'layered',
        'dependencies': [],
        'provides': ['UserService', 'AuthenticationService']
    }
}
```

## API Structure

### Mental Health APIs

- `POST /api/mental-health/therapy-sessions/` - Schedule therapy session
- `POST /api/mental-health/therapy-sessions/{id}/start_session/` - Start session
- `POST /api/mental-health/therapy-sessions/{id}/end_session/` - End session
- `POST /api/mental-health/therapy-sessions/{id}/cancel_session/` - Cancel session
- `GET /api/mental-health/therapy-sessions/availability/` - Get therapist availability
- `GET /api/mental-health/therapy-sessions/statistics/` - Get session statistics
- `GET /api/mental-health/disorders/` - List disorders
- `GET /api/mental-health/disorders/search/` - Search disorders
- `GET /api/mental-health/chatbot-interactions/recent/` - Recent interactions

### User APIs

- `GET /api/users/` - List users
- `POST /api/users/` - Create user
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user

## Development Guidelines

### Adding a New Module

1. **Create module structure**:

   ```bash
   mkdir aura/newmodule
   mkdir aura/newmodule/api
   # Add other directories based on chosen architecture
   ```

2. **Update module configuration** in `config/modules.py`

3. **Implement services** and register them in the service registry

4. **Add API routes** to `config/api_router.py`

5. **Add to Django settings** in `LOCAL_APPS`

### Clean Architecture Guidelines

When implementing clean architecture:

1. **Dependencies flow inward**: Outer layers depend on inner layers, never the reverse
2. **Use interfaces**: Define repository and service interfaces in the domain layer
3. **Keep entities pure**: Domain entities should only contain business logic
4. **Use cases coordinate**: Application layer orchestrates domain operations
5. **Infrastructure is pluggable**: Database and external services are implementation details

### Inter-Module Communication (Service Registry)

1. **Use the service registry** for synchronous communication
2. **Use the event bus** for asynchronous notifications
3. **Avoid direct imports** between modules
4. **Define clear contracts** through interfaces

## Testing Strategy

- **Unit Tests**: Test domain logic in isolation
- **Integration Tests**: Test use cases with real repositories
- **API Tests**: Test endpoints and serialization
- **Module Tests**: Test inter-module communication

## Benefits

1. **Modularity**: Clear separation of concerns
2. **Scalability**: Easy to scale individual modules
3. **Maintainability**: Independent module development
4. **Testability**: Each module can be tested in isolation
5. **Flexibility**: Different architectural patterns per module
6. **Migration Path**: Easy transition to microservices if needed

## Future Enhancements

1. **Additional Modules**: Notifications, Billing, Analytics
2. **Event Sourcing**: For audit and analytics
3. **CQRS**: Separate read and write models
4. **Microservices Migration**: Extract modules to separate services
5. **API Versioning**: Version individual module APIs
