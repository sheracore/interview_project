import re
import invoke
import shutil
import platform

from django.utils import timezone
from django.conf import settings

from agents.exceptions import AVException
import rpyc
import os
import subprocess
from core.utils.files import extract_compressed_file


class AVBackend:
    av_name = None
    title = None
    service_name = None
    scan_command = None
    scan_time_pattern = None
    infected_pattern = None
    threats_pattern = None

    def __init__(self, host=None):
        if host:
            self.conn = rpyc.classic.connect(host, 18811)
            self.conn._config['sync_request_timeout'] = None
            self.os = self.conn.modules.os
            self.open = self.conn.builtins.open
            self.subprocess = self.conn.modules.subprocess
            self.invoke = self.conn.modules.invoke
            self.shutil = self.conn.modules.shutil
            self.settings = self.conn.root.settings
            self.extract = self.conn.root.extract_compressed_file
            if self.conn.modules.platform.uname().system == 'Windows':
                self.pywinauto = self.conn.modules.pywinauto
        else:
            self.conn = None
            self.os = os
            self.open = open
            self.subprocess = subprocess
            self.invoke = invoke
            self.shutil = shutil
            self.settings = settings
            self.extract = extract_compressed_file
            if platform.uname().system == 'Windows':
                import pywinauto
                self.pywinauto = pywinauto

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def _perform_command(self, command):
        if not command:
            raise AVException(
                f'No command specified')

        result = self.invoke.run(command, warn=True)

        if result.exited == 0 and result.ok:
            return result.stdout.strip()
        else:
            error = result.stderr.strip() or result.stdout.strip()
            raise AVException(error)

    def on_scan_exit_ok(self, result):
        return result.stdout.strip()

    def on_scan_exit_fail(self, result):
        error = result.stderr.strip() or result.stdout.strip()
        raise AVException(error)

    def _perform_scan_command(self, command):
        if not command:
            raise AVException(
                f'No command specified')

        result = self.invoke.run(command, warn=True)

        if result.exited == 0 and result.ok:
            return self.on_scan_exit_ok(result)
        else:
            return self.on_scan_exit_fail(result)

    def check(self):
        return self._perform_command(f'service {self.service_name} status')

    def get_scan_time(self, stdout):
        if not self.scan_time_pattern:
            # raise AVException('Scan time pattern not specified')
            return None
        m = re.match(self.scan_time_pattern, repr(stdout))
        if m:
            return float(m.groupdict()['scan_time'])
        else:
            raise AVException(f'Scan time pattern not found in following stdout: {stdout}')

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            return int(m.groupdict()['infected'])
        else:
            raise AVException(f'Infected pattern not found in following stdout: {stdout}')

    def get_threats(self, stdout):
        if not self.threats_pattern:
            # raise AVException('Threats pattern not specified')
            return None
        m = re.match(self.threats_pattern, repr(stdout))
        if m:
            return m.groupdict()['threats']
        else:
            raise AVException(f'Threats pattern not found in: {stdout}')

    def on_success(self, stdout):
        scan_time = self.get_scan_time(stdout)
        infected = self.get_infected_num(stdout)
        threats = self.get_threats(stdout)
        return scan_time, infected, threats

    def scan(self, *args):
        now = timezone.now()
        command = f'{self.scan_command} {" ".join(args)}'
        stdout = self._perform_scan_command(command)
        scan_time, infected, threats = self.on_success(stdout)
        if not scan_time:
            end = timezone.now()
            result = end - now
            scan_time = result.seconds
        return stdout, scan_time, infected, threats

    def get_last_update(self):
        return None

    def get_version(self):
        return None

    def get_license_key(self):
        return None

    def get_license_expiry(self):
        return None

    def update(self, path):
        raise AVException('Offline update not implemented.')
