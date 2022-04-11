from rest_framework import serializers


class WalkSerializer(serializers.Serializer):
    path = serializers.CharField(required=True)