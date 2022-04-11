from time import sleep
from django.core.management.base import BaseCommand

from kiosks.models import Kiosk

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sets kiosks status periodically'

    def set_status(self):
        kiosks = Kiosk.objects.all()
        kiosk_names = []
        for kiosk in kiosks:
            kiosk_names.append(kiosk.api_ip)

            # logger.info(f'Setting status for kiosk with IP {kiosk.api_ip}')
            res = kiosk.remote('system/settings/', 'GET')
            status = {
                'status_code': res['status_code'],
                'detail': res.get('detail') or (
                        res['status_code'] == 200 and 'Up')
            }
            Kiosk.objects.filter(pk=kiosk.pk).update(status=status)
        logger.info(f'Status set for kiosks with IPs {",".join(kiosk_names)}')
        return True

    def handle(self, *args, **options):
        logger.info('Polling kiosks started ...')
        while True:
            # logger.info('Starting to set status for kiosks ...')
            self.set_status()
            sleep(5)
