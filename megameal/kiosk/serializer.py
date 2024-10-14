from .models import KioskOrderData
from rest_framework import serializers
# from models import KioskOrderData
class KiosK_create_order_serializer(serializers.ModelSerializer):
    class Meta:
        model=KioskOrderData
        fields='__all__'