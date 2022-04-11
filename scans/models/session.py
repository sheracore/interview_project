import os
from celery.result import AsyncResult

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from core.models.mixins import DateMixin
from core.models.system import System
from core.mixins import AsyncMixin
from core.tasks import send_email
from scans.tasks import postscan_print, postscan_copy, \
    postscan_ftp, postscan_sftp, postscan_webdav
from scans.exceptions import InvalidPostScanOperation

User = get_user_model()


class SessionQuerySet(models.QuerySet):
    pass


class SessionManager(models.Manager, AsyncMixin):

    def get_queryset(self):
        return SessionQuerySet(self.model, using=self._db)


class Session(DateMixin, AsyncMixin):
    user = models.ForeignKey(User, related_name='sessions',
                             on_delete=models.SET_NULL, null=True,
                             editable=False)
    username = models.CharField(max_length=32, null=True)
    progress = models.FloatField(null=True, db_index=True)
    total = models.PositiveSmallIntegerField(null=True)
    counter = models.PositiveSmallIntegerField(null=True)
    current_path = models.CharField(max_length=1024, null=True)
    analyze_progress = models.FloatField(null=True)

    source_choices = (
        ('upload', _("Upload")),
        ('url', _("URL")),
        ('disk', _("Disk")),
        ('email', _("Email")),
    )
    source = models.CharField(choices=source_choices, max_length=32, null=True, blank=True)
    remote_addr = models.CharField(max_length=64, null=True)
    objects = SessionManager()

    class Meta:
        default_permissions = ['view', 'delete']

    def state(self):
        from scans.models.file import File
        async_result = AsyncResult(str(self.pk))

        if self.analyze_progress is None:
            analyze_title = _('Waiting to start reading files...')
        elif self.analyze_progress != 100:
            analyze_title = _('Reading files...')
        else:
            analyze_title = _('Reading files finished')

        if self.progress is None:
            scan_title = _('Waiting to start scanning...')
        elif self.progress != 100:
            scan_title = _('Scanning files...')
        else:
            scan_title = _('Scanning files finished')

        valid_count = File.objects.filter(session=self,
                                          parent=None, valid=True).count()
        invalid_count = (
                self.total - valid_count) if self.total else None
        scanned_qs = File.objects.filter(session=self,
                                         progress=100,
                                         parent=None, valid=True)
        infected_count = scanned_qs.filter(infected=True).count()
        clean_count = scanned_qs.filter(infected=False).count()
        unknown_count = scanned_qs.filter(infected=None, valid=True).count()

        data = {
            'session_id': self.pk,
            'started_at': self.created_at,
            'state': async_result.state,
            'progresses': {
                'analyze': {
                    'title': analyze_title,
                    'total': self.total,
                    'counter': self.counter,
                    'current_item': self.current_path,
                    'progress': self.analyze_progress
                },
                'scan': {
                    'title': scan_title,
                    'total': valid_count,
                    'counter': scanned_qs.count(),
                    'progress': self.progress
                }
            },
            'total': self.total,
            'invalid': invalid_count,
            'scanned': scanned_qs.count(),
            'infected': infected_count,
            'clean': clean_count,
            'mysterious': unknown_count,
            'complete': self.progress == 100 and self.analyze_progress == 100
        }

        return data

    def update_progress(self):
        with transaction.atomic():
            obj = Session.objects.select_for_update().filter(pk=self.pk).get()
            total_files = obj.files.filter(parent=None, valid=True).count()
            total_files_scanned = obj.files.filter(parent=None, progress=100,
                                                   valid=True).count()
            if total_files:
                obj.progress = round(100 * total_files_scanned/total_files, 1)
            elif obj.counter:
                obj.progress = 100
            obj.save()
        if obj.progress == 100 and self.source == 'email' and self.remote_addr:
            self.postscan_email()

    def postscan_email(self):
        from scans.models.scan import Scan
        from scans.serializers import ScanSerializer
        data = self.state()
        scans_queryset = Scan.objects.filter(file__session=self)
        serializer = ScanSerializer(scans_queryset, many=True)
        message = render_to_string('scans/scan_result.html', {'data': data, 'scans': serializer.data})
        send_email.delay(f'Scan Result session:{self.pk}', message, [self.remote_addr])

    def postscan_valid(self, raise_exception=True):
        try:
            is_valid = self.progress == 100
            if is_valid:
                return True
            elif raise_exception:
                raise InvalidPostScanOperation('Scan is not yet complete')
            else:
                return False
        except ValidationError as e:
            if raise_exception:
                raise InvalidPostScanOperation(str(e))
            else:
                return False

    def postscan_print(self, _async=True):
        self.postscan_valid()
        if _async:
            return self.perform_async(
                postscan_print.si(self.pk),
                on_commit=False
            ).task_id
        else:
            return postscan_print.si(self.pk)

    def postscan_copy(self, path, _async=True):
        self.postscan_valid()
        if not os.path.isdir(path):
            raise InvalidPostScanOperation(f'Invalid directory "{path}"')
        if _async:
            return self.perform_async(
                postscan_copy.si(self.pk, path),
                on_commit=False
            ).task_id
        else:
            return postscan_copy.si(self.pk, path)

    def postscan_ftp(self, _async=True):
        self.postscan_valid()
        success, detail = System.check_ftp()
        if not success:
            raise InvalidPostScanOperation(detail)
        if _async:
            return self.perform_async(
                postscan_ftp.si(self.pk),
                on_commit=False
            ).task_id
        else:
            return postscan_ftp.si(self.pk)

    def postscan_sftp(self, _async=True):
        self.postscan_valid()
        success, detail = System.check_sftp()
        if not success:
            raise InvalidPostScanOperation(detail)
        if _async:
            return self.perform_async(
                postscan_sftp.si(self.pk),
                on_commit=False
            ).task_id
        else:
            return postscan_sftp.si(self.pk)

    def postscan_webdav(self, _async=True, username=None, password=None):
        self.postscan_valid()
        success, detail = System.check_webdav()
        if not success:
            raise InvalidPostScanOperation(detail)
        if _async:
            return self.perform_async(
                postscan_webdav.si(self.pk, username, password),
                on_commit=False
            ).task_id
        else:
            return postscan_webdav.si(self.pk, username, password)


class TaskLog(DateMixin):
    session_id = models.CharField(max_length=64, db_index=True)
    task_id = models.CharField(max_length=64)

    class Meta:
        default_permissions = []
