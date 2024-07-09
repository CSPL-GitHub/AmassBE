from rest_framework import serializers
from woms.models import Waiter, Floor, HotelTable
from pos.models import StoreTiming, Banner, CoreUserCategory, CoreUser, Department
from order.models import Order_Discount
from core.models import (
    ProductCategory,
    Product,
    ProductImage,
    ProductCategoryJoint,
    ProductAndModifierGroupJoint,
    ProductModifierGroup,
    ProductModifier,
)
from koms.models import Station, Staff



class StoreTImingSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreTiming
        fields = "__all__"


class WaiterSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context["request"].method in ["PUT", "PATCH"]:
            excluded_fields = ["vendorId"]
            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Waiter
        fields = (
            "id",
            "name",
            "phone_number",
            "email",
            "username",
            "password",
            "image",
            "is_waiter_head",
            "is_active",
            "vendorId",
        )


class FloorSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context["request"].method in ["PUT", "PATCH"]:
            excluded_fields = ["id", "vendorId", "table_count"]
            for field_name in excluded_fields:
                self.fields.pop(field_name)

    floorId = serializers.ReadOnlyField(source="id")
    table_count = serializers.SerializerMethodField(read_only=True)

    def get_table_count(self, floor):
        return floor.hoteltable_set.count()

    class Meta:
        model = Floor
        fields = ("id", "floorId", "name", "name_ar", "is_active", "table_count", "vendorId")


class HotelTableSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context["request"].method in ["PUT", "PATCH"]:
            excluded_fields = ["id", "vendorId", "waiterId", "floor", "guestCount"]
            for field_name in excluded_fields:
                self.fields.pop(field_name)

    tableId = serializers.IntegerField(source="id", read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    floorName = serializers.CharField(source="floor.name", read_only=True)

    class Meta:
        model = HotelTable
        fields = "__all__"


class ProductCategorySerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ["PUT", "PATCH"]:
            excluded_fields = ("vendorId",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "categoryStation",
            "categoryPLU",
            "categoryName",
            "categoryName_locale",
            "categoryDescription",
            "categoryDescription_locale",
            "categoryImageUrl",
            "vendorId",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('categoryImageUrl') is None:
            representation['categoryImageUrl'] = ""
        return representation


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "PLU",
            "productName",
            "productName_locale",
            "productDesc",
            "productDesc_locale",
            "productPrice",
            "productType",
            "active",
            "tag",
            "is_displayed_online",
            "vendorId",
        )


class ProductCategoryJointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategoryJoint
        fields = "__all__"


class ProductImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductModGroupJointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAndModifierGroupJoint
        fields = "__all__"


class ModifierGroupSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendorId",)
            
            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductModifierGroup
        fields = (
            'id', 'name', 'name_locale', 'modifier_group_description', 'modifier_group_description_locale',
            'PLU', 'min', 'max', 'active', 'vendorId'
        )


class ModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductModifier
        fields = "__all__"


class DiscountCouponModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendorId",)
            
            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order_Discount
        fields = (
            "id",
            "discountName",
            "discountCode",
            "value",
            "start",
            "end",
            "multiUse",
            "calType",
            "is_active",
            "vendorId"
        )


class StationModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendorId",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Station
        fields = (
            "id",
            "station_name",
            "client_id",
            "client_secrete",
            "tag",
            "isStation",
            "vendorId"
        )

class ChefModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendorId",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Staff
        fields = "__all__"


class BannerModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendor",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Banner
        fields = "__all__"


class CoreUserCategoryModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendor",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = CoreUserCategory
        fields = ("id", "name", "vendor")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['name'] = instance.name.split('_')[0]
        return data


class CoreUserModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendor",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = CoreUser
        extra_kwargs = {'password': {'write_only': True}}
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "current_address",
            "permanent_address",
            "username",
            "password",
            "profile_picture",
            "date_joined",
            "is_active",
            "is_staff",
            "groups",
            "vendor",
        )
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        if not instance.profile_picture:
            data['profile_picture'] = ''

        return data


class DepartmentModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context["request"].method in ("PUT", "PATCH",):
            excluded_fields = ("vendor",)

            for field_name in excluded_fields:
                self.fields.pop(field_name)

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = "__all__"
