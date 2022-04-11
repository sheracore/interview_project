from django.db import models
from django.utils.translation import ugettext_lazy as _
import os

from core.models.mixins import DateMixin, UpdateModelMixin
from core.mixins import AsyncMixin
from core.fields import SafeCharField

from agents.models import Agent
from scans.tasks import perform_scan, scan_report
from scans.models.file import File

import logging
logger = logging.getLogger(__name__)


class AbstractScan(models.Model):
    av_name = SafeCharField(max_length=128)
    status_code = models.IntegerField(null=True, db_index=True)
    stdout = models.TextField(blank=True)
    scan_time = models.FloatField(null=True)
    infected_num = models.IntegerField(null=True, db_index=True)
    threats = models.CharField(max_length=512, null=True)
    error = models.TextField(null=True)

    class Meta:
        abstract = True


class BaseScan(AbstractScan, DateMixin):
    class Meta:
        abstract = True


class ScanQuerySet(models.QuerySet, AsyncMixin):

    def report(self, name):
        pk_list = list(self.values_list('pk', flat=True))
        obj = ScanReport.objects.create(name=name)
        self.perform_async(scan_report.si(pk_list, obj.pk))

        return obj


class ScanManager(models.Manager):
    def get_queryset(self):
        qs = ScanQuerySet(self.model)
        return qs


class Scan(BaseScan, UpdateModelMixin, AsyncMixin):
    agent = models.ForeignKey(Agent, related_name='scans',
                              editable=False, on_delete=models.SET_NULL,
                              null=True)
    file = models.ForeignKey(File, on_delete=models.CASCADE,
                             related_name='scans')

    objects = ScanManager()

    class Meta:
        verbose_name = _('Scan')
        verbose_name_plural = _('Scans')
        unique_together = ('agent', 'file')
        default_permissions = ['view', 'delete']
        permissions = [
            ('view_stats', 'Can view scan stats'),
            ('view_compare', 'Can view comparing agents average scan time'),
            ('view_performance', 'Can view performance of an agent')
        ]

    def perform(self, _async=True):
        if _async:
            self.perform_async(
                perform_scan.si(self.pk),
                session_id=self.file.session.pk
            )
        else:
            return perform_scan(self.pk)

    def log(self):
        data = {
            'user_name': self.file.username,
            'display_name': self.file.display_name,
            'size': self.file.info.size,
            'md5': self.file.info.md5,
            'sha1': self.file.info.sha1,
            'sha256': self.file.info.sha256,
            'ext_match': self.file.info.ext_match,
            'extension': self.file.info.extension,
            'mimetype': self.file.info.mimetype,
            'session_id': self.file.session.pk,
            'notes': self.file.notes,
            'deleted': self.file.deleted,
            'av_name': self.av_name,
            'status_code': self.status_code,
            'stdout': self.stdout,
            'scan_time': self.scan_time,
            'infected_num': self.infected_num,
            'threats': self.threats,
            'error': self.error,
            'scanned_at': str(self.modified_at)
        }
        logger.info({
            'action': 'scan',
            'additional_data': data,
            'username': self.file.username
        })


def get_report_upload_path(instance, filename):
    return os.path.join("scan_reports/%s" % instance.name, filename)


class ScanReport(DateMixin):
    STATUS_OPTIONS = [
        ('creating', _('Creating')),
        ('created', _('Created')),
        ('failed', _('Failed'))
    ]
    name = SafeCharField(max_length=120)
    excel_file = models.FileField(upload_to=get_report_upload_path, editable=False)
    pdf_file = models.FileField(upload_to=get_report_upload_path, editable=False)
    csv_file = models.FileField(upload_to=get_report_upload_path, editable=False)
    status = models.CharField(max_length=16, choices=STATUS_OPTIONS, default='creating', editable=False)
    error = models.CharField(max_length=4096, blank=True, editable=False)

    class Meta:
        verbose_name = _('Scan Report')
        verbose_name_plural = _('Scan Reports')
        default_permissions = []



