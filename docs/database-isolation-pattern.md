# Database Isolation Pattern for Modular Monolith

This document explains the database isolation pattern implemented in Aura's modular monolith architecture. This pattern ensures true module independence by eliminating cross-module database dependencies while maintaining data integrity and performance.

## Overview

The database isolation pattern replaces traditional foreign key relationships between modules with simple ID references, enabling:

- **True Module Independence**: Each module can use separate databases or schemas
- **Independent Deployment**: Modules can be migrated and deployed independently
- **Flexible Data Storage**: Different modules can use different database technologies
- **Enhanced Security**: Sensitive data can be isolated in separate databases
- **Better Scalability**: Critical modules can have dedicated database resources

## Core Principles

### 1. No Cross-Module Foreign Keys

❌ **Before (Tight Coupling)**:
```python
# Mental Health Module
class TherapySession(models.Model):
    therapist = models.ForeignKey("users.Therapist", on_delete=models.CASCADE)
    patient = models.ForeignKey("users.Patient", on_delete=models.CASCADE)
    # ... other fields
```

✅ **After (Loose Coupling)**:
```python
# Mental Health Module
class TherapySession(models.Model):
    therapist_id = models.PositiveIntegerField(
        verbose_name="Therapist ID",
        help_text="ID of therapist from users module"
    )
    patient_id = models.PositiveIntegerField(
        verbose_name="Patient ID", 
        help_text="ID of patient from users module"
    )
    # ... other fields

    class Meta:
        indexes = [
            models.Index(fields=["therapist_id", "scheduled_at"]),
            models.Index(fields=["patient_id", "scheduled_at"]),
        ]
```

### 2. ID-Only References

All cross-module relationships use simple integer IDs instead of foreign keys:

```python
# Instead of: user = models.ForeignKey(User)
# Use: user_id = models.PositiveIntegerField()

# Instead of: category = models.ForeignKey("core.Category")  
# Use: category_id = models.PositiveIntegerField()
```

### 3. Module-Specific Databases

Each module can have its own database configuration:

```python
# config/database_configs.py
POSTGRES_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aura_core',
        # ... connection details
    },
    'users_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aura_users',
        # ... connection details
    },
    'mentalhealth_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aura_mentalhealth',
        # ... connection details
    },
    'billing_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aura_billing',
        # ... connection details
    }
}
```

## Implementation Guide

### Step 1: Update Models

Replace foreign keys with ID fields:

```python
# Before
class ChatbotInteraction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # ...

# After
class ChatbotInteraction(models.Model):
    user_id = models.PositiveIntegerField(
        verbose_name="User ID",
        help_text="ID of user from users module"
    )
    # ...
    
    class Meta:
        indexes = [
            models.Index(fields=["user_id", "-interaction_date"]),
        ]
```

### Step 2: Configure Database Routing

Set up database routing to direct each module to its specific database:

```python
# config/database_router.py
class ModularMonolithRouter:
    MODULE_DATABASES = {
        'users': 'users_db',
        'mentalhealth': 'mentalhealth_db',
        'billing': 'billing_db',
    }
    
    def db_for_read(self, model, **hints):
        module_name = self._get_module_name(model)
        return self.MODULE_DATABASES.get(module_name, 'default')
    
    def db_for_write(self, model, **hints):
        module_name = self._get_module_name(model)
        return self.MODULE_DATABASES.get(module_name, 'default')
```

### Step 3: Update Repository Patterns

Repository implementations handle cross-module data access through the API Gateway:

```python
class DjangoTherapySessionRepository:
    def find_with_user_details(self, session_id: int):
        # Get therapy session (local data)
        session = self.find_by_id(session_id)
        if not session:
            return None
            
        # Get user details through gateway (cross-module)
        try:
            from config.gateway import gateway
            therapist_data = gateway.inter_module_call(
                source_module='mentalhealth',
                target_module='users',
                service_name='user_service',
                method='get_therapist_by_id',
                data={'therapist_id': session.therapist_id}
            )
            
            patient_data = gateway.inter_module_call(
                source_module='mentalhealth',
                target_module='users',
                service_name='user_service', 
                method='get_patient_by_id',
                data={'patient_id': session.patient_id}
            )
            
            # Combine local and remote data
            return {
                'session': session,
                'therapist': therapist_data,
                'patient': patient_data
            }
        except Exception as e:
            # Handle cross-module communication failures gracefully
            return {
                'session': session,
                'therapist': {'id': session.therapist_id, 'error': str(e)},
                'patient': {'id': session.patient_id, 'error': str(e)}
            }
```

