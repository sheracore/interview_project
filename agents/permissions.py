from rest_framework.permissions import (BasePermission, IsAuthenticated)
from core.permissions import HasAPIKey


class AgentPermissions(BasePermission):

    def has_permission(self, request, view):
        ACTION_PERMS_MAPPING = {
            'create': 'agents.add_agent',
            'retrieve': 'agents.view_agent',
            'sys_info': 'agents.view_agent',
            'update': 'agents.change_agent',
            'partial_update': 'agents.change_agent',
            'destroy': 'agents.delete_agent',
            'stats': 'agents.view_agent_stats',
        }

        if request.user.is_superuser or HasAPIKey().has_permission(request, view):
            return True

        if view.action == 'list':
            return IsAuthenticated().has_permission(request, view)

        if view.action == 'avs':
            return request.user.has_perm('agents.change_agent') or \
                   request.user.has_perm('agents.add_agent')

        if view.action in {'update_from_disk', 'update_from_upload'}:
            return request.user.has_perm('agents.add_updatefile')

        return request.user.has_perm(

            ACTION_PERMS_MAPPING.get(view.action)

        ) or False


class UpdateFilePermissions(BasePermission):

    def has_permission(self, request, view):
        ACTION_PERMS_MAPPING = {
            'list': 'agents.view_updatefile',
            'retrieve': 'agents.view_updatefile',
            'create': 'agents.add_updatefile',
            'update': 'agents.change_updatefile',
            'partial_update': 'agents.change_updatefile',
            'destroy': 'agents.delete_updatefile',
        }

        if request.user.is_superuser or HasAPIKey().has_permission(request, view):
            return True

        return request.user.has_perm(
            ACTION_PERMS_MAPPING.get(view.action)
        ) or False
