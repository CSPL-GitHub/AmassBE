from rest_framework import serializers
from koms.models import Order_modifer


class OrderModifierWriterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order_modifer
        fields = '__all__'
