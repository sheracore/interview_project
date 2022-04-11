from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.fields import JSONField
from core.models.mixins import DateMixin


class AbstractAuditLog(models.Model):
    choices = (
        ('device_add', _("Add Device")),
        ('device_remove', _("Remove Device")),
        ('device_change', _("Change Device")),
        ('device_mount', _("Mount Device")),
        ('device_unmount', _("Unmount Device")),
        ('user_login', _("User Login")),
        ('user_create', _("User Create")),
        ('user_update', _("User Update")),
        ('user_destroy', _("User Destroy")),
        ('user_pass_change', _("User Password Change")),
        ('scan', _("File Scan")),
        ('settings_create', _("Settings Create")),
        ('settings_reset', _("Settings Reset")),
        ('settings_update', _("Settings Update")),
    )

    level = models.CharField(max_length=10)
    message = models.TextField()
    action = models.CharField(choices=choices, max_length=32,
                              verbose_name=_("action"), null=True)
    username = models.CharField(max_length=32, blank=True, null=True)
    remote_addr = models.GenericIPAddressField(
        blank=True, null=True, verbose_name=_("remote address")
    )
    additional_data = JSONField(blank=True, null=True,
                                verbose_name=_("additional data"))

    class Meta:
        abstract = True


class AuditLog(AbstractAuditLog, DateMixin):
    class Meta:
        ordering = ['created_at']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        default_permissions = ['view']
