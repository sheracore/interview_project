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


class CoreReadOnlyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'full_name')


class APISerializer(serializers.ModelSerializer):
    owner = CoreReadOnlyUserSerializer(read_only=True)
    allowed_hosts = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = API
        fields = '__all__'

    def generate_apikey(self):
        keygen = KeyGenerator(key_length=32)
        return keygen.generate()

    def create(self, validated_data):
        user = self.context['request'].user
        key = self.generate_apikey()
        instance = API.objects.create(
            owner=user,
            key=key,
            **validated_data
        )
        return instance