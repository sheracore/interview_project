from proj.celery import app as celery_app
from core.utils.version import get_version

__version_tuple__ = (0, 1, 0, 'final', 0)

VERSION = get_version(__version_tuple__)

__all__ = ['celery_app']
