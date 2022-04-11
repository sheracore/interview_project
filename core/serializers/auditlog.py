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


class CoreAuditLogSerializer(serializers.ModelSerializer):
    additional_data = serializers.JSONField()

    class Meta:
        model = AuditLog
        fields = '__all__'
        depth = 1