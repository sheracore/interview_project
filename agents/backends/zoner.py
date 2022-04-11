import re
from py7zr.helpers import filetime_to_dt
from .core import AVBackend
from agents.exceptions import AVException


class ZonerBackend(AVBackend):
    r"""
        C:/test.txt: INFECTED [EICAR.Test.File-NoVirus.250]
        C:/test.txt: CLEAN
    """
    av_name = 'zoner'
    title = 'Zoner'
    scan_command = r'"C:\Program Files\Zoner\ZONER Antivirus\zavscan.exe"'
    last_update_command = r'Reg Query "HKEY_CURRENT_USER\SOFTWARE\ZONER\ZAV\Client" /v "LastUpdate"'

    def check(self):
        if self.os.path.exists(r"C:\Program Files\Zoner\ZONER Antivirus\zavscan.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_name = self.os.path.split(path)[-1]
        dst = self.settings.MEDIA_ROOT + '\\' + file_name
        try:
            self.shutil.copyfile(path, dst)
            return super().scan(f'"{dst}"')
        except Exception as ex:
            raise AVException(str(ex))
        finally:
            if self.os.path.exists(dst):
                self.os.remove(dst)

    def get_infected_num(self, stdout):
        if 'INFECTED' in stdout:
            return 1
        elif 'CLEAN' in stdout:
            return 0
        raise AVException(f'Invalid stdout: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 11:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LastUpdate\s*REG_QWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return filetime_to_dt(int(last_update_time, 16)).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
