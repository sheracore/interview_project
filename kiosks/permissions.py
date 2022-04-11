from rest_framework.permissions import BasePermission, IsAuthenticated
from core.permissions import HasAPIKey


class KioskPermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if view.action == 'create':
            return request.user.has_perm('kiosks.add_kiosk')

        if view.action == 'list':
            return request.user.has_perm('kiosks.view_kiosk')

        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if view.action == 'remote':
            return request.user.has_perm('kiosks.remote')

        if view.action == 'destroy':
            return request.user.has_perm('kiosks.delete_kiosk')

        if view.action in {'partial_update', 'update'}:
            return request.user.has_perm('kiosks.change_kiosk')

        if view.action == 'retrieve':
            return request.user.has_perm('kiosks.view_kiosk')

        if view.action == 'add_audit_log':
            return HasAPIKey().has_permission(request, view)

        if view.action == 'add_audit_log':
            return HasAPIKey().has_permission(request, view)

        return False


class ScanLogPermissions(BasePermission):

    def has_permission(self, request, view):
        ACTION_PERMS_MAPPING = {
            'list': 'kiosks.view_scanlog',
            'retrieve': 'kiosks.view_scanlog',
            'create': 'kiosks.add_scanlog',
            'update': 'kiosks.change_scanlog',
            'partial_update': 'kiosks.change_scanlog',
            'destroy': 'kiosks.delete_scanlog',
        }

        if request.user.is_superuser:
            return True

        if view.action == 'stats':
            return IsAuthenticated().has_permission(request, view)

        return request.user.has_perm(
            ACTION_PERMS_MAPPING.get(view.action)
        ) or False


class KioskAuditLogPermissions(BasePermission):

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        return request.user.has_perm('kiosks.view_kioskauditlog') or False
