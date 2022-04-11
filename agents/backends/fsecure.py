import json
from dateutil.parser import parse
from .core import AVBackend
from agents.exceptions import AVException


class FsecureBackend(AVBackend):
    """
        Connecting...
        Scanning...
        ----
        Scanned items: 1
        Harmful items: 0
    """
    av_name = 'fsecure'
    title = 'Fsecure'
    scan_command = r'"C:\Program Files (x86)\F-Secure\SAFE\fsscan.exe"'
    infected_pattern = r'^.*Harmful items: (?P<infected>\d+)'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\F-Secure\Ultralight\Statistics\engine" /v "array"'

    def check(self):
        if self.os.path.exists(r"C:\Program Files (x86)\F-Secure\SAFE\fsscan.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_fail(self, result):
        if result.exited == 3 and result.stdout:
            return result.stdout.strip()
        return super().on_scan_exit_fail(result)

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        return super().scan(f'"{path}"', '--noflyer')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        if output and len(output.split('    ')) >= 4:
            output = output.split('    ')[3]
            json_data = json.loads(output)
            res = [x['db'] for x in json_data]
            last_update_time = max([parse(x) for x in res if int(x[0]) != 0])
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')