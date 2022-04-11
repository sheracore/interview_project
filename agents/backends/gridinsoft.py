import re
from dateutil.parser import parse
from .core import AVBackend
from agents.exceptions import AVException


class GridinsoftBackend(AVBackend):
    r"""
        C:\Users\vagrant>"C:\Program Files\GridinSoft Anti-Malware\tkcon.exe" C:\Users\vagrant\Desktop\infected\eicar
        Scan started...
        C:\Users\vagrant\Desktop\infected\eicar
        Threat
        Trojan.EicarTest.vl!yf
        Scan finished
        """
    av_name = 'gridinsoft'
    title = 'GridinSoft'
    scan_command = r'"C:\Program Files\GridinSoft Anti-Malware\tkcon.exe"'
    last_update_command = r'"C:\Program Files\GridinSoft Anti-Malware\tkcon.exe" /dbinfo'

    def check(self):
        if self.os.path.exists(r"C:\Program Files\GridinSoft Anti-Malware\tkcon.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        return super().scan(f'"{path}"')

    def get_infected_num(self, stdout):
        if 'Threat' in stdout:
            return 1
        elif 'Clean' in stdout:
            return 0
        raise AVException(f'Invalid stdout: {stdout}')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        """
            EngineVersion   : 4.2.27
            DatabaseVersion : 2022.02.27 11-01-21
            VirusSignatures : 66800348
        """
        m = re.match(r'^.*DatabaseVersion : (?P<last_update_time>\d+.\d+.\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
