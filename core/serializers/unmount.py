from rest_framework import serializers


class UnMountSerializer(serializers.Serializer):
    devname = serializers.CharField()