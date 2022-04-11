from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models.api import API
from django.db.models import ObjectDoesNotExist

User = get_user_model()


class Command(BaseCommand):
    help = 'Add API Key'

    def add_arguments(self, parser):
        parser.add_argument('owner', nargs=1, type=str)
        parser.add_argument('api_key', nargs=1, type=str)

    def handle(self, *args, **options):
        username = options['owner'][0]
        key = options['api_key'][0]
        try:
            owner = User.objects.get(username=username)
        except ObjectDoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist')
            )
            return

        instance, created = API.objects.get_or_create(key=key, defaults={'owner': owner})
        if created:
            self.stdout.write(
                'Created API key ' + self.style.SUCCESS('%s' % key) + ' for ' + self.style.SUCCESS('%s' % username)
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'API key "{key}" already exists.')
            )
