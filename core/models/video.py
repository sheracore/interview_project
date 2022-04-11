import os
from django.db import models
from django.db.models.signals import post_delete

from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver

from core.models.mixins import DateMixin

import logging
logger = logging.getLogger(__name__)


def get_video_upload_path(instance, filename):
    return os.path.join("video_files", filename)


class Video(DateMixin):
    file = models.FileField(max_length=1024, upload_to=get_video_upload_path)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Video File')
        verbose_name_plural = _('Video Files')


@receiver(post_delete, sender=Video)
def post_delete_video(sender, instance, *args, **kwargs):
    instance.file.delete(save=False)