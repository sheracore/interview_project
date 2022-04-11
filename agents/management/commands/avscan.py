from django.core.management.base import BaseCommand
from agents.models import Agent


class Command(BaseCommand):
    help = 'Scans a file on an antivirus'

    def add_arguments(self, parser):
        parser.add_argument('av_name', help='Antivirus backend module name',
                            type=str)
        parser.add_argument('file_path', help='File path to be scanned',
                            type=str)

    def handle(self, *args, **options):
        av_name = options['av_name']
        file_path = options['file_path']

        agent = Agent.objects.get(av_name=av_name)

        stdout, scan_time, infected, threats = agent.av.scan(file_path)
        self.stdout.write(self.style.SUCCESS(stdout))
