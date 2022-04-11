from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from core.fields import SafeCharField, JSONField
from core.utils.api import KeyGenerator
from core.models.mixins import DateMixin


class API(DateMixin):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                              related_name='apis', editable=False)
    title = SafeCharField(max_length=256, blank=True)
    key = models.CharField(max_length=256, editable=False, unique=True)
    allowed_hosts = JSONField(default=[])
    MODE_CHOICES = (
        ('web', _('Web')),
        ('screen', _('Screen')),
    )
    app_mode = models.CharField(max_length=16, choices=MODE_CHOICES, blank=True)

    class Meta:
        verbose_name = _('Api')
        verbose_name_plural = _('Apis')

    def refresh(self):
        keygen = KeyGenerator(key_length=32)
        key = keygen.generate()
        self.key = key
        self.save()
        return key
