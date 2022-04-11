from django_filters.rest_framework import (FilterSet, BooleanFilter,
                                           NumberFilter)

from scans.models.file import File


class FileFilter(FilterSet):
    no_parent = BooleanFilter(method='no_parent_filter')
    session_id = NumberFilter(method='session_filter')
    mysterious = BooleanFilter(method='mysterious_filter')

    class Meta:
        model = File
        fields = ['parent', 'client_username', 'session', 'infected', 'valid']

    def no_parent_filter(self, queryset, name, value):
        return queryset.filter(parent__isnull=value)

    def mysterious_filter(self, queryset, name, value):
        return queryset.filter(infected__isnull=value, valid=True)

    def session_filter(self, queryset, name, value):
        return queryset.filter(session__pk=value)

