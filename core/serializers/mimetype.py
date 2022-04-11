import os
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.cache import caches
from django.core.validators import validate_ipv4_address
from django.contrib.auth import get_user_model
from rest_framework.serializers import ValidationError
from rest_captcha.settings import api_settings
from rest_captcha import utils

from core.models.api import API
from core.models.system import System
from core.models.mimetype import MimeTypeCat, MimeType
from core.models.video import Video
from core.models.auditlog import AuditLog

from core.utils.api import KeyGenerator
from core.mixins import AsyncMixin
from core.tasks import set_splash


class ReadOnlyMimeTypeSerializer(serializers.ModelSerializer):
    extensions = serializers.JSONField()

    class Meta:
        model = MimeType
        exclude = ('cat',)


class MimeTypeCatSerializer(serializers.ModelSerializer):
    mimetypes = ReadOnlyMimeTypeSerializer(many=True, read_only=True)

    class Meta:
        model = MimeTypeCat
        fields = '__all__'


class MimeTypeSerializer(serializers.ModelSerializer):
    extensions = serializers.ListField(child=serializers.CharField(),
                                       allow_empty=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('cat'):
            representation['cat'] = MimeTypeCatSerializer(instance.cat).data
        return representation

    class Meta:
        model = MimeType
        fields = '__all__'