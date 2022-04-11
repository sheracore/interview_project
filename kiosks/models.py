from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.db import models

from core.fields import SafeCharField
from core.models.server import Server
from core.models.auditlog import AbstractAuditLog

from scans.models.scan import AbstractScan
from scans.models.file import AbstractFile, AbstractFileInfo


class Kiosk(Server):
    serial = SafeCharField(max_length=64, unique=True)
    last_update = models.DateTimeField(null=True)

    class Meta:
        verbose_name = _('Kiosk')
        verbose_name_plural = _('Kiosks')
        permissions = [
            ('remote', 'Can Send Remote Request')
        ]

    def get_url(self):
        return f'http://{self.api_ip}:{self.api_port}/{translation.get_language()}/api/v1/'

    def remote(self, url, method, json=None, data=None, files=None, extra_headers=None, params=None):
        return self.perform(url, method=method, json=json, data=data, files=files,
                            extra_headers=extra_headers, params=params)


class ScanLog(AbstractScan, AbstractFile, AbstractFileInfo):
    kiosk = models.ForeignKey(Kiosk, on_delete=models.SET_NULL, null=True,
                              related_name='scan_logs', editable=False)
    kiosk_title = models.CharField(editable=False, null=True, max_length=64,
                                   blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField()
    read = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = _('Scan Log')
        verbose_name_plural = _('Scan Logs')
        default_permissions = ['view']


class KioskAuditLog(AbstractAuditLog):
    kiosk = models.ForeignKey(Kiosk, on_delete=models.SET_NULL, null=True, related_name='audit_log', editable=False)
    kiosk_title = models.CharField(editable=False, null=True, max_length=64, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ['received_at']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        default_permissions = ['view']
