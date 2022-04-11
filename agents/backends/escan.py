import re
import uuid
from datetime import datetime
from .core import AVBackend
from agents.exceptions import AVException


class EscanBackend(AVBackend):
    av_name = 'escan'
    title = 'Escan'
    scan_command = r'"C:\eScan\bdc.exe"'
    infected_pattern = r'^.*Infected files\s*:(?P<infected>\d+)'
    total_pattern = r'^.*Files\s*:(?P<total_scan>\d+)'
    last_update_command = r'"C:\eScan\bdc.exe" -update'

    def check(self):
        if self.os.path.exists(r'C:\eScan\bdc.exe'):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_ok(self, result):
        m = re.match(self.total_pattern, repr(result.stdout.strip()))
        if m:
            if int(m.groupdict()['total_scan']) == 0:
                raise AVException(f'Seems that nothing was scanned: {result.stdout.strip()}')
            else:
                return result.stdout.strip()
        else:
            raise AVException(f'Invalid pattern to check number of files scanned: {result.stdout.strip()}')

    def on_scan_exit_fail(self, result):
        if result.exited == 1 and result.stdout:
            return result.stdout
        return super().on_scan_exit_fail(result)

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        self.log_path = f'{self.settings.MEDIA_ROOT}\ESC_{str(uuid.uuid4())}.txt'
        return super().scan(path)
        # return super().scan('/pipe=escan /SC /LOGINFECT /FS /SNOC /ScanArchive', path)

    def update(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        old_path_name = f"C:\eScan-{str(uuid.uuid4())}"
        try:
            if self.os.path.exists(r"C:\eScan"):
                self.shutil.move(r'C:\eScan', f'{old_path_name}')
                self.extract(file_path=path, dst=r'C:\\')
                self.shutil.rmtree(old_path_name)
            else:
                self.extract(file_path=path, dst=r'C:\\')
            return True

        except Exception as ex:
            if self.os.path.exists(r"C:\eScan") and self.os.path.exists(old_path_name):
                self.shutil.rmtree(r'C:\eScan')
                self.shutil.move(f'{old_path_name}', r'C:\eScan')
            raise AVException(str(ex))

    def get_last_update(self):
        output = self.invoke.run(self.last_update_command, warn=True)
        if output.stdout:
            m = re.match(r'^.*Last update (?P<last_update_time>\w+ \w+ \d+ \d+:\d+:\d+ \d+)', repr(output.stdout))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.strptime(last_update_time, '%a %b %d %H:%M:%S %Y')
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
