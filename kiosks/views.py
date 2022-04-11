import calendar

from datetime import datetime
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import CharField
from django.db.models.functions import TruncMonth, Cast, Substr
from django.db.models import Count, F
from django.utils import timezone
from django.core.exceptions import ValidationError as django_validatior_error

from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from core.views import ServerViewSet
from core.validators import validate_date

from kiosks.permissions import KioskPermissions, KioskAuditLogPermissions, ScanLogPermissions
from kiosks.serializers import KioskSerializer, KioskAuditLogSerializer, ScanLogSerializer
from kiosks.models import Kiosk, KioskAuditLog, ScanLog


User = get_user_model()


class KioskViewSet(ServerViewSet):
    queryset = Kiosk.objects.order_by('-created_at')
    serializer_class = KioskSerializer
    search_fields = ('title', 'ip', 'serial',)
    permission_classes = [KioskPermissions]

    # def perform_destroy(self, instance):
    #     with transaction.atomic():
    #         if instance.pt:
    #             PeriodicTask.objects.filter(pk=instance.pt.pk).delete()
    #         instance.delete()

    @action(methods=['get', 'post', 'put', 'patch', 'delete', 'head',
                     'options'], detail=True, url_path=r'(?P<url>[^.]+)')
    def remote(self, request, pk=None, url=None):
        instance = self.get_object()

        auth_header = request.headers.get('authorization-proxy')
        api_key_header = request.headers.get('x-api-key-proxy')
        captcha_key = request.headers.get('x-captcha-key')
        captcha_value = request.headers.get('x-captcha-value')
        content_type = request.headers.get('Content-Type')
        extra_headers = {}
        if auth_header:
            extra_headers['authorization'] = auth_header
        if api_key_header:
            extra_headers['x-api-key'] = api_key_header
        if captcha_key:
            extra_headers['x-captcha-key'] = captcha_key
        if captcha_value:
            extra_headers['x-captcha-value'] = captcha_value
        if content_type:
            extra_headers['Content-Type'] = content_type

        kwargs = {
            'extra_headers': extra_headers,
            'params': request.query_params
        }

        if content_type == 'application/json':
            kwargs['json'] = request.data
        else:
            kwargs['data'] = request.data

        kwargs['files'] = request.FILES

        data = instance.remote(url, request.method, **kwargs)

        return Response(data, status=status.HTTP_200_OK)

    # @action(methods=['post'], detail=True, url_path='scanlogs',
    #         serializer_class=ScanLogSerializer)
    # def add_scan_log(self, request, pk=None):
    #     kiosk = self.get_object()
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     with transaction.atomic():
    #         serializer.save(kiosk=kiosk, kiosk_title=kiosk.title)
    #         kiosk.last_update = timezone.now()
    #         kiosk.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path='auditlogs',
            serializer_class=KioskAuditLogSerializer)
    def add_audit_log(self, request, pk=None):
        kiosk = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            auditlog_instance = serializer.save(kiosk=kiosk, kiosk_title=kiosk.title)
            if auditlog_instance.action == 'scan':
                data = auditlog_instance.additional_data
                scanlog_serializer = ScanLogSerializer(data=data)
                scanlog_serializer.is_valid(raise_exception=True)
                scanlog_serializer.save(kiosk=kiosk, kiosk_title=kiosk.title)
            kiosk.last_update = timezone.now()
            kiosk.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class ScanLogViewSet(ReadOnlyModelViewSet):
    queryset = ScanLog.objects.order_by('-received_at', '-read')
    serializer_class = ScanLogSerializer
    search_fields = ('display_name', 'kiosk__title')
    filter_fields = ('kiosk',)
    ordering_fields = ('kiosk', )
    permission_classes = [ScanLogPermissions]

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        with transaction.atomic():
            fetched_pks = []
            for item in res.data['results']:
                fetched_pks.append(item['id'])
            ScanLog.objects.filter(pk__in=fetched_pks).update(read=True)
            return res

    @action(methods=['get'], detail=False)
    def stats(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total_scans = qs.count()
        today_scans = qs.filter(scanned_at=timezone.now().date()).count()

        interval_type = self.request.query_params.get('interval_type')
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')

        if interval_type == 'month':
            queryset = qs.annotate(
                month=Substr(
                    Cast(
                        TruncMonth('scanned_at'),
                        output_field=CharField()
                    ), 1, 7
                )
            ).values('month').annotate(count=Count('pk')).order_by('-month')

            if start:
                start = start + '-01'
                try:
                    start = validate_date(start)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(scanned_at__gte=start)

            if end:
                end = end + '-01'
                try:
                    end = validate_date(end)
                    weekday, days = calendar.monthrange(end.year, end.month)
                    end = datetime(end.year, end.month, days, 23, 59)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(scanned_at__lte=end)

        elif interval_type == 'year':
            queryset = qs.annotate(
                year=F('scanned_at__year')
            ).values('year').annotate(count=Count('pk')).order_by('-year')

            if start:
                start = start + '-01-01'
                try:
                    start = validate_date(start)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(scanned_at__gte=start)

            if end:
                end = end + '-12-01'
                try:
                    end = validate_date(end)
                    weekday, days = calendar.monthrange(end.year, end.month)
                    end = datetime(end.year, end.month, days, 23, 59)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(scanned_at__lte=end)
        else:
            queryset = qs.annotate(
                date=F('scanned_at__date')
            ).values('date').annotate(count=Count('pk')).order_by('-date')

            if start:
                try:
                    start = validate_date(start)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(scanned_at__gte=start)

            if end:
                try:
                    end = validate_date(end)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(scanned_at__lte=end)

        # page = self.paginate_queryset(queryset)
        #
        # if page is not None:
        #     res = self.get_paginated_response(page)
        #     res.data['total_scans'] = total_scans
        #     res.data['today_scans'] = today_scans
        #     return res
        res = Response({'results': queryset})
        res.data['total_scans'] = total_scans
        res.data['today_scans'] = today_scans
        return res


class KioskAuditLogViewSet(ReadOnlyModelViewSet):
    queryset = KioskAuditLog.objects.order_by('-received_at')
    serializer_class = KioskAuditLogSerializer
    search_fields = ('kiosk_title', 'action', 'additional_data', 'message', 'username', 'remote_addr')
    filter_fields = ('kiosk', 'action')
    ordering_fields = ('kiosk',)
    permission_classes = [KioskAuditLogPermissions]

    # def list(self, request, *args, **kwargs):
    #     pass
        # res = super().list(request, *args, **kwargs)
        # with transaction.atomic():
        #     fetched_pks = []
        #     for item in res.data['results']:
        #         fetched_pks.append(item['id'])
        #     ScanLog.objects.filter(pk__in=fetched_pks).update(read=True)
        #     return res
