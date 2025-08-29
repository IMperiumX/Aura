# XXX: recuureces is not a field in TherapySession model we can use ORM agains!!
"""
patterns could be used tho
pattern = recurrence.Recurrence(
   rrules=[recurrence.Rule(recurrence.WEEKLY, byday=recurrence.MONDAY)],
   include_dtstart=False).between(
      datetime(2010, 1, 1, 0, 0, 0),
      datetime(2014, 12, 31, 0, 0, 0),
      dtstart=datetime(2010, 1, 1, 0, 0, 0),
      inc=True
   )
)
"""

from datetime import datetime

import recurrence
from django_filters import rest_framework as filters

from aura.mentalhealth.models import TherapySession


class RecurrenceFilter(filters.DateFromToRangeFilter):
    def filter(self, qs, value):
        if value in ([], (), {}, "", None):
            return qs

        try:
            date = datetime.strptime(value, "%Y-%m-%d").date()
            # using date object instead
            date = date.isoformat()

        except ValueError:
            return qs

        recurrences = qs.values_list("recurrences", flat=True)
        dtstart = ...
        dtend = ...
        IDs = [obj.id for obj in qs if obj.recurrences.between(dtstart, dtend)]
        # Filter rec available on the given date
        return qs.filter(id__in=IDs)


class RecurrenceDayOfWeekFilter(filters.DateFromToRangeFilter):
    def filter(self, qs, value):
        if value in ([], (), {}, "", None):
            return qs

        try:
            pass
        except ValueError:
            return qs

        recurrences = qs.values_list("recurrences", flat=True)

        pattern = ...

        return qs
        # Filter rec available on the given day of week


class RecurrenceFrequencyFilter(filters.MultipleChoiceFilter):
    def filter(self, qs, value):
        if value in ([], (), {}, "", None):
            return qs

        # Map string frequency to Recurrence constants
        frequency_map = {
            "daily": recurrence.DAILY,
            "weekly": recurrence.WEEKLY,
            "monthly": recurrence.MONTHLY,
            "yearly": recurrence.YEARLY,
        }

        if value not in frequency_map:
            return qs

        pattern = ...

        return qs


class TherapySessionFilter(filters.FilterSet):
    available_on = RecurrenceFilter()
    available_day = RecurrenceDayOfWeekFilter()
    recurrences_frequency = RecurrenceFrequencyFilter(
        choices=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
    )

    class Meta:
        model = TherapySession
        fields = [
            "status",
            "scheduled_at",
            "therapist",
            "patient",
            "session_type",
            "target_audience",
            "session_type",
            # custom filters
            "available_on",
            "available_day",
            "recurrences_frequency",
        ]
