from rest_framework import serializers
from koms.models import Order

class Order_serializer(serializers.ModelSerializer):
    # creator = serializers.ReadOnlyField(source='creator.username')

    class Meta:
        model = Order
        fields = ('externalOrderId', 'arrival_time', 'order_status', 'order_note', 'order_type')

class OrderSerializerWriterSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = "__all__"