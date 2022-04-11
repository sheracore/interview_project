from django.conf import settings
from django.contrib.auth.models import ContentType
from django.contrib.auth.models import Group
from django.db.models import Count
from django.contrib.auth import get_user_model


from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.viewsets import ModelViewSet

from users.permissions import (UserPermissions, PermissionPermissions,
                               GroupPermission)
from users.serializers import (ChangePasswordSerializer,
                               MeSerializer, UserSerializer,
                               ContentTypeSerializer, GroupSerializer)

from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

import logging
logger = logging.getLogger(__name__)


User = get_user_model()


class UserViewSet(ModelViewSet):
    queryset = User.objects.order_by('-date_joined').prefetch_related('groups')
    filter_fields = '__all__'
    ordering_fields = '__all__'
    search_fields = ('username', 'email', 'full_name', )
    permission_classes = [UserPermissions]

    def get_serializer_class(self):
        if self.action == 'me':
            return MeSerializer

        elif self.action == 'change_password':
            return ChangePasswordSerializer

        else:
            return UserSerializer

    def perform_destroy(self, instance):
        logger.info({
            'action': 'user_destroy',
            'additional_data': {
                'username': instance.username,
                'full_name': instance.full_name,
                'email': instance.email,
                'phone_number': instance.phone_number,
                'is_superuser': instance.is_superuser,
                'is_staff': instance.is_staff,
                'is_active': instance.is_active,
                'last_login': instance.last_login,
                'date_joined': instance.date_joined,
                'created_at': instance.created_at,
                'modified_at': instance.modified_at,
                'groups': [group.name for group in instance.groups.all()]
            }
        })
        instance.delete()

    def get_instance(self):
        return self.request.user

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(is_superuser=False)

        return qs

    @action(methods=['get', 'put', 'patch'],
            filter_backends=[],
            pagination_class=None,
            detail=False)
    def me(self, request, *args, **kwargs):
        """Retrieve, update or partial update the current user.

        get: retrieve the current user (authenticated user)

        put: update the current user (authenticated user)

        patch: partial update the current user (authenticated user)
        """
        user = self.get_instance()
        
        def user_logger():
            logger.info({
                'action': 'user_update',
                'username': user.username,
                'additional_data': {
                    'username': user.username,
                    'full_name': user.full_name,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                    'is_active': user.is_active,
                    'last_login': str(user.last_login),
                    'date_joined': str(user.date_joined),
                    'created_at': str(user.created_at),
                    'modified_at': str(user.modified_at),
                    'groups': [group.name for group in user.groups.all()]
                }
            })
        self.get_object = self.get_instance
        if request.method == 'GET':
            return self.retrieve(request, *args, **kwargs)

        elif request.method == 'PUT':
            user_logger()
            return self.update(request, *args, **kwargs)

        elif request.method == 'PATCH':
            user_logger()
            return self.partial_update(request, *args, **kwargs)

    @action(['patch'], url_path='me/change_password',
            url_name='change-my-password', detail=False)
    def change_password(self, request):
        """Change password of current user.

        patch: Change password of the current user (authenticated user)
        """
        if request.method == 'PATCH':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            self.request.user.set_password(serializer.data['new_password'])
            self.request.user.save()

            return Response(status=HTTP_204_NO_CONTENT)


class PermissionViewSet(GenericViewSet, mixins.ListModelMixin):
    scope = 'permission'
    queryset = ContentType.objects.exclude(permission=None).prefetch_related(
        'permission_set'
    ).filter(app_label__in=['core', 'kiosks', 'agents', 'sale', 'scans', 'users']
             ).exclude(model='api').distinct().order_by('model')
    serializer_class = ContentTypeSerializer
    permission_classes = [PermissionPermissions]
    search_fields = ('permission__codename', 'permission__name', 'model')
    filter_fields = ('app_label', 'model')

    def get_queryset(self):
        qs = super().get_queryset()
        if not settings.I_CAN_MANAGE_KIOSKS:
            return qs.exclude(app_label='kiosks')
        return qs


class GroupViewSet(ModelViewSet):
    scope = 'group'
    queryset = Group.objects.annotate(
        members_count=Count('user')).order_by('-pk')
    serializer_class = GroupSerializer
    filter_fields = ('name', )
    ordering_fields = ('members_count', 'id')
    permission_classes = [GroupPermission]
