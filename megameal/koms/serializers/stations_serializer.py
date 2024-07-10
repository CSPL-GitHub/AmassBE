from rest_framework import serializers
from koms.models import Station

class Stations_serializer(serializers.ModelSerializer):
    # creator = serializers.ReadOnlyField(source='creator.username')
    # name = serializers.CharField(source='station_name')
    # colorCode = serializers.CharField(source='color_code')

    class Meta:
        model = Station
        fields = "__all__"

class StationsReadSerializer(serializers.ModelSerializer):
    """
    Serializer class for reading orders
    """
    name = serializers.CharField(source='station_name')
    colorCode = serializers.CharField(source='color_code')

    class Meta:
        model = Station
        fields = ('id','name','colorCode')