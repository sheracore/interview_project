from time import sleep
from django.core.management.base import BaseCommand

from agents.models import Agent
from agents.exceptions import AVException

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sets agents status periodically'

    def set_status(self):
        agents = Agent.objects.filter(active=True)
        av_names = []
        for agent in agents:
            av_names.append(agent.av_name)
            # logger.info(f'Setting status for {agent.av_name}')
            try:
                try:
                    agent.av.check()
                    status = {
                        'detail': 'Up', 'status_code': 200
                    }

                except AVException as e:
                    status = {'detail': f'Checking AV: {str(e)}',
                              'status_code': 498}
                    Agent.objects.filter(pk=agent.pk).update(status=status)
                    continue

                try:
                    status['version'] = agent.av.get_version()
                except AVException as e:
                    status['version'] = f'Getting AV Version: {str(e)}'

                try:
                    status['last_update'] = str(agent.av.get_last_update())
                except AVException as e:
                    status[
                        'last_update'] = f'Getting Last Update: {str(e)}'

                try:
                    status['license_key'] = agent.av.get_license_key()
                except AVException as e:
                    status[
                        'license_key'] = f'Getting License Key: {str(e)}'

                try:
                    status['license_expiry'] = str(
                        agent.av.get_license_expiry())
                except AVException as e:
                    status[
                        'license_expiry'] = f'Getting License Expiry: {str(e)}'

            except ModuleNotFoundError as e:
                status = {'detail': str(e), 'status_code': 404}
            except (TimeoutError, OSError, EOFError) as e:
                status = {'detail': str(e), 'status_code': 499}

            Agent.objects.filter(pk=agent.pk).update(status=status)
        logger.info(f'Status set for {",".join(av_names)}')
        return True

    def handle(self, *args, **options):
        logger.info('Polling agents started ...')
        while True:
            # logger.info('Starting to set status for agents ...')
            self.set_status()
            sleep(5)
