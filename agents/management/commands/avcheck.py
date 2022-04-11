from django.core.management.base import BaseCommand
from agents.models import Agent


class Command(BaseCommand):
    help = 'Checks an antivirus functionality'

    def add_arguments(self, parser):
        parser.add_argument('av_name', help='Antivirus backend module name',
                            type=str)

    def handle(self, *args, **options):
        av_name = options['av_name']

        agent = Agent.objects.get(av_name=av_name)
        agent.av.check()

        self.stdout.write(self.style.SUCCESS(f'{av_name} is up'))
