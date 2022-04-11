from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated


class IsSuperUser(BasePermission):
    """
    Allows access only to admin (superuser!).
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_superuser


class UserPermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if view.action in {'me', 'change_password'}:
            return IsAuthenticated().has_permission(request, view)

        elif view.action in {'list'}:
            return request.user.has_perm('users.view_user')

        elif view.action in {'retrieve'}:
            return True

        elif view.action in {'create'}:
            return request.user.has_perm('users.add_user')

        elif view.action in {'update', 'partial_update'}:
            return True

        elif view.action in {'destroy'}:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if view.action == 'destroy':
            if obj.is_superuser:
                return False
            else:
                return request.user.has_perm(
                    'users.delete_user') or request.user == obj
        elif view.action == 'retrieve':
            return request.user.has_perm(
                'users.view_user') or request.user == obj

        elif view.action in {'update', 'partial_update'}:
            return request.user.has_perm(
                'users.change_user') or request.user == obj

        return True


class PermissionPermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if request.user.is_authenticated:
            user_permissions = set(
                request.user.perms.all().values_list(
                    'codename', flat=True))
            allowed_perms = {'add_group', 'change_group',
                             'delete_group', 'view_group'}
            if user_permissions and user_permissions.intersection(allowed_perms):
                return True

        return False


class GroupPermission(BasePermission):

    def has_permission(self, request, view):
        # ACTION_PERMS_MAPPING = {
        #     'list': 'auth.view_group',
        #     'retrieve': 'auth.view_group',
        #     'create': 'auth.add_group',
        #     'update':  'auth.change_group',
        #     'partial_update':  'auth.change_group',
        #     'destroy': 'auth.delete_group',
        # }

        return request.user.is_superuser
