from datetime import datetime
from .core import AVBackend
from agents.exceptions import AVException
import re


class SophosBackend(AVBackend):
    """
        1 file swept in 7 seconds.
        1 virus was discovered.  OR No viruses were discovered.
        1 file out of 1 was infected.
        If you need further advice regarding any detections please visit our
        Threat Center at: http://www.sophos.com/en-us/threat-center.aspx
        Ending Sophos Anti-Virus.
    """
    av_name = 'sophos'
    title = 'Sophos'
    scan_command = r'"C:\ProgramData\Sophos\AutoUpdate\Cache\decoded\savxp\program files\Sophos\Sophos Anti-Virus\SAV32CLI.exe"'
    scan_time_pattern = r''
    infected_pattern = r'^.*(?P<infected>\d+)\svirus was discovered\.'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Sophos\AutoUpdate\UpdateStatus" /v "LastUpdateTime"'
    version_command = r''

    def check(self):
        if self.os.path.exists(r"C:\ProgramData\Sophos\AutoUpdate\Cache\decoded\savxp\program files\Sophos\Sophos Anti-Virus\SAV32CLI.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_fail(self, result):
        if result.exited == 3:
            if result.stdout:
                return result.stdout.strip()
            elif result.stderr:
                raise AVException(result.stderr.strip())
            else:
                raise AVException('No stdout and stderr returned.')
        else:
            return super().on_scan_exit_fail(result)

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')
        if "No viruses were discovered." in repr(stdout):
            return 0
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            return int(m.groupdict()['infected'])
        else:
            raise AVException(f'Infected pattern not found in following stdout: {stdout}')

    def scan(self, path):
        path = r'\\192.168.100.1' + path.replace('/', '\\')
        return super().scan(r'-P=C:\scanlog.txt', f'"{path}"')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LastUpdateTime\s*REG_DWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.fromtimestamp(int(last_update_time, 16))
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')