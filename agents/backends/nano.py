from .core import AVBackend
from agents.exceptions import AVException
import re
from datetime import datetime


class NanoBackend(AVBackend):
    """
        Scanned files:       1
        Scanned objects:     1
        Infected files:      1
        Infected objects:    1
        Suspicious files:    0
        Suspicious objects:  0
        Cured files:         0
        Deleted files:       0
        Scan time:           00:00:01.016
    """
    av_name = 'nano'
    title = 'NanoAV'
    scan_command = r'"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" scan'
    exe_file_path = r'C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe'
    infected_pattern = r'^.*Infected files:\s*(?P<infected>\d+)'
    scan_time_pattern = r'^.*Scan time:\s*(?P<scan_time>\d+:\d+:\d+)\s*'
    last_update_command = r'"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" avinfo'

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.exe_file_path}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        return super().scan(path)

    def get_scan_time(self, stdout):
        if not self.scan_time_pattern:
            return None
        m = re.match(self.scan_time_pattern, repr(stdout))
        if m:
            total_time = m.groupdict()['scan_time']
            seconds = float(total_time.split(':')[0]) * 60 * 60 + \
                      float(total_time.split(':')[1]) * 60 + \
                      float(total_time.split(':')[2])
            return seconds
        else:
            raise AVException(f'Scan time pattern not found in: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 1 and result.stdout:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*Virus base: \d+.\d+.\d+.\d+ \((?P<last_update_time>\d+-\d+-\d+ \d+:\d+:\d+)\)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.strptime(last_update_time, '%Y-%m-%d %H:%M:%S')
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
