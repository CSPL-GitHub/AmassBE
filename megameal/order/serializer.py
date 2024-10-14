from rest_framework import serializers
from .models import *

# class Paymentserializers(serializers.ModelSerializer):
#     class Meta:
#         model= Payment
#         fields = "__all__"


class Orderserializers(serializers.ModelSerializer):
    class Meta:
        model= Order
        fields = "__all__"


class OriginalOrderserializers(serializers.ModelSerializer):
    class Meta:
        model= OriginalOrder
        fields = "__all__"


class OrderItemserializers(serializers.ModelSerializer):
    class Meta:
        model= OrderItem
        fields = "__all__"


# class Order_Modifiersserializers(serializers.ModelSerializer):
#     class Meta:
#         model= Order_Modifiers
#         fields = "__all__"

class Customerserializers(serializers.ModelSerializer):
    class Meta:
        model= Customer
        fields = "__all__"

class Addressserializers(serializers.ModelSerializer):
    class Meta:
        model= Address
        fields = "__all__"