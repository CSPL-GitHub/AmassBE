from rest_framework import serializers
from .models import *



class Productserializers(serializers.ModelSerializer):
    class Meta:
         model =  Product
         fields = "__all__"


class productImageserializers(serializers.ModelSerializer):
     class Meta:
        model =  ProductImage
        fields = "__all__"


class Categoryserializers(serializers.ModelSerializer):
    class Meta:
        model= ProductCategory
        fields = "__all__"        

class ProductCategoryserializers(serializers.ModelSerializer):
    class Meta:
        model=  ProductCategoryJoint
        fields = "__all__"
                
class Modifierserializers(serializers.ModelSerializer):
    class Meta:
        model=  ProductModifier
        fields = "__all__"

class ModifierGroupserializers(serializers.ModelSerializer):
    class Meta:
        model=  ProductModifierGroup
        fields = "__all__"


class ProductModGroupserializers(serializers.ModelSerializer):
    class Meta:
        model=  ProductAndModifierGroupJoint
        fields = "__all__"


class ModifierModGroupserializers(serializers.ModelSerializer):
    class Meta:
        model=  ProductModifierAndModifierGroupJoint
        fields = "__all__"


class Vendorserializers(serializers.ModelSerializer):
    class Meta:
        model= Vendor
        fields = "__all__"


class Platformserializers(serializers.ModelSerializer):
    class Meta:
        model= Platform
        fields = "__all__"



class ProductOptionsserializers(serializers.ModelSerializer):
    class Meta:
        model= Product_Option
        fields = "__all__"


class Optionsserializers(serializers.ModelSerializer):
    class Meta:
        model= Product_Option_Value
        fields = "__all__"

