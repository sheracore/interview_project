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

cache = caches[api_settings.CAPTCHA_CACHE]


class RestCaptchaSerializer(serializers.Serializer):
    captcha_key = serializers.CharField(max_length=64)
    captcha_value = serializers.CharField(max_length=8, trim_whitespace=True)

    def validate(self, data):
        super(RestCaptchaSerializer, self).validate(data)
        cache_key = utils.get_cache_key(data['captcha_key'])

        if data['captcha_key'] in api_settings.MASTER_CAPTCHA:
            real_value = api_settings.MASTER_CAPTCHA[data['captcha_key']]
        else:
            real_value = cache.get(cache_key)

        if real_value is None:
            raise serializers.ValidationError(
                _('Invalid or expired captcha key'))

        cache.delete(cache_key)
        if data['captcha_value'].upper() != real_value:
            raise serializers.ValidationError(_('Invalid captcha value'))

        del data['captcha_key']
        del data['captcha_value']
        return data