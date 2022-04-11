import os

from celery import Celery
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'proj.settings')

app = Celery('viruspod')
app.conf.task_default_queue = settings.CELERY_TASK_DEFAULT_QUEUE
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self, tid):
    from time import sleep
    logger.info(self)
    sleep(5)
    logger.info('testing celery log')
    return tid
