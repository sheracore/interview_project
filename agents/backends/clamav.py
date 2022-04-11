
from .core import AVBackend
from agents.exceptions import AVException
import re

from dateutil.parser import parse


class ClamavBackend(AVBackend):
    """
        Sample outputput of clamdscan command:
                /tmp/0373ce9f-2f37-4cb0-a371-2c31e65683c8: OK
                mal.pdf: Heuristics.PDF.ObfuscatedNameObject FOUND

                ----------- SCAN SUMMARY -----------
                Known viruses: 6561140
                Engine version: 0.99.4
                Scanned directories: 1
                Scanned files: 4
                Infected files: 2
                Data scanned: 2.29 MB
                Data read: 3.02 MB (ratio 0.76:1)
                Time: 10.522 sec (0 m 10 s)

    """
    av_name = 'clamav'
    title = 'Clamav'
    service_name = 'clamav-daemon'
    scan_command = 'clamdscan'
    scan_time_pattern = r'^.*Time:\s*(?P<scan_time>\S+)'
    infected_pattern = r'^.*Infected files:\s*(?P<infected>\d+)'
    last_update_command = f'sigtool --info /var/lib/clamav/daily.cvd'
    version_command = f'clamscan -V'

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return result.stdout
        # elif result.exited == 2:
        #     raise AVException('unable to open', result.command)
        else:
            return super().on_scan_exit_fail(result)

    def get_last_update(self):
        result = self._perform_command(self.last_update_command)
        """
        File: /var/lib/clamav/daily.cvd
        Build time: 08 Jan 2020 04:56 -0500
        """
        m = re.match(r'.*Build time:\s*((?P<build_time>.*)\s(-))', repr(result))  # return '08 Jan 2020 04:56'
        if m:
            build_time = m.groupdict()['build_time']
            return parse(build_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {result.strip()}')

    def update(self, path):
        try:
            self.extract(file_path=path, dst='/var/lib/clamav/')
            self._perform_command("chmod 444 /var/lib/clamav/bytecode.cvd && chmod 444 /var/lib/clamav/daily.cvd &&"
                                  "chmod 444 /var/lib/clamav/main.cvd")
            self._perform_command("chown -R clamav:clamav /var/lib/clamav/ && chown -R clamav:clamav /var/log/clamav")
            self._perform_command("systemctl restart clamav-daemon.service")
            return True
        except Exception as ex:
            raise AVException(str(ex))

    def scan(self, path):
        return super().scan(f'"{path}"')

    def get_version(self):
        return self._perform_command(self.version_command)

    def get_license_key(self):
        return 'Free'

    def get_license_expiry(self):
        return 'Free'
