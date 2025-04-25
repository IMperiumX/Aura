from django_filters import rest_framework as drf_filters


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
