from django.core.management.base import BaseCommand

from core.models.system import System


class Command(BaseCommand):
    help = 'Udev Service'

    def handle(self, *args, **options):
        System.mount_devices()
        System.monitor_udev()
