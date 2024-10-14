from rest_framework import serializers
from koms.models import UserSettings



class UserSettingReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = "__all__"