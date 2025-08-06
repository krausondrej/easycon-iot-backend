from rest_framework import serializers
from .models import Device

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'serial_number', 'created_at']
