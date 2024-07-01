from rest_framework import serializers
from .models import *



class Hotal_Tables_serializers(serializers.ModelSerializer):
    class Meta:
         model =  Hotal_Tables
         fields = "__all__"
