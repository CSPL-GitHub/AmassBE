from rest_framework import serializers

from koms.models import OrderHistory


class Order_History_serializer(serializers.ModelSerializer):
    # creator = serializers.ReadOnlyField(source='creator.username')

    class Meta:
        model = OrderHistory
        fields = '__all__'