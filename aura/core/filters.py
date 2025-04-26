from django.contrib.postgres.search import SearchQuery
from django.contrib.postgres.search import SearchVector
from django_filters import rest_framework as drf_filters

DEFAULT_SEARCH_FIELDS = []
class BaseFilterSet(drf_filters.FilterSet):
    def do_nothing(self, queryset, name, value):
        return queryset

    def get_query_param(self, k, default=None):
        if k in self.form.data:
            return self.form.cleaned_data[k]
        return default


class IDInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class UUIDInFilter(drf_filters.BaseInFilter, drf_filters.UUIDFilter):
    pass


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class FullTextSearchFilter(drf_filters.CharFilter):
    def __init__(self, *args, **kwargs):
        self.search_fields = kwargs.pop("search_fields", DEFAULT_SEARCH_FIELDS)
        super().__init__(*args, **kwargs)

    def filter(self, queryset, value):
        if not value:
            return queryset
        return queryset.annotate(
            search=SearchVector(*self.search_fields),
        ).filter(
            search=SearchQuery(value),
        )
