from rest_framework import serializers
from koms.models import Order_content, Order_point_cred

class Order_point_cred_serializer(serializers.ModelSerializer):
    # creator = serializers.ReadOnlyField(source='creator.username')

    class Meta:
        model = Order_content
        fields = ("key","value")