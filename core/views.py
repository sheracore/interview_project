import os
from invoke.exceptions import UnexpectedExit

from redis.exceptions import ConnectionError as RedisConnectionError
from celery.result import AsyncResult
from rest_framework.viewsets import ModelViewSet
from rest_framework.viewsets import GenericViewSet, mixins
from rest_framework.viewsets import ViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.response import Response

from rest_framework.decorators import action
from rest_framework import status
from rest_framework.exceptions import (ValidationError, PermissionDenied,
                                       NotFound)
from rest_framework.permissions import AllowAny
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from proj.celery import app as celery_app
from core.mixins import AsyncMixin
from core.models.api import API
from core.models.system import System
from core.models.mimetype import MimeTypeCat, MimeType
from core.models.video import Video
from core.models.auditlog import AuditLog

from core.serializers.walk import WalkSerializer
from core.serializers.settings import SettingsSerializer
from core.serializers.settings import KioskSettingsSerializer
from core.serializers.api import APISerializer
from core.serializers.pincode import PinCodeSerializer
from core.serializers.unmount import UnMountSerializer
from core.serializers.mimetype import MimeTypeSerializer, MimeTypeCatSerializer
from core.serializers.interface import InterfaceListSerializer
from core.serializers.video import VideoSerializer, ActivationVideoSerializer
from core.serializers.auditlog import CoreAuditLogSerializer
from core.permissions import SystemPermissions, APIPermissions, \
    MimeTypePermissions, VideoPermissions, AuditLogPermissions
from django.core.cache import cache


