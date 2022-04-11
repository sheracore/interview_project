from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from rest_framework.serializers import ValidationError

from core.models.system import System


class PinCodeSerializer(serializers.Serializer):
    pincode = serializers.CharField()

    def validate_pincode(self, value):
        if value != System.decrypt_password(System.get_settings()['pincode']):
            raise ValidationError(_('Incorrect pin code'))
        return value