import logging

from django.conf import settings
from rest_framework.permissions import (BasePermission,
                                        IsAdminUser, IsAuthenticated, AllowAny)
from core.serializers.captcha import RestCaptchaSerializer

logger = logging.getLogger('logger')


class HasAPIKey(BasePermission):

    def get_client_ip(self, request):
        return request.META.get('REMOTE_ADDR')

    def has_permission(self, request, view):
        from core.models.api import API
        request_api_key = request.META.get('HTTP_X_API_KEY')
        api = API.objects.filter(key=request_api_key).first()
        request_host = self.get_client_ip(request)
        if api:
            if api.owner.is_active:
                if api.allowed_hosts == [] or request_host in api.allowed_hosts:
                    return True

        return False


class IsAdminUserOrHasAPIKey(BasePermission):

    def has_permission(self, request, view):
        return IsAdminUser().has_permission(request, view) or \
               HasAPIKey().has_permission(request, view)


class CaptchaRequired(BasePermission):

    def has_permission(self, request, view):
        from core.models.api import API
        request_api_key = request.META.get('HTTP_X_API_KEY')
        api = API.objects.filter(key=request_api_key).first()
        if api and api.app_mode == 'screen':
            return True

        captcha_key = request.META.get('HTTP_X_CAPTCHA_KEY')
        captcha_value = request.META.get('HTTP_X_CAPTCHA_VALUE')
        captcha_data = {
            'captcha_key': captcha_key,
            'captcha_value': captcha_value,
        }
        captcha_serializer = RestCaptchaSerializer(data=captcha_data)
        captcha_serializer.is_valid(raise_exception=True)

        return True


class IsAuthenticatedOrHasAPIKeyWithCaptcha(BasePermission):

    def has_permission(self, request, view):
        if settings.DEBUG:
            condition = HasAPIKey().has_permission(request, view)
        else:
            condition = HasAPIKey().has_permission(request,
                                                   view) and CaptchaRequired().has_permission(
                request, view)
        return IsAuthenticated().has_permission(request, view) or condition


class SystemPermissions(BasePermission):

    def has_permission(self, request, view):
        if view.action == 'get_settings':
            return True
            # return HasAPIKey().has_permission(request, view)

        if view.action in {'shutdown', 'restart', 'unmount', 'pci_slots',
                           'disks', 'walk', 'check_printer', 'check_ftp',
                           'check_disk', 'defaultinterface'}:
            return settings.I_AM_A_KIOSK

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        if view.action in {'set_settings', 'get_mimetypes', 'set_mimetypes'}:
            return request.user.has_perm('users.change_app_settings')

        if view.action == 'info':
            return request.user.has_perm('users.view_sys_info')

        return False


class APIPermissions(BasePermission):

    def has_permission(self, request, view):
        return IsAuthenticated().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        ACTION_PERMS_MAPPING = {
            'retrieve': 'core.view_api',
            'update': 'core.change_api',
            'partial_update': 'core.change_api',
            'refresh': 'core.change_api',
            'destroy': 'core.delete_api',
        }

        if request.user.is_superuser:
            return True

        return obj.owner == request.user or request.user.has_perm(
            ACTION_PERMS_MAPPING.get(view.action)
        )


class MimeTypePermissions(BasePermission):

    def has_permission(self, request, view):
        ACTION_PERMS_MAPPING = {
            'create': 'core.add_mimetype',
            'list': 'core.view_mimetype',
            'retrieve': 'core.view_mimetype',
            'update': 'core.change_mimetype',
            'partial_update': 'core.change_mimetype',
            'destroy': 'core.delete_mimetype',
        }

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        return request.user.has_perm(ACTION_PERMS_MAPPING.get(view.action))


class VideoPermissions(BasePermission):

    def has_permission(self, request, view):
        ACTION_PERMS_MAPPING = {
            'create': 'core.add_video',
            'retrieve': 'core.view_video',
            'activation': 'core.change_video',
            'destroy': 'core.delete_video',
            'list': 'core.view_video',
        }


        if request.user.is_superuser:
            return True

        if view.action == 'current':
            return AllowAny().has_permission(request, view)

        return request.user.has_perm(
            ACTION_PERMS_MAPPING.get(view.action)
        ) or False


class AuditLogPermissions(BasePermission):

    def has_permission(self, request, view):
        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True
        #
        # if view.action == 'stats':
        #     return IsAuthenticated().has_permission(request, view)
        #
        return request.user.has_perm('core.view_auditlog') or False
