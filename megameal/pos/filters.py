import django_filters
from woms.models import Waiter
from koms.models import Staff


class WaiterFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Waiter
        fields = ["name"]


class ChefFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(lookup_expr="icontains")
    last_name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Staff
        fields = ("first_name", "last_name",)
