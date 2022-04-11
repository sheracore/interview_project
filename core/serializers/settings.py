from rest_framework import serializers
from django.core.validators import validate_ipv4_address
from rest_framework.serializers import ValidationError

from core.models.system import System
from core.mixins import AsyncMixin
from core.tasks import set_splash


class SettingsSerializer(serializers.Serializer):
    logo = serializers.CharField(required=False, allow_null=True)
    max_file_size = serializers.IntegerField(required=False, allow_null=True)
    total_max_files_size = serializers.IntegerField(
        required=False, allow_null=True)
    mimetypes = serializers.ListField(required=False, allow_empty=True)
    extract = serializers.NullBooleanField(required=False)
    compress = serializers.NullBooleanField(required=False)
    ftp_host = serializers.CharField(required=False,
                                     validators=[validate_ipv4_address],
                                     allow_blank=True)
    ftp_user = serializers.CharField(required=False, allow_blank=True)
    ftp_pass = serializers.CharField(required=False, allow_blank=True)
    ftp_port = serializers.IntegerField(required=False, default=21)
    webdav_host = serializers.CharField(required=False, allow_blank=True)
    webdav_user = serializers.CharField(required=False, allow_blank=True)
    webdav_pass = serializers.CharField(required=False, allow_blank=True)
    delete_file_after_scan = serializers.BooleanField(required=False)
    clean_acceptance_index = serializers.FloatField(required=False)
    valid_acceptance_index = serializers.FloatField(required=False)
    log = serializers.BooleanField(required=False)
    log_http_url = serializers.URLField(required=False)
    log_http_method = serializers.ChoiceField(choices=['POST', 'PATCH'],
                                              required=False)
    log_http_headers = serializers.JSONField(required=False)

    ldap_server_uri = serializers.CharField(required=False, allow_blank=True)
    ldap_bind_dn = serializers.CharField(required=False, allow_blank=True)
    ldap_password = serializers.CharField(required=False, allow_blank=True)
    ldap_user_search = serializers.CharField(required=False, allow_blank=True)
    syslog = serializers.BooleanField(required=False)
    syslog_ip = serializers.CharField(required=False, allow_blank=True)
    syslog_port = serializers.IntegerField(required=False, default=514)
    syslog_protocol = serializers.ChoiceField(required=False, choices=['UDP', 'TCP'])
    log_file_path = serializers.CharField(required=False, allow_blank=True)

    email_host = serializers.CharField(required=False, allow_blank=True)
    email_user = serializers.CharField(required=False, allow_blank=True)
    email_password = serializers.CharField(required=False, allow_blank=True)
    email_port = serializers.IntegerField(required=False, default=587)
    email_imap_port = serializers.IntegerField(required=False, default=143)
    email_pop3_port = serializers.IntegerField(required=False, default=110)
    email_protocol = serializers.ChoiceField(choices=['POP3', 'IMAP'], required=False)

    def validate_valid_acceptance_index(self, value):
        if not 0 < value <= 1:
            raise ValidationError('not a valid choice')
        return value

    def validate_clean_acceptance_index(self, value):
        if not 0 < value <= 1:
            raise ValidationError('not a valid choice')
        return value

    def create(self, validated_data):
        System.update_settings(validated_data)
        return validated_data


class KioskSettingsSerializer(serializers.Serializer):
    pincode = serializers.CharField(required=False)
    logo = serializers.CharField(required=False, allow_null=True)
    max_file_size = serializers.IntegerField(required=False, allow_null=True)
    total_max_files_size = serializers.IntegerField(
        required=False, allow_null=True)
    mimetypes = serializers.ListField(required=False, allow_empty=True)
    extract = serializers.NullBooleanField(required=False)
    compress = serializers.NullBooleanField(required=False)
    printer_port = serializers.IntegerField(required=False, allow_null=True)
    printer_ip = serializers.CharField(
        validators=[validate_ipv4_address], required=False, allow_blank=True,
        allow_null=True)
    input_slots = serializers.ListField(required=False, allow_null=True,
                                        allow_empty=True)
    output_slots = serializers.ListField(required=False, allow_null=True,
                                         allow_empty=True)
    update_slots = serializers.ListField(required=False, allow_null=True,
                                         allow_empty=True)
    ftp_host = serializers.CharField(required=False,
                                     validators=[validate_ipv4_address],
                                     allow_blank=True)
    ftp_user = serializers.CharField(required=False, allow_blank=True)
    ftp_pass = serializers.CharField(required=False, allow_blank=True)
    ftp_port = serializers.IntegerField(required=False, default=21)
    webdav_host = serializers.CharField(required=False, allow_blank=True)
    webdav_user = serializers.CharField(required=False, allow_blank=True)
    webdav_pass = serializers.CharField(required=False, allow_blank=True)
    delete_file_after_scan = serializers.BooleanField(required=False)
    clean_acceptance_index = serializers.FloatField(required=False)
    valid_acceptance_index = serializers.FloatField(required=False)
    log = serializers.BooleanField(required=False)
    log_http_url = serializers.URLField(required=False, allow_blank=True)
    log_http_method = serializers.ChoiceField(choices=['POST', 'PATCH'],
                                              required=False)
    log_http_headers = serializers.JSONField(required=False)
    login_required = serializers.BooleanField(required=False)

    ldap_server_uri = serializers.CharField(required=False, allow_blank=True)
    ldap_bind_dn = serializers.CharField(required=False, allow_blank=True)
    ldap_password = serializers.CharField(required=False, allow_blank=True)
    ldap_user_search = serializers.CharField(required=False, allow_blank=True)
    syslog = serializers.BooleanField(required=False)
    syslog_ip = serializers.CharField(required=False, allow_blank=True)
    syslog_port = serializers.IntegerField(required=False, default=514)
    syslog_protocol = serializers.ChoiceField(required=False, choices=['UDP', 'TCP'])
    log_file_path = serializers.CharField(required=False, allow_blank=True)

    email_host = serializers.CharField(required=False, allow_blank=True)
    email_user = serializers.CharField(required=False, allow_blank=True)
    email_password = serializers.CharField(required=False, allow_blank=True)
    email_port = serializers.IntegerField(required=False, default=587)
    email_imap_port = serializers.IntegerField(required=False, default=143)
    email_pop3_port = serializers.IntegerField(required=False, default=110)
    email_protocol = serializers.ChoiceField(choices=['POP3', 'IMAP'], required=False)

    def validate_clean_acceptance_index(self, value):
        if not 0 < value <= 1:
            raise ValidationError('not a valid choice')
        return value

    def validate_valid_acceptance_index(self, value):
        if not 0 < value <= 1:
            raise ValidationError('not a valid choice')
        return value

    def create(self, validated_data):
        pre_saved_settings = System.get_settings()
        System.update_settings(validated_data)
        if 'logo' in validated_data and pre_saved_settings['logo'] != validated_data['logo']:
            AsyncMixin.perform_async(set_splash.si())

        return validated_data