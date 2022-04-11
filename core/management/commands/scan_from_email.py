from django.core.management.base import BaseCommand

from core.models.system import System


class Command(BaseCommand):
    help = 'Scan From Email Process'

    def handle(self, *args, **options):
        System.start_email_scanner()
