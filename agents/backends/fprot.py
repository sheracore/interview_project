from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse
import re


class FprotBackend(AVBackend):
    """
    Results:

    Files: 1
    Skipped files: 0
    MBR/boot sectors checked: 0
    Objects scanned: 1
    Infected objects: 1
    Infected files: 1
    Files with errors: 0
    Disinfected: 0

    Running time: 00:02
    """
    av_name = 'fprot'
    title = 'Fprot'
    scan_command = '/usr/local/bin/fpscan'
    last_update_command = 'stat /opt/f-prot/antivir.def | grep Modify'
    scan_time_pattern = r'^.*Running\s+time:\s+(?P<scan_time>\d+:\d+)'
    infected_pattern = r'.*Infected\s+files:\s+(?P<infected>\d+)'

    def check(self):
        if self.os.path.exists(self.scan_command):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_fail(self, result):
        if result.exited == 1 and result.stdout:
            return result.stdout
        return super().on_scan_exit_fail(result)

    def get_scan_time(self, stdout):
        if not self.scan_time_pattern:
            return None
        m = re.match(self.scan_time_pattern, repr(stdout))
        if m:
            total_time = m.groupdict()['scan_time']
            seconds = float(total_time.split(':')[0]) * 60 + \
                float(total_time.split(':')[1])
            return seconds
        else:
            raise AVException(f'Scan time pattern not found in: {stdout}')

    def scan(self, path):
        return super().scan('--report', f'"{path}"')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        output_list = output.split(' ')
        if len(output_list) > 1:
            try:
                return parse(output_list[1]).date()    # 2021-09-22
            except Exception as e:
                raise AVException(str(e))
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')

    def update(self, path):
        try:
            self.extract(file_path=path, dst='/opt/f-prot')
            return True
        except Exception as e:
            raise AVException(str(e))