## Database Configuration Strategies

### Strategy 1: Separate Databases (Full Isolation)

Best for: Production environments with strict security requirements

```yaml
# docker-compose.yml
services:
  users-db:
    image: postgres:15
    environment:
      POSTGRES_DB: aura_users
    ports: ["5434:5432"]
      
  mentalhealth-db:
    image: postgres:15
    environment:
      POSTGRES_DB: aura_mentalhealth
    ports: ["5435:5432"]
      
  billing-db:
    image: postgres:15
    environment:
      POSTGRES_DB: aura_billing
    ports: ["5436:5432"]
```

### Strategy 2: Schema Separation (Intermediate Isolation)

Best for: Development and staging environments

```python
POSTGRES_SCHEMA_DATABASE = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aura',
        'OPTIONS': {
            'options': '-c search_path=public,users_schema,mentalhealth_schema,billing_schema'
        },
    }
}
```

### Strategy 3: Single Database (Development Only)

Best for: Local development and testing

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

## Data Consistency Patterns

### 1. Eventual Consistency

Use domain events for maintaining data consistency across modules:

```python
# Mental Health Module
class TherapySessionCreated:
    def __init__(self, session_id: int, therapist_id: int, patient_id: int):
        self.session_id = session_id
        self.therapist_id = therapist_id
        self.patient_id = patient_id

# Users Module Event Handler
def handle_therapy_session_created(event: TherapySessionCreated):
    # Update user statistics, send notifications, etc.
    user_service.increment_session_count(event.therapist_id)
    user_service.increment_session_count(event.patient_id)
```

### 2. Cross-Module Validation

Validate cross-module references during business operations:

```python
class ScheduleTherapySessionUseCase:
    def execute(self, request):
        # Validate therapist exists
        therapist = gateway.inter_module_call(
            'mentalhealth', 'users', 'user_service', 
            'get_therapist_by_id', {'id': request.therapist_id}
        )
        if not therapist:
            raise ValidationError("Therapist not found")
            
        # Validate patient exists  
        patient = gateway.inter_module_call(
            'mentalhealth', 'users', 'user_service',
            'get_patient_by_id', {'id': request.patient_id}
        )
        if not patient:
            raise ValidationError("Patient not found")
            
        # Create session with validated IDs
        session = TherapySession(
            therapist_id=request.therapist_id,
            patient_id=request.patient_id,
            # ... other fields
        )
        return self.repository.save(session)
```

## Migration Strategy

### Phase 1: Add ID Fields
```python
# Add new ID fields alongside existing FKs
class Migration(migrations.Migration):
    operations = [
        migrations.AddField('therapysession', 'therapist_id', 
                          models.PositiveIntegerField(null=True)),
        migrations.AddField('therapysession', 'patient_id', 
                          models.PositiveIntegerField(null=True)),
    ]
```

### Phase 2: Populate ID Fields
```python
# Data migration to populate ID fields from FKs
def populate_id_fields(apps, schema_editor):
    TherapySession = apps.get_model('mentalhealth', 'TherapySession')
    for session in TherapySession.objects.all():
        session.therapist_id = session.therapist_id if session.therapist else None
        session.patient_id = session.patient_id if session.patient else None
        session.save()
```

### Phase 3: Remove Foreign Keys
```python
# Remove FK constraints and fields
class Migration(migrations.Migration):
    operations = [
        migrations.RemoveField('therapysession', 'therapist'),
        migrations.RemoveField('therapysession', 'patient'),
        migrations.AlterField('therapysession', 'therapist_id', 
                            models.PositiveIntegerField()),
        migrations.AlterField('therapysession', 'patient_id', 
                            models.PositiveIntegerField()),
    ]
```

## Performance Considerations

### Indexing Strategy
```python
class Meta:
    indexes = [
        # Index on foreign ID fields for joins
        models.Index(fields=["therapist_id", "scheduled_at"]),
        models.Index(fields=["patient_id", "scheduled_at"]),
        models.Index(fields=["status", "scheduled_at"]),
        
        # Composite indexes for common queries
        models.Index(fields=["therapist_id", "status"]),
        models.Index(fields=["patient_id", "status"]),
    ]
```

