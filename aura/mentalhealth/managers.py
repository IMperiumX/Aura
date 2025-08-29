from django.db import models
from django.utils import timezone


class TherapySessionQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(scheduled_at__gt=timezone.now())

    def past(self):
        return self.filter(scheduled_at__lte=timezone.now())

    def for_therapist(self, therapist):
        return self.filter(therapist=therapist)

    def for_patient(self, patient):
        return self.filter(patient=patient)

    def by_type(self, session_type):
        return self.filter(session_type=session_type)


class TherapySessionManager(models.Manager):
    def get_queryset(self):
        return TherapySessionQuerySet(self.model, using=self._db)

    def upcoming(self):
        return self.get_queryset().upcoming()

    def past(self):
        return self.get_queryset().past()

    def for_therapist(self, therapist):
        return self.get_queryset().for_therapist(therapist)

    def for_patient(self, patient):
        return self.get_queryset().for_patient(patient)

    def by_type(self, session_type):
        return self.get_queryset().by_type(session_type)


class TherapyApproachQuerySet(models.QuerySet):
    def search(self, query):
        return self.filter(
            models.Q(name__icontains=query) | models.Q(description__icontains=query),
        )


class TherapyApproachManager(models.Manager):
    def get_queryset(self):
        return TherapyApproachQuerySet(self.model, using=self._db)

    def search(self, query):
        return self.get_queryset().search(query)


class ChatbotInteractionQuerySet(models.QuerySet):
    def recent(self, days=7):
        return self.filter(
            interaction_date__gte=timezone.now() - timezone.timedelta(days=days),
        )

    def for_user(self, user):
        return self.filter(user=user)


class ChatbotInteractionManager(models.Manager):
    def get_queryset(self):
        return ChatbotInteractionQuerySet(self.model, using=self._db)

    def recent(self, days=7):
        return self.get_queryset().recent(days)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class DisorderQuerySet(models.QuerySet):
    def by_type(self, disorder_type):
        return self.filter(type=disorder_type)

    def with_symptom(self, symptom):
        return self.filter(symptoms__contains=[symptom])

    def with_cause(self, cause):
        return self.filter(causes__contains=[cause])


class DisorderManager(models.Manager):
    def get_queryset(self):
        return DisorderQuerySet(self.model, using=self._db)

    def by_type(self, disorder_type):
        return self.get_queryset().by_type(disorder_type)

    def with_symptom(self, symptom):
        return self.get_queryset().with_symptom(symptom)

    def with_cause(self, cause):
        return self.get_queryset().with_cause(cause)
