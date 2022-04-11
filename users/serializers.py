import datetime
from copy import deepcopy

from django.contrib.auth.models import Permission, ContentType, Group
from django.contrib.auth import get_user_model, password_validation
from django.core import exceptions
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.serializers import (CharField, HyperlinkedRelatedField,
                                        HyperlinkedModelSerializer,
                                        ModelSerializer, Serializer,
                                        ValidationError)
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

User = get_user_model()


class NestedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'full_name')


class PermissionSerializer(ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'


class ContentTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    permissions = PermissionSerializer(source='permission_set', many=True)

    class Meta:
        model = ContentType
        fields = ('id', 'name', 'app_label', 'model', 'permissions')


class GroupSerializer(ModelSerializer):
    members_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('permissions'):
            representation['permissions'] = PermissionSerializer(
                instance.permissions.all(),
                many=True
            ).data
        return representation


class UserSerializer(ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='user-detail')
    inbox_url = HyperlinkedRelatedField(view_name='inbox-detail',
                                        source='inbox',
                                        read_only=True)

    class Meta:
        model = get_user_model()
        fields = [
            'url',
            'id',
            'username',
            'password',
            'full_name',
            'email',
            'phone_number',
            'is_superuser',
            'is_staff',
            'is_active',
            # 'is_deleted',
            'last_login',
            'date_joined',
            'created_at',
            'modified_at',
            'inbox_url',
            'groups'
        ]
        read_only_fields = [
            'last_login',
            'date_joined',
            'created_at',
            'modified_at',
            'is_superuser'
        ]
        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': False,
                'style': {'input_type': 'password'},
            }
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('groups'):
            representation['groups'] = GroupSerializer(
                instance.groups, many=True).data

        return representation

    def validate(self, data):
        if not self.context.get('request').user.is_superuser and \
                'groups' in data:
            raise PermissionDenied(_('Insufficient privilege to set groups.'))
        password = data.get('password')
        if password:
            copy = deepcopy(data)
            copy.pop('groups', None)
            user = self.instance if self.instance else User(**copy)
            errors = dict()
            try:
                password_validation.validate_password(password, user=user)

            except exceptions.ValidationError as e:
                errors['password'] = list(e.messages)

            if errors:
                raise ValidationError(errors)
        return data

    def validate_is_active(self, value):
        if self.instance and self.instance.is_superuser and value is False:
            raise ValidationError('Super user cannot be deactivated')
        return value

    def create(self, validated_data):
        current_user = self.context.get('request', None).user
        password = validated_data.get('password')
        groups = validated_data.pop('groups', None)

        if password is None:
            raise ValidationError(
                _('"password" is required for creating a user'),
                code='required'
            )

        with transaction.atomic():
            user = User.objects.create_user(**validated_data)

            if groups is not None:
                user.groups.set(groups)

        logger.info({
            'action': 'user_create',
            'username': current_user.username,
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

        return user

    def update(self, instance, validated_data):
        current_user = self.context.get('request', None).user
        old_instance = deepcopy(instance)
        password = validated_data.get('password', None)
        groups = validated_data.pop('groups', None)

        with transaction.atomic():
            instance = super(UserSerializer, self).update(instance,
                                                          validated_data)

            if groups is not None:
                instance.groups.set(groups)

            if password:
                instance.set_password(password)

            instance.save()

            # if password is not None:
            #     instance.create_reset_password_token()

            logger.info({
                'action': 'user_update',
                'username': current_user.username,
                'additional_data': {
                    'username': instance.username,
                    'full_name': instance.full_name,
                    'email': instance.email,
                    'phone_number': instance.phone_number,
                    'is_superuser': instance.is_superuser,
                    'is_staff': instance.is_staff,
                    'is_active': instance.is_active,
                    'last_login': str(instance.last_login),
                    'date_joined': str(instance.date_joined),
                    'created_at': str(instance.created_at),
                    'modified_at': str(instance.modified_at),
                    'groups': [group.name for group in instance.groups.all()]
                }
            })
        return instance


class MeSerializer(HyperlinkedModelSerializer):
    """
    Serializer for User model with limited fields.

    "UserViewSet" view uses this serializer
    'users/me' endpoint uses this serializer.

    fields:
        'url', 'username' (required), 'full_name', 'email'.
    """
    inbox_url = HyperlinkedRelatedField(view_name='inbox-detail',
                                        source='inbox',
                                        read_only=True)
    perms = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'url',
            'username',
            'full_name',
            'email',
            'phone_number',
            'is_superuser',
            'is_staff',
            'is_active',
            # 'is_deleted',
            'last_login',
            'date_joined',
            'created_at',
            'modified_at',
            'inbox_url',
            'perms'
        ]
        read_only_fields = [
            'is_superuser',
            'is_staff',
            'is_active',
            # 'is_deleted',
            'last_login',
            'date_joined',
            'created_at',
            'modified_at',
        ]


class ChangePasswordSerializer(Serializer):
    """
    Serializer for changing password of a user.

    "UserViewSet" view uses this serializer
    'users/me/change_password' endpoint uses this serializer.

    fields (all_required):
        'current_password', 'new_password', 're_new_password'.
    """

    current_password = CharField(style={'input_type': 'password'})
    new_password = CharField(style={'input_type': 'password'})
    re_new_password = CharField(style={'input_type': 'password'})

    def validate_current_password(self, value):
        current_password = value
        is_password_valid = \
            self.context['request'].user.check_password(current_password)
        if is_password_valid:
            return value

        else:
            raise ValidationError(_('Invalid password'), code='invalid')

    def validate(self, data):
        user = self.context['request'].user or self.user
        new_password = data['new_password']
        re_new_password = data['re_new_password']
        if new_password == re_new_password:
            errors = dict()
            try:
                password_validation.validate_password(new_password, user=user)

            except exceptions.ValidationError as e:
                errors['new_password'] = list(e.messages)

            if errors:
                raise ValidationError(errors)

            logger.info({
                'action': 'user_pass_change',
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

            return data

        else:
            raise ValidationError(
                _('New password and its repeat do not match.'),
                code='not_equal'
            )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        current_user = self.context.get('request', None).user
        data = super().validate(attrs)
        data['refresh_expires_in'] = (settings.SIMPLE_JWT.get(
            'REFRESH_TOKEN_LIFETIME') - datetime.timedelta(seconds=10)).seconds
        data['access_expires_in'] = (settings.SIMPLE_JWT.get(
            'ACCESS_TOKEN_LIFETIME') - datetime.timedelta(seconds=10)).seconds

        logger.info({
            'action': 'user_login',
            'username': current_user.username,
            'additional_data': {
                'username': self.user.username,
                'full_name': self.user.full_name,
                'email': self.user.email,
                'phone_number': self.user.phone_number,
                'is_superuser': self.user.is_superuser,
                'is_staff': self.user.is_staff,
                'is_active': self.user.is_active,
                'last_login': str(self.user.last_login),
                'date_joined': str(self.user.date_joined),
                'created_at': str(self.user.created_at),
                'modified_at': str(self.user.modified_at),
                'groups': [group.name for group in
                           self.user.groups.all()]
            }
        })
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        data = super().validate(attrs)
        data['access_expires_in'] = (settings.SIMPLE_JWT.get(
            'ACCESS_TOKEN_LIFETIME') - datetime.timedelta(seconds=10)).seconds

        return data
