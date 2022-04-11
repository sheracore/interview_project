import os
from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from rest_framework.serializers import ValidationError

from core.models.video import Video


class VideoSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()
    size = serializers.FloatField(read_only=True, source='file.size')

    class Meta:
        model = Video
        fields = '__all__'

    def get_filename(self, obj):
        try:
            return os.path.split(obj.file.path)[-1]
        except:
            return ''

    def validate_file(self, value):
        if value.size > settings.MAX_VIDEO_SIZE:
            raise ValidationError('File too large!')
        return value

    def create(self, validated_data):
        file = validated_data.get('file')
        is_active = validated_data.get('is_active')
        if is_active:
            with transaction.atomic():
                videos = Video.objects.select_for_update()
                videos.update(is_active=False)

        instance = Video.objects.create(file=file, is_active=is_active)
        return instance


class ActivationVideoSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()
    size = serializers.FloatField(read_only=True, source='file.size')
    is_active = serializers.BooleanField()

    class Meta:
        model = Video
        fields = '__all__'
        read_only_fields = ('file',)

    def get_filename(self, obj):
        try:
            return os.path.split(obj.file.path)[-1]
        except:
            return ''

    def update(self, instance, validated_data):
        is_active = validated_data.get('is_active', False)
        if is_active:
            with transaction.atomic():
                videos = Video.objects.select_for_update()
                videos.update(is_active=False)
        instance.is_active = is_active
        instance.save()
        return instance