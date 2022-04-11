import re
import calendar
from datetime import datetime
from redis.exceptions import ConnectionError as RedisConnectionError

from django.db.models import CharField, When, Count, Avg, F, Q, Subquery,\
    OuterRef, Case, Value, ObjectDoesNotExist
from django.db.models.functions import TruncMonth, Cast, Substr
from django.conf import settings
from rest_framework.viewsets import mixins, GenericViewSet
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.core.exceptions import ValidationError as django_validatior_error

from proj.celery import app as celery_app
from core.mixins import AsyncMixin
from scans.serializers import (FileSerializer, FromUrlSerializer,
                               FromPathSerializer, FromDiskSerializer,
                               ScanSerializer,
                               CopySerializer, SessionSerializer,
                               CleanupSerializer, ScanReportSerializer)
from scans.models.file import File
from scans.models.session import Session, TaskLog
from scans.models.scan import Scan
from scans.exceptions import InvalidPostScanOperation
from scans.permissions import SessionPermissions, FilePermissions, ScanPermissions
from scans.tasks import cleanup
from scans.filters import FileFilter
from agents.models import Agent

from core.validators import validate_date


class SessionViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     GenericViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [SessionPermissions]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.annotate(files_count=Count('files', filter=Q(
                files__parent=None)))

        return qs.order_by('-created_at')

    def retrieve(self, request, *args, **kwargs):
        res = super().retrieve(request, *args, **kwargs)
        progress = self.request.query_params.get('progress', 'True')

        if progress and progress.lower() == 'true':
            instance = self.get_object()
            try:
                data = instance.state()

            except RedisConnectionError as e:
                return Response(data={'detail': str(e)}, status=499)

            data.update(res.data)
            res.data = data
        return res


class FileViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  GenericViewSet,
                  AsyncMixin):
    scope = 'file'
    queryset = File.objects.order_by('-pk')
    serializer_class = FileSerializer
    filterset_class = FileFilter
    permission_classes = [FilePermissions]

    def get_queryset(self):
        qs = super().get_queryset()
        # newest = File.objects.filter(pk=OuterRef('pk')).order_by(
        #     '-session')
        # qs = qs.filter(session=Subquery(newest.values('session')[:1])).annotate(
        #     scan_progress=F('progress'),
        # )
        # if self.action in {'create', 'list', 'retrieve'}:
        #     newest = SessionFile.objects.filter(file=OuterRef('pk')).order_by('-created_at')
        #     qs = qs.annotate(
        #         session_id=Subquery(newest.values('session')[:1]),
        #         scan_progress=Subquery(newest.values('progress')[:1]),
        #         infected=Subquery(newest.values('infected')[:1]),
        #     )
        # elif self.action == 'sessions':
        #     qs = Session.objects.annotate(files_count=Count('files', filter=Q(files__file__parent=None))).order_by('-created_at')

        user = self.request.user

        if user.is_superuser or user.has_perm('scans.view_file') \
                or settings.I_AM_A_KIOSK:
            return qs

        elif user.is_anonymous:
            return qs.filter(user=None)

        else:
            return qs.filter(user=user)

    # def get_serializer_class(self):
    #     if self.action == 'list' and not self.request.query_params.get('session_id'):
    #         return SessionSerializer
    #
    #     else:
    #         return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        session_id = self.request.query_params.get('session_id')
        if session_id:
            if not re.match(r'\d+', session_id):
                return Response(data={'detail': 'Session id must be integer'},
                                status=status.HTTP_400_BAD_REQUEST)
            progress = self.request.query_params.get('progress', 'True')
            results = self.request.query_params.get('results', 'True')
            if results and results.lower() == 'true':
                res = super().list(request, *args, **kwargs)
            else:
                res = Response(data={}, status=status.HTTP_200_OK)

            if progress and progress.lower() == 'true':
                try:
                    session = Session.objects.get(pk=session_id)
                    data = session.state()
                except ObjectDoesNotExist:
                    return Response(data={'detail': 'Session not found'},
                                    status=status.HTTP_404_NOT_FOUND)

                except RedisConnectionError as e:
                    return Response(data={'detail': str(e)}, status=499)

                data.update(res.data)
                res.data = data
            return res
        else:
            return super().list(request, *args, **kwargs)

    @action(methods=['get'], detail=False)
    def sessions(self, request, pk=None):
        queryset = Session.objects.annotate(files_count=Count('files', filter=Q(
            files__parent=None))).order_by('-created_at')
        # queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SessionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SessionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def scans(self, request, pk=None):
        file = self.get_object()
        # queryset = file.scans.filter(
        #     serial=file.scanned_serial).order_by('-agent__created_at')
        newest = File.objects.filter(pk=OuterRef('file__pk')).order_by(
            '-session')
        queryset = Scan.objects.filter(
            file=file,
            file__session=Subquery(newest.values('session')[:1])
        ).order_by('-agent__created_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ScanSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ScanSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=True, permission_classes=[AllowAny])
    def scan(self, request, pk=None):
        instance = self.get_object()
        if instance.deleted:
            return Response({'detail': 'File has been deleted'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance, data=request.data,
                                         partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['post'], serializer_class=FromUrlSerializer,
            detail=False, url_path='url')
    def from_url(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.create(serializer.validated_data)
        return Response({'session_id': session.pk},
                        status=status.HTTP_201_CREATED)

    @action(methods=['post'], serializer_class=FromPathSerializer,
            detail=False, url_path='path')
    def from_path(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.create(serializer.validated_data)
        return Response({'session_id': session.pk}, status=status.HTTP_201_CREATED)

    @action(methods=['post'], serializer_class=FromDiskSerializer,
            detail=False, url_path='disk')
    def from_disk(self, request):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        session = serializer.create(serializer.validated_data)
        return Response({'session_id': session.pk}, status=status.HTTP_201_CREATED)

    @action(methods=['post'], serializer_class=FromDiskserializer,
            detail=False, url_path='disk')
    def from_disk(self, request):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        session = serializer.create(serializer.validated_data)
        return Response({'session_id': session.pk}, status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=False, serializer_class=CleanupSerializer)
    def cleanup(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_id = self.perform_async(cleanup.si(
            serializer.validated_data['days_older_than']),
            on_commit=False
        ).task_id
        return Response({'task_id': task_id}, status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, permission_classes=[AllowAny])
    def terminate(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            celery_app.control.revoke(session_id, terminate=True)
            # celery_app.control.cancel_consumer(queue=session_id)
            for task_log in TaskLog.objects.filter(session_id=session_id):
                celery_app.control.revoke(task_log.task_id, terminate=True)
                task_log.delete()

            return Response(data={'detail': 'Task terminated'},
                            status=status.HTTP_200_OK)
        except RedisConnectionError as e:
            return Response(data={'detail': str(e)}, status=499)

    @action(methods=['patch'], detail=False, url_path='postscan/print')
    def postscan_print(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not re.match(r'\d+', session_id):
            return Response(data={'detail': 'session_id querystring must be integer'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            session = Session.objects.get(pk=session_id)
            task_id = session.postscan_print()
            return Response(data={'detail': task_id})
        except ObjectDoesNotExist:
            return Response(data={'detail': 'Session not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except InvalidPostScanOperation as e:
            return Response(data={'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, serializer_class=CopySerializer,
            url_path='postscan/copy')
    def postscan_copy(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not re.match(r'\d+', session_id):
            return Response(data={'detail': 'session_id querystring must be integer'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = Session.objects.get(pk=session_id)
            task_id = session.postscan_copy(serializer.data['path'])
            return Response(data={'detail': task_id})
        except ObjectDoesNotExist:
            return Response(data={'detail': 'Session not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except InvalidPostScanOperation as e:
            return Response(data={'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, url_path='postscan/ftp')
    def postscan_ftp(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not re.match(r'\d+', session_id):
            return Response(data={'detail': 'session_id querystring must be integer'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            session = Session.objects.get(pk=session_id)
            task_id = session.postscan_ftp()
            return Response(data={'detail': task_id})
        except ObjectDoesNotExist:
            return Response(data={'detail': 'Session not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except InvalidPostScanOperation as e:
            return Response(data={'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, url_path='postscan/sftp')
    def postscan_sftp(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not re.match(r'\d+', session_id):
            return Response(data={'detail': 'session_id querystring must be integer'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            session = Session.objects.get(pk=session_id)
            task_id = session.postscan_sftp()
            return Response(data={'detail': task_id})
        except ObjectDoesNotExist:
            return Response(data={'detail': 'Session not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except InvalidPostScanOperation as e:
            return Response(data={'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False, url_path='postscan/webdav')
    def postscan_webdav(self, request):
        session_id = request.query_params.get('session_id')
        username = request.data.get('username', None)
        password = request.data.get('password', None)
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not re.match(r'\d+', session_id):
            return Response(data={'detail': 'session_id querystring must be integer'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            session = Session.objects.get(pk=session_id)
            task_id = session.postscan_webdav(username=username, password=password)
            return Response(data={'detail': task_id})
        except ObjectDoesNotExist:
            return Response(data={'detail': 'Session not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except InvalidPostScanOperation as e:
            return Response(data={'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['delete'], detail=False)
    def delete(self, request):
        session_id = self.request.query_params.get('session_id')
        if not session_id:
            return Response(data={'detail': 'session_id querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not re.match(r'\d+', session_id):
            return Response(data={'detail': 'session_id querystring must be integer'},
                            status=status.HTTP_400_BAD_REQUEST)
        Session.objects.filter(pk=session_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def search(self, request):
        search = self.request.query_params.get('key')
        if not search:
            return Response(data={'detail': '"key" querystring required'},
                            status=status.HTTP_400_BAD_REQUEST)
        chains = Q(files__info__md5=search) | Q(files__info__sha1=search) | Q(files__info__sha256=search) | Q(files__display_name=search)
        if isinstance(search, int):
            chains |= Q(pk=search)
        queryset = Session.objects.filter(chains)
        # queryset = self.get_queryset().filter(Q(session_id=search) | Q(md5=search) | Q(sha1=search) | Q(sha256=search) | Q(display_name=search))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SessionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SessionSerializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class ScanViewSet(mixins.ListModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.RetrieveModelMixin,
                  GenericViewSet):
    scope = 'scan'
    queryset = Scan.objects.order_by('-created_at')
    serializer_class = ScanSerializer
    permission_classes = [ScanPermissions]
    filter_fields = ('agent', 'file', 'file__session')

    @action(methods=['get'], detail=False)
    def stats(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total_scans = qs.count()
        today_scans = qs.filter(created_at__date=timezone.now().date()).count()

        interval_type = self.request.query_params.get('interval_type')
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')

        if interval_type == 'month':
            queryset = qs.annotate(
                month=Substr(
                    Cast(
                        TruncMonth('created_at'),
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
                queryset = queryset.filter(created_at__gte=start)

            if end:
                end = end + '-01'
                try:
                    end = validate_date(end)
                    weekday, days = calendar.monthrange(end.year, end.month)
                    end = datetime(end.year, end.month, days, 23, 59)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(created_at__lte=end)

        elif interval_type == 'year':
            queryset = qs.annotate(
                year=F('created_at__year')
            ).values('year').annotate(count=Count('pk')).order_by('-year')

            if start:
                start = start + '-01-01'
                try:
                    start = validate_date(start)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(created_at__gte=start)

            if end:
                end = end + '-12'
                try:
                    end = validate_date(end)
                    weekday, days = calendar.monthrange(end.year, end.month)
                    end = datetime(end.year, end.month, days, 23, 59)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(created_at__lte=end)
        else:
            queryset = qs.annotate(
                date=F('created_at__date')
            ).values('date').annotate(count=Count('pk')).order_by('-date')

            if start:
                try:
                    start = validate_date(start)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(created_at__gte=start)

            if end:
                try:
                    end = validate_date(end)
                except django_validatior_error as e:
                    raise ValidationError(str(e))
                queryset = queryset.filter(created_at__lte=end)

        # page = self.paginate_queryset(queryset)

        # if page is not None:
        #     res = self.get_paginated_response(page)
        #     res.data['total_scans'] = total_scans
        #     res.data['today_scans'] = today_scans
        #     return res
        res = Response({'results': queryset})
        res.data['total_scans'] = total_scans
        res.data['today_scans'] = today_scans
        return res

    @action(methods=['get'], detail=False, url_path='performance', url_name='performance')
    def performance(self, request):
        # get agent
        pk = self.request.query_params.get('agent')
        if not pk:
            return Response(data={'detail': 'agent is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            agent = Agent.objects.get(pk=pk)
        except Exception as ex:
            return Response(data={'detail': 'Agent not founded'},
                            status=status.HTTP_404_NOT_FOUND)

        # get all scan objects for a special agent and make average scan time for size range
        qs = Scan.objects.filter(agent=agent).annotate(
            size_range=Case(
                When(file__info__size__lte=10*1024*1024, then=Value('1Kb-10Mb')),
                When(file__info__size__lte=100*1024*1024, then=Value('10-100Mb')),
                When(file__info__size__lte=500*1024*1024, then=Value('100-500Mb')),
                When(file__info__size__lte=1000*1024*1024, then=Value('500Mb-1Gb')),
                When(file__info__size__lte=5*1000*1024*1024, then=Value('1-5Gb')),
                When(file__info__size__gt=5*1000*1024*1024, then=Value('5Gb')),
                # output_field=IntegerField(),
                )).values('size_range').annotate(avg_scan_time=Avg('scan_time'))
        return Response({'results': qs})

    @action(methods=['get'], detail=False, url_path='compare', url_name='compare')
    def compare_agents_avg_scan_time(self, request):
        qs = Agent.objects.annotate(avg_scan_time=Avg('scans__scan_time')).values('av_name', 'avg_scan_time')
        return Response({'results': qs})

    @action(serializer_class=ScanReportSerializer, methods=['post'], detail=False)
    def add_report(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qs = self.filter_queryset(self.get_queryset())
        instance = qs.report(**serializer.validated_data)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
