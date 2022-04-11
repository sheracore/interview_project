from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.fields import SafeCharField, JSONField
from core.models.mixins import DateMixin


class MimeTypeCat(DateMixin):
    name = SafeCharField(max_length=128, unique=True)

    class Meta:
        verbose_name = _('Mime Type Category')
        verbose_name_plural = _('Mime Type Categories')
        default_permissions = []


class MimeType(DateMixin):
    cat = models.ForeignKey(MimeTypeCat, on_delete=models.CASCADE,
                            related_name='mimetypes')
    name = SafeCharField(max_length=128, unique=True)
    extensions = JSONField(default=[])

    class Meta:
        verbose_name = _('Mime Type')
        verbose_name_plural = _('Mime Types')
