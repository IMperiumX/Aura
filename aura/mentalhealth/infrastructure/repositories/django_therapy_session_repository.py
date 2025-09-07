"""
Django implementation of TherapySessionRepository.
Adapts Django ORM to domain repository interface.
"""

from datetime import datetime

from django.utils import timezone

from aura.mentalhealth.domain.entities.therapy_session import SessionStatus
from aura.mentalhealth.domain.entities.therapy_session import SessionType
from aura.mentalhealth.domain.entities.therapy_session import TargetAudience
from aura.mentalhealth.domain.entities.therapy_session import TherapySession as TherapySessionEntity
from aura.mentalhealth.domain.repositories.therapy_session_repository import TherapySessionRepository
from aura.mentalhealth.models import TherapySession as DjangoTherapySession


class DjangoTherapySessionRepository(TherapySessionRepository):
    """Django ORM implementation of therapy session repository."""

    def save(self, therapy_session: TherapySessionEntity) -> TherapySessionEntity:
        """Save a therapy session."""
        if therapy_session.id:
            # Update existing
            django_session = DjangoTherapySession.objects.get(id=therapy_session.id)
            self._update_django_model(django_session, therapy_session)
        else:
            # Create new
            django_session = self._create_django_model(therapy_session)

        django_session.save()
        return self._to_domain_entity(django_session)

    def find_by_id(self, session_id: int) -> TherapySessionEntity | None:
        """Find a therapy session by ID."""
        try:
            django_session = DjangoTherapySession.objects.get(id=session_id)
            return self._to_domain_entity(django_session)
        except DjangoTherapySession.DoesNotExist:
            return None

    def find_by_therapist_id(self, therapist_id: int) -> list[TherapySessionEntity]:
        """Find all therapy sessions for a therapist."""
        django_sessions = DjangoTherapySession.objects.filter(
            therapist_id=therapist_id,
        ).order_by("-scheduled_at")

        return [self._to_domain_entity(session) for session in django_sessions]

    def find_by_patient_id(self, patient_id: int) -> list[TherapySessionEntity]:
        """Find all therapy sessions for a patient."""
        django_sessions = DjangoTherapySession.objects.filter(
            patient_id=patient_id,
        ).order_by("-scheduled_at")

        return [self._to_domain_entity(session) for session in django_sessions]

    def find_by_status(self, status: SessionStatus) -> list[TherapySessionEntity]:
        """Find therapy sessions by status."""
        django_sessions = DjangoTherapySession.objects.filter(
            status=status.value,
        ).order_by("-scheduled_at")

        return [self._to_domain_entity(session) for session in django_sessions]

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[TherapySessionEntity]:
        """Find therapy sessions within a date range."""
        django_sessions = DjangoTherapySession.objects.filter(
            scheduled_at__gte=start_date,
            scheduled_at__lte=end_date,
        ).order_by("scheduled_at")

        return [self._to_domain_entity(session) for session in django_sessions]

    def find_upcoming_sessions(
        self,
        therapist_id: int | None = None,
        patient_id: int | None = None,
    ) -> list[TherapySessionEntity]:
        """Find upcoming therapy sessions."""
        queryset = DjangoTherapySession.objects.filter(
            scheduled_at__gte=timezone.now(),
            status__in=[
                DjangoTherapySession.SessionStatus.PENDING,
                DjangoTherapySession.SessionStatus.ACCEPTED,
            ],
        )

        if therapist_id:
            queryset = queryset.filter(therapist_id=therapist_id)

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        django_sessions = queryset.order_by("scheduled_at")
        return [self._to_domain_entity(session) for session in django_sessions]

    def find_active_sessions(self) -> list[TherapySessionEntity]:
        """Find currently active therapy sessions."""
        django_sessions = DjangoTherapySession.objects.filter(
            started_at__isnull=False,
            ended_at__isnull=True,
        ).order_by("started_at")

        return [self._to_domain_entity(session) for session in django_sessions]

    def update(self, therapy_session: TherapySessionEntity) -> TherapySessionEntity:
        """Update a therapy session."""
        if not therapy_session.id:
            msg = "Cannot update a session without an ID"
            raise ValueError(msg)

        django_session = DjangoTherapySession.objects.get(id=therapy_session.id)
        self._update_django_model(django_session, therapy_session)
        django_session.save()

        return self._to_domain_entity(django_session)

    def delete(self, session_id: int) -> bool:
        """Delete a therapy session."""
        try:
            DjangoTherapySession.objects.get(id=session_id).delete()
        except DjangoTherapySession.DoesNotExist:
            return False
        else:
            return True

    def count_by_therapist(self, therapist_id: int, status: SessionStatus | None = None) -> int:
        """Count sessions by therapist and optionally by status."""
        queryset = DjangoTherapySession.objects.filter(therapist_id=therapist_id)

        if status:
            queryset = queryset.filter(status=status.value)

        return queryset.count()

    def count_by_patient(self, patient_id: int, status: SessionStatus | None = None) -> int:
        """Count sessions by patient and optionally by status."""
        queryset = DjangoTherapySession.objects.filter(patient_id=patient_id)

        if status:
            queryset = queryset.filter(status=status.value)

        return queryset.count()

    def _create_django_model(self, entity: TherapySessionEntity) -> DjangoTherapySession:
        """Create Django model from domain entity."""
        return DjangoTherapySession(
            session_type=entity.session_type.value,
            status=entity.status.value,
            summary=entity.summary,
            notes=entity.notes,
            scheduled_at=entity.scheduled_at,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            target_audience=entity.target_audience.value,
            therapist_id=entity.therapist_id,
            patient_id=entity.patient_id,
        )

    def _update_django_model(
        self,
        django_model: DjangoTherapySession,
        entity: TherapySessionEntity,
    ) -> None:
        """Update Django model with domain entity data."""
        django_model.session_type = entity.session_type.value
        django_model.status = entity.status.value
        django_model.summary = entity.summary
        django_model.notes = entity.notes
        django_model.scheduled_at = entity.scheduled_at
        django_model.started_at = entity.started_at
        django_model.ended_at = entity.ended_at
        django_model.target_audience = entity.target_audience.value
        django_model.therapist_id = entity.therapist_id
        django_model.patient_id = entity.patient_id

    def _to_domain_entity(self, django_model: DjangoTherapySession) -> TherapySessionEntity:
        """Convert Django model to domain entity."""
        return TherapySessionEntity(
            id=django_model.id,
            session_type=SessionType(django_model.session_type),
            status=SessionStatus(django_model.status),
            summary=django_model.summary,
            notes=django_model.notes,
            scheduled_at=django_model.scheduled_at,
            started_at=django_model.started_at,
            ended_at=django_model.ended_at,
            target_audience=TargetAudience(django_model.target_audience),
            therapist_id=django_model.therapist_id,
            patient_id=django_model.patient_id,
            created_at=django_model.created,
            updated_at=django_model.modified,
        )
