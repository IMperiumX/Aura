==================
Architecture Overview
==================

The Aura platform is built using a **modular monolith architecture** that provides the benefits of microservices while maintaining the simplicity of a monolith.

.. contents::
   :local:
   :depth: 2

What is a Modular Monolith?
===========================

A modular monolith is an architectural style where:

- The application is deployed as a single unit (monolith)
- Code is organized into independent, loosely-coupled modules
- Each module has clear boundaries and responsibilities
- Modules communicate through well-defined interfaces
- Different architectural patterns can be used per module

Benefits
========

**Operational Simplicity**
  - Single deployment unit
  - Simplified monitoring and logging
  - No distributed system complexity
  - Easier local development

**Development Flexibility**
  - Independent module development
  - Different teams can own different modules
  - Each module can use different architectural patterns
  - Easy to enforce module boundaries

**Migration Path**
  - Can extract modules to microservices later
  - Gradual decomposition is possible
  - Low risk of over-engineering early

**Performance**
  - No network overhead between modules
  - Shared database transactions
  - Faster inter-module communication

Architecture Principles
=======================

1. **Module Independence**
   - Each module is self-contained
   - Modules don't directly import from other modules
   - Clear public APIs for each module

2. **Single Responsibility**
   - Each module handles one business domain
   - Clear ownership of data and functionality

3. **Interface-Based Communication**
   - Modules communicate through service interfaces
   - Event-driven architecture for loose coupling
   - API gateway for external communication

4. **Dependency Direction**
   - Dependencies flow toward the core domain
   - Infrastructure depends on business logic, not vice versa
   - Stable abstractions principle

Module Types
============

**Core Modules**
  - Users: Authentication and user management
  - Shared utilities and common functionality

**Business Modules**
  - Mental Health: Therapy sessions, disorders, chatbot
  - Billing: Payments and subscriptions
  - Notifications: Email, SMS, push notifications

**Infrastructure Modules**
  - Gateway: API routing and module coordination
  - Service Registry: Inter-module communication

System Architecture
===================

.. code-block:: text

   ┌─────────────────────────────────────────────┐
   │                API Gateway                  │
   │         (Routing & Coordination)            │
   └─────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌─────▼─────┐    ┌────▼────┐
   │  Users  │    │  Mental   │    │ Billing │
   │ Module  │    │  Health   │    │ Module  │
   │         │    │  Module   │    │         │
   └─────────┘    └───────────┘    └─────────┘
        │               │               │
   ┌────▼────┐    ┌─────▼─────┐    ┌────▼────┐
   │Database │    │ Database  │    │Database │
   │ Tables  │    │  Tables   │    │ Tables  │
   └─────────┘    └───────────┘    └─────────┘

Communication Patterns
======================

**Synchronous Communication**
  - Direct service calls through service registry
  - Request/response pattern
  - Used for data queries and commands

**Asynchronous Communication**
  - Event-driven messaging through event bus
  - Publish/subscribe pattern
  - Used for notifications and side effects

**API Gateway Pattern**
  - Centralized entry point for external clients
  - Request routing to appropriate modules
  - Cross-cutting concerns (auth, rate limiting)

Example Communication Flow
==========================

1. **Client Request**
   - Client sends POST to ``/api/mental-health/therapy-sessions/``

2. **API Gateway**
   - Gateway routes request to Mental Health module
   - Applies authentication and validation

3. **Mental Health Module**
   - Executes business logic using Clean Architecture
   - May call Users module for user validation

4. **Event Publishing**
   - Publishes "therapy_session_scheduled" event
   - Other modules can react to this event

5. **Response**
   - Returns response through gateway to client

Module Architectural Patterns
=============================

**Clean Architecture** (Mental Health Module)
  - Entities: Core business objects
  - Use Cases: Application-specific business rules
  - Repositories: Data access abstractions
  - Infrastructure: Framework and external services

**Hexagonal Architecture** (Notifications Module)
  - Core: Business logic
  - Ports: Interfaces for external communication
  - Adapters: Implementations of ports

**Layered Architecture** (Users Module)
  - Presentation: API endpoints
  - Business: Service layer
  - Data: Repository layer

Technology Stack
================

**Framework**
  - Django 4.x for web framework
  - Django REST Framework for APIs

**Database**
  - PostgreSQL for relational data
  - Redis for caching and sessions

**Communication**
  - Service Registry for service discovery
  - Event Bus for publish/subscribe
  - Dependency Injection for loose coupling

**Development**
  - Python 3.11+
  - Docker for containerization
  - pytest for testing

Migration to Microservices
==========================

When the time comes, modules can be extracted to microservices:

1. **Database Separation**
   - Split shared database by module boundaries
   - Implement eventual consistency where needed

2. **Service Extraction**
   - Convert module to standalone service
   - Replace in-process calls with HTTP/gRPC

3. **Data Migration**
   - Migrate module data to separate database
   - Implement data synchronization if needed

4. **Gradual Migration**
   - Extract one module at a time
   - Maintain backward compatibility
   - Monitor performance and reliability

Best Practices
==============

**Module Design**
  - Keep modules cohesive and focused
  - Minimize inter-module dependencies
  - Define clear public APIs

**Communication**
  - Prefer asynchronous communication
  - Handle failures gracefully
  - Implement circuit breakers for resilience

**Testing**
  - Test modules in isolation
  - Use contract testing for inter-module interfaces
  - Implement end-to-end tests for critical paths

**Monitoring**
  - Monitor module health individually
  - Track inter-module communication
  - Implement distributed tracing

This architecture provides a solid foundation that can evolve with your needs while maintaining the benefits of both monoliths and microservices.