class SystemViewSet(GenericViewSet):
    permission_classes = [SystemPermissions]
    filter_backends = []

    def get_queryset(self):
        return None

    def get_serializer_class(self):
        if self.action == 'set_settings':
            if settings.I_AM_A_KIOSK:
                return KioskSettingsSerializer
            else:
                return SettingsSerializer
        elif self.action == 'set_mimetypes':
            return MimeTypeSerializer
        else:
            return super().get_serializer_class()

    @action(methods=['get'], detail=False)
    def info(self, request):
        try:
            data = System.get_sys_info()
        except Exception as e:
            raise ValidationError(str(e))

        return Response(data=data, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False,
            serializer_class=PinCodeSerializer)
    def shutdown(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            System.poweroff()
            return Response(data={'detail': 'System shut down'})
        except Exception as e:
            raise ValidationError(str(e))

    @action(methods=['patch'], detail=False,
            serializer_class=PinCodeSerializer)
    def restart(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            System.reboot()
            return Response(data={'detail': 'System restarted'})
        except Exception as e:
            raise ValidationError(str(e))

    @action(methods=['patch'], detail=False,
            serializer_class=UnMountSerializer)
    def unmount(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            devname = serializer.validated_data['devname']
            unmounted = System.unmount(devname)
            state = cache.get(devname)
            if unmounted:
                return Response(status=status.HTTP_200_OK,
                                data=state)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data=state)
        except Exception as e:
            raise ValidationError(str(e))

    @action(methods=['get'], detail=False, url_path='settings',
            url_name='settings')
    def get_settings(self, request):
        return Response(status=status.HTTP_200_OK, data=System.get_settings())

    @get_settings.mapping.patch
    def set_settings(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK, data=System.get_settings())

    @action(methods=['get'], detail=False, url_path='pci-slots')
    def pci_slots(self, request):
        try:
            slots = System.get_pci_slots()
            return Response(data={'results': slots},
                            status=status.HTTP_200_OK)
        except Exception as ex:
            raise ValidationError(str(ex))

    @action(methods=['get'], detail=False, url_path='disks')
    def disks(self, request):
        use = self.request.query_params.get('use')
        try:
            devices = System.get_removable_disks(use)
        except (PermissionError, UnexpectedExit) as e:
            return Response(data={'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(data={'results': devices},
                        status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='disks/check',
            serializer_class=UnMountSerializer)
    def check_disk(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exists = System.check_disk(serializer.validated_data['devname'])
        return Response(data={'exists': exists}, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='disks/walk',
            serializer_class=WalkSerializer)
    def walk(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        path = serializer.data['path']

        if not os.path.exists(path):
            raise NotFound(_("Path not found"))

        if not os.path.isdir(path):
            raise NotFound(_('No such directory'))

        try:
            data = System.walk_disk(path)
        except PermissionError as ep:
            raise PermissionDenied(str(ep))
        except Exception as ex:
            raise ValidationError(str(ex))

        return Response(data, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='printer')
    def check_printer(self, request):
        success, detail = System.check_printer(raise_exception=False)
        if success:
            return Response(data={'detail': detail},
                            status=status.HTTP_200_OK)
        else:
            return Response(data={'detail': detail},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, url_path='ftp')
    def check_ftp(self, request):
        success, detail = System.check_ftp()
        if success:
            return Response(data={'detail': detail},
                            status=status.HTTP_200_OK)
        else:
            return Response(data={'detail': detail},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, url_path='webdav')
    def check_webdav(self, request):
        success, detail = System.check_webdav()
        if success:
            return Response(data={'detail': detail},
                            status=status.HTTP_200_OK)
        else:
            return Response(data={'detail': detail},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, url_path='ldap')
    def check_ldap(self, request):
        success, detail = System.check_ldap()
        if success:
            return Response(data={'detail': detail},
                            status=status.HTTP_200_OK)
        else:
            return Response(data={'detail': detail},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='interfaces',
            url_name='interfaces', serializer_class=InterfaceListSerializer)
    def get_interfaces(self, request):
        interfaces = System.list_interfaces()
        items = []
        for key, value in interfaces.items():
            item = {'interface': key, **value}
            items.append(item)

        return Response({'results': items},
                        status.HTTP_200_OK)

    @get_interfaces.mapping.patch
    def update_interfaces(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            System.update_interfaces(serializer.validated_data['content'])
        except PermissionError as e:
            return Response({'detail': str(e)},
                            status.HTTP_400_BAD_REQUEST)
        return Response({'results': System.list_interfaces()},
                        status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='defaultinterface',
            url_name='defaultinterface', serializer_class=PinCodeSerializer)
    def get_default_interface(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = System.get_default_interface()

        if data:
            return Response(data, status.HTTP_200_OK)
        else:
            return Response({'detail': _('No default interface found')},
                            status.HTTP_400_BAD_REQUEST)


class AuditLogViewSet(ReadOnlyModelViewSet):
    queryset = AuditLog.objects.order_by('-created_at')
    serializer_class = CoreAuditLogSerializer
    search_fields = ('id', 'action', 'additional_data', 'message', 'username', 'remote_addr')
    filter_fields = ('action',)
    ordering_fields = ('action',)
    permission_classes = [AuditLogPermissions]


class ServerViewSet(ModelViewSet, AsyncMixin):
    pass


class TaskViewSet(ViewSet):
    permission_classes = [AllowAny]
    lookup_field = 'task_id'

    def list(self, request, *args, **kwargs):
        i = celery_app.control.inspect()
        cat = self.request.query_params.get('cat')
        if not cat:
            return Response(data={'detail': 'cat query string is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        if cat not in {'registered', 'active', 'scheduled', 'reserved'}:
            return Response(
                data={
                    'detail': 'valid choices for cat are: ["registered", "active", "scheduled", "reserved"]'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = {}

        if cat == 'registered':
            results = i.registered()

        elif cat == 'active':
            results = i.active()

        elif cat == 'scheduled':
            results = i.scheduled()

        elif cat == 'reserved':
            results = i.reserved()

        return Response({'results': results})

    def retrieve(self, request, task_id=None):
        try:
            async_result = AsyncResult(task_id)
            info = async_result.info
            result = async_result.result
            if not isinstance(info, dict):
                info = str(info)
            if not isinstance(result, dict):
                result = str(result)
            data = {
                'task_id': async_result.task_id,
                'state': async_result.state,
                'ready': async_result.ready(),
                'result': result,
                'info': info
            }
        except RedisConnectionError as e:
            return Response(data={'detail': str(e)},
                            status=499)

        return Response(data=data, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=True)
    def terminate(self, request, task_id=None):
        try:
            celery_app.control.revoke(task_id, terminate=True)
            return Response(data={'detail': 'Task terminated'},
                            status=status.HTTP_200_OK)
            # if result.ready() and isinstance(result.result, TaskRevokedError):
            #     return Response(data={'detail': 'Task terminated'},
            #                     status=status.HTTP_200_OK)
            # else:
            #     return Response(data={'detail': 'Something happened and the task was not terminated.'},
            #                     status=status.HTTP_400_BAD_REQUEST)
        except RedisConnectionError as e:
            return Response(data={'detail': str(e)},
                            status=499)

    @action(methods=['patch'], detail=False)
    def terminateall(self, request):
        try:
            messages_count = celery_app.control.purge()
            return Response(
                data={'detail': f'{messages_count} messages were purged.'})
        except RedisConnectionError as e:
            return Response(data={'detail': str(e)},
                            status=499)


class APIViewSet(ModelViewSet):
    """
    Crud for api model
    """
    queryset = API.objects.all().select_related('owner').order_by('-pk')
    serializer_class = APISerializer
    permission_classes = [APIPermissions]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.has_perm('core.view_api') or user.has_perm('core.change_api') \
                or user.has_perm('core.delete_api'):
            return qs
        else:
            return qs.filter(owner=user)

    @action(methods=['patch'], detail=True)
    def refresh(self, request, pk=None):
        instance = self.get_object()
        key = instance.refresh()
        return Response({'key': key},
                        status=status.HTTP_200_OK)


class MimeTypeCatViewSet(ModelViewSet):
    """
    Crud for api model
    """
    queryset = MimeTypeCat.objects.all().order_by('-pk')
    serializer_class = MimeTypeCatSerializer
    permission_classes = [MimeTypePermissions]
    search_fields = ('name',)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'results': serializer.data})


class MimeTypeViewSet(ModelViewSet):
    """
    Crud for api model
    """
    queryset = MimeType.objects.all().select_related('cat').order_by('-pk')
    serializer_class = MimeTypeSerializer
    permission_classes = [MimeTypePermissions]
    search_fields = ('name',)
    order_fields = ('cat',)


class VideoViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                   mixins.ListModelMixin, GenericViewSet):
    queryset = Video.objects.order_by('-pk')
    serializer_class = VideoSerializer
    permission_classes = [VideoPermissions]

    @action(methods=['patch'], detail=True, serializer_class=ActivationVideoSerializer)
    def activation(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status.HTTP_200_OK)

    @action(methods=['get'], detail=False, serializer_class=VideoSerializer)
    def current(self, request):
        instance = Video.objects.filter(is_active=True).first()
        if not instance:
            return Response(data={'detail': _('No active video found')}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
