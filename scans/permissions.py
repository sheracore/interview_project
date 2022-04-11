from django.conf import settings
from rest_framework.permissions import (BasePermission, IsAuthenticated,
                                        AllowAny)
from core.permissions import HasAPIKey, IsAuthenticatedOrHasAPIKeyWithCaptcha
from core.models.system import System


class SessionPermissions(BasePermission):

    def has_permission(self, request, view):
        is_kiosk = settings.I_AM_A_KIOSK

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        if view.action in {'list'}:
            return IsAuthenticated().has_permission(request, view) or HasAPIKey().has_permission(request, view) or is_kiosk

        if view.action == 'destroy':
            return request.user.has_perm('scans.delete_session')  # for multiple files with session_id

        return True

    def has_object_permission(self, request, view, obj):

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        if view.action in {'retrieve'}:
            return AllowAny().has_object_permission(request, view, obj)

        return False


class FilePermissions(BasePermission):

    def has_permission(self, request, view):
        is_kiosk = settings.I_AM_A_KIOSK

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        if view.action in {'list', 'sessions', 'search'}:
            return IsAuthenticated().has_permission(request, view) or HasAPIKey().has_permission(request, view) or is_kiosk

        if view.action == 'from_path':
            return request.user.has_perm('scans.add_file_from_path')

        if view.action == 'cleanup':
            return request.user.has_perm('scans.cleanup')

        if view.action in {'create', 'from_url'}:
            return IsAuthenticatedOrHasAPIKeyWithCaptcha().has_permission(request, view)

        if view.action in {'postscan_copy', 'postscan_print',
                           'postscan_ftp', 'from_disk'}:
            _settings = System.get_settings()
            login_required = _settings.get('login_required')
            if login_required:
                return IsAuthenticated().has_permission(request, view) and is_kiosk
            return is_kiosk

        if view.action == 'delete':
            return request.user.has_perm('scans.delete_files')  # for multiple files with session_id

        return True

    def has_object_permission(self, request, view, obj):

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        if view.action in {'retrieve', 'scans', 'scan'}:
            return AllowAny().has_object_permission(request, view, obj)

        if view.action == 'destroy':
            return request.user.has_perm('scans.delete_file')

        if view.action == 'copy_to_disk':
            return AllowAny().has_object_permission(request, view, obj)

        return False


class ScanPermissions(BasePermission):

    def has_permission(self, request, view):
        is_kiosk = settings.I_AM_A_KIOSK

        if request.user.is_superuser or HasAPIKey().has_permission(request,
                                                                   view):
            return True

        if view.action == 'list':
            return request.user.has_perm('scans.view_scan')

        if view.action == 'stats':
            IsAuthenticated().has_permission(request,
                                             view) or HasAPIKey().has_permission(
                request, view) or is_kiosk
            return True
            # return request.user.has_perm('scans.view_stats')

        if view.action == 'destroy':
            return request.user.has_perm('scans.delete_scan')

        if view.action == 'retrieve':
            return request.user.has_perm('scans.view_scan')

        if view.action == 'compare_agents_avg_scan_time':
            return request.user.has_perm('scans.view_compare')

        if view.action == 'performance':
            return request.user.has_perm('scans.view_performance')

        return False
