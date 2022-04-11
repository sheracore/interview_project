from .core import AVBackend
from agents.exceptions import AVException
import uuid
import time
import re
from datetime import datetime


class DrwebBackend(AVBackend):
    """
        Total 8 bytes in 1 file scanned
        Total 1 file are clean
        There are no infected objects detected
        Scan time is 00:00:01, 0KB/sec
    """
    av_name = 'drweb'
    title = 'Dr Web'
    scan_command = r'"C:\Program Files\DrWeb\dwscancl.exe" /OK /AR'
    exe_file_path = r'C:\Program Files\DrWeb\dwscancl.exe'
    log_path = ''
    scan_time_pattern = r'^.*Scan time is (?P<scan_time>\d+:\d+:\d+)'
    infected_pattern = r'.*Total *(?P<infected>\d+) file[s]* are infected'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\Doctor Web\Settings\av-service" /v "LastUpdate"'

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.exe_file_path}" path does not exist')

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')

        if 'There are no infected objects detected' in stdout:
            return 0
        else:
            m = re.match(self.infected_pattern, repr(stdout))
            if m:
                return int(m.groupdict()['infected'])
            else:
                raise AVException(f'Infected pattern not found in following stdout: {stdout}')

    def get_scan_time(self, stdout):
        if not self.scan_time_pattern:
            return None
        m = re.match(self.scan_time_pattern, repr(stdout))
        if m:
            total_time = m.groupdict()['scan_time']
            seconds = float(total_time.split(':')[0]) * 60 * 60 + float(total_time.split(':')[1]) * 60 + \
                      float(total_time.split(':')[2])
            return seconds
        else:
            raise AVException(f'Scan time pattern not found in: {stdout}')

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        complete_log = False
        while counter < 10:
            if self.os.path.exists(self.log_path):
                with self.open(self.log_path, 'r') as f:
                    stdout = f.read()
                    if stdout:
                        complete_log = True
                        break
            time.sleep(0.5)
            counter += 1
        self.os.remove(self.log_path)
        if complete_log:
            return stdout
        raise AVException('After 10 tries, log is still empty')

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()
        return stdout

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return self.read_stdout_from_scan_log()
        else:
            return super().on_scan_exit_fail(result)

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        self.log_path = rf'{self.settings.MEDIA_ROOT}\DW_{str(uuid.uuid4())}.txt'
        return super().scan(f'"{path}" /RA:{self.log_path}')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LastUpdate\s*REG_QWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.fromtimestamp(int(last_update_time, 16))
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
