from rest_framework import serializers

from kiosks.models import Kiosk, ScanLog, KioskAuditLog


class KioskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kiosk
        fields = '__all__'


class ScanLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanLog
        fields = '__all__'
        extra_kwargs = {
            'display_name': {
                'allow_blank': True
            },
            'session_id': {
                'allow_blank': True
            },
            'av_name': {
                'allow_blank': True
            },
            'threats': {
                'allow_blank': True
            },
            'error': {
                'allow_blank': True
            },
            'user_name': {
                'allow_blank': True
            },
            'extension': {
                'allow_blank': True,
                'required': False
            },
            'md5': {
                'allow_blank': True,
                'required': False
            },
            'sha1': {
                'allow_blank': True,
                'required': False
            },
            'sha256': {
                'allow_blank': True,
                'required': False
            },
            'mimetype': {
                'allow_blank': True,
                'required': False
            }
        }
        depth = 1


class KioskAuditLogSerializer(serializers.ModelSerializer):
    additional_data = serializers.JSONField(required=False)

    class Meta:
        model = KioskAuditLog
        fields = '__all__'
        depth = 1
