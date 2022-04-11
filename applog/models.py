from django.db import models

from core.fields import JSONField


class AppLog(models.Model):
    level = models.CharField(max_length=16)
    message = models.CharField(blank=True, max_length=255, null=True)
    username = models.CharField(max_length=32, blank=True, null=True)
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    additional_data = JSONField(blank=True, null=True)
