import django_filters
from woms.models import Waiter, Hotal_Tables
from core.models import ProductCategory, Product, ProductModifierGroup
from order.models import Order_Discount
from koms.models import Stations, Staff


class WaiterFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Waiter
        fields = ["name"]


class HotelTableFilter(django_filters.FilterSet):
    floor = django_filters.NumberFilter(field_name="floor", lookup_expr="exact")

    class Meta:
        model = Hotal_Tables
        fields = ["floor"]


class ProductCategoryFilter(django_filters.FilterSet):
    categoryName = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = ProductCategory
        fields = ("categoryName",)


class ModifierGroupFilter(django_filters.FilterSet):
    categoryName = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = ProductModifierGroup
        fields = ("name",)


class DiscountCouponFilter(django_filters.FilterSet):
    discountName = django_filters.CharFilter(lookup_expr="icontains")
    discountCode = django_filters.CharFilter(lookup_expr="icontains")
    value = django_filters.NumberFilter()

    class Meta:
        model = Order_Discount
        fields = ("discountName", "discountCode", "value")


class StationFilter(django_filters.FilterSet):
    station_name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Stations
        fields = ("station_name",)


class ChefFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(lookup_expr="icontains")
    last_name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Staff
        fields = ("first_name", "last_name",)