### Caching Strategy
```python
class UserServiceCache:
    def get_user_by_id(self, user_id: int):
        cache_key = f"user:{user_id}"
        user = cache.get(cache_key)
        
        if not user:
            user = gateway.inter_module_call(
                'mentalhealth', 'users', 'user_service',
                'get_user_by_id', {'id': user_id}
            )
            cache.set(cache_key, user, timeout=300)  # 5 minutes
            
        return user
```

### Batch Loading
```python
def load_sessions_with_users(session_ids: list[int]):
    # Load all sessions first
    sessions = TherapySession.objects.filter(id__in=session_ids)
    
    # Extract unique user IDs
    user_ids = set()
    for session in sessions:
        user_ids.add(session.therapist_id)
        user_ids.add(session.patient_id)
    
    # Batch load users
    users = gateway.inter_module_call(
        'mentalhealth', 'users', 'user_service',
        'get_users_by_ids', {'ids': list(user_ids)}
    )
    users_by_id = {user['id']: user for user in users}
    
    # Combine data
    return [{
        'session': session,
        'therapist': users_by_id.get(session.therapist_id),
        'patient': users_by_id.get(session.patient_id)
    } for session in sessions]
```

## Testing Strategies

### Unit Testing
```python
class TestTherapySessionRepository:
    def test_save_session_with_user_ids(self):
        session = TherapySession(
            therapist_id=123,
            patient_id=456,
            session_type=SessionType.VIDEO,
            scheduled_at=datetime.now()
        )
        
        saved_session = self.repository.save(session)
        
        assert saved_session.therapist_id == 123
        assert saved_session.patient_id == 456
        assert saved_session.id is not None
```

### Integration Testing
```python
class TestCrossModuleIntegration:
    def test_schedule_session_validates_users(self):
        # Mock gateway responses
        with patch('config.gateway.gateway.inter_module_call') as mock_call:
            mock_call.side_effect = [
                {'id': 123, 'name': 'Dr. Smith'},  # therapist
                {'id': 456, 'name': 'John Doe'},   # patient
            ]
            
            request = ScheduleTherapySessionRequest(
                therapist_id=123,
                patient_id=456,
                session_type='video',
                scheduled_at=datetime.now()
            )
            
            result = self.use_case.execute(request)
            
            assert result.therapist_id == 123
            assert result.patient_id == 456
```

## Monitoring and Observability

### Health Checks
```python
def check_cross_module_connectivity():
    """Check if cross-module communication is working."""
    try:
        result = gateway.inter_module_call(
            'mentalhealth', 'users', 'user_service',
            'health_check', {}
        )
        return result.get('status') == 'healthy'
    except Exception:
        return False
```

### Metrics
```python
# Track cross-module call performance
def track_cross_module_call_metrics(source, target, method, duration, success):
    metrics.histogram('cross_module_call_duration', duration, tags={
        'source_module': source,
        'target_module': target, 
        'method': method,
        'success': success
    })
```

## Benefits

1. **Module Independence**: Modules can be deployed, scaled, and maintained independently
2. **Database Flexibility**: Each module can use the most appropriate database technology
3. **Security Isolation**: Sensitive data can be completely isolated
4. **Performance Optimization**: Critical modules can have dedicated database resources
5. **Simplified Testing**: Modules can be tested in isolation without complex database setups
6. **Easier Migration**: Individual modules can be migrated to microservices if needed

## Trade-offs

1. **No Database-Level Referential Integrity**: Must be enforced at application level
2. **Increased Complexity**: Cross-module queries require additional code
3. **Potential Inconsistency**: Data consistency must be managed through application logic
4. **Performance Overhead**: Cross-module calls add latency compared to JOINs

## Conclusion

The database isolation pattern is a crucial architectural decision that enables true modularity in a monolithic application. While it introduces some complexity, the benefits of module independence, security isolation, and deployment flexibility make it essential for building maintainable, scalable modular monoliths.

The pattern works best when combined with proper event-driven communication, caching strategies, and robust monitoring to ensure data consistency and optimal performance across module boundaries.