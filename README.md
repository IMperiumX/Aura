# Aura

<p align="center">
      <img src="https://github.com/IMperiumX/logos/blob/main/Aura/LOGO.png?raw=true" width=30% height=30%></img>
</p>

The virtual health and wellness platform aims to provide a comprehensive solution for individuals seeking personalized health and wellness guidance, support, and resources in a convenient digital format.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: Apache Software License 2.0

## Architecture

![aura arch](https://github.com/IMperiumX/logos/blob/main/Aura/aura_architecture.png?raw=true)
## Features

- **RESTful API**: Build and deploy a RESTful API for health and wellness services using Django REST framework.
- **Access Control**: Implement role-based access control to manage user permissions and data privacy.
- **Personalized Health Assessments**: Complete detailed health assessments to receive tailored recommendations for nutrition, fitness, mental health, and overall wellness.
- **Virtual Health Coaches**: Connect with certified health coaches, nutritionists, fitness trainers, and mental health professionals for personalized guidance and support.
- **Mental Health Support**: Engage with mindfulness exercises, stress management techniques, and mental health resources to promote emotional well-being and reduce anxiety.
- **User Management** with multiple roles (Patient, Therapist, etc..): Manage user accounts, roles, and permissions for patients, therapists, and administrators.
- **JWT** and **LDAP** Authentication: Secure user authentication and authorization using JSON Web Tokens and LDAP.
- **Therapy Session Management (Telehealth Consultations)**: Schedule, manage, and join virtual therapy sessions with mental health professionals.
- **Recommendation Engine** using RAG (Retrieval-Augmented Generation): Generate personalized health and wellness recommendations using RAG.
- **Admin Interface** for easy management: Manage users, health assessments, therapy sessions, and recommendations using the admin interface.

### Technology Stack

- Backend: Django (Python)
- Database: PostgreSQL with pgvector for similarity search
- AI/ML: LlamaIndex, Hugging Face Transformers
- Real-time Communication: Django Channels, WebSockets
- Authentication: JWT, LDAP integration
- Deployment: Docker, AWS

## Project Structure

The project follows a modular structure with the following main components:

- `aura/users`: User management and authentication
- `aura/assessments`: Health assessment models and logic
- `aura/mentalhealth`: Mental health disorder and therapy approach models
- `aura/communication`: Real-time communication features
- `aura/core`: Core services and utilities, including the AI recommendation engine

## Key Implementations

### AI-Powered Recommendation Engine

The `RecommendationEngine` class implements a sophisticated RAG (Retrieval-Augmented Generation) pipeline for providing personalized therapist recommendations and answering user queries.

### Health Assessment Model

The `Assessment` model captures detailed health assessment data, including risk levels, responses, and recommendations. It uses pgvector for efficient similarity searches.

### Telehealth Consultations

The project uses Django Channels and WebSockets to enable real-time communication features, crucial for the platform's chat and video call functionalities.

## Security and Compliance

- HIPAA and GDPR compliant data handling
- End-to-end encryption for all communications
- Secure authentication using JWT and LDAP integration
- Regular security audits and penetration testing

## Deployment and Scalability

- Containerized using Docker for easy deployment and scaling
- AWS infrastructure for robust and scalable cloud hosting
- Celery for handling background tasks and improving performance

## Settings

Moved to [settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

        mypy aura

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    coverage run -m pytest
    coverage html
    open htmlcov/index.html

#### Running tests with pytest

    pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html#sass-compilation-live-reloading).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd aura
celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd aura
celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd aura
celery -A config.celery_app worker -B -l info
```

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. If you choose to use [Mailpit](https://github.com/axllent/mailpit) when generating the project a local SMTP server with a web interface will be available.

1. [Download the latest Mailpit release](https://github.com/axllent/mailpit/releases) for your OS.

2. Copy the binary file to the project root.

3. Make it executable:

        chmod +x mailpit

4. Spin up another terminal window and start it there:

        ./mailpit

5. Check out <http://127.0.0.1:8025/> to see how it goes.

Now you have your own mail server running locally, ready to receive whatever you send it.

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.
