from .core import AVBackend
from agents.exceptions import AVException
import re
from datetime import datetime


class ZillyaBackend(AVBackend):
    """
        Zillya! Command line scanner v3.0.0.1\n\n   Programm version: 3.0.2339.0 Kernel version: 1.2.0.13\n\n   Bases
        version: 2.0.0.4513 Records count: 16485920\n\n   Copyright(c) 2009 - 2016 ALLIT Service LLC. All rights
        reserved.\n\n\n\n\nC:\\test.txt (Skipped EICAR.TestFile)\n\n\n\n\n   Elapsed time:\t\t00:00:00\n\n
        Files scanned:\t\t1\n\n   Infected files found:\t1\n\n   Deleted:\t\t\t0\n\n   Cleaned:\t\t\t0
    """
    av_name = 'zillya'
    title = 'Zillya'
    scan_command = r'"C:\Program Files (x86)\Zillya Antivirus\ConScan.exe"'
    exe_file_path = r'C:\Program Files (x86)\Zillya Antivirus\ConScan.exe'
    infected_pattern = r'^.*Infected files found:\\t(?P<infected>\d+)'
    scan_time_pattern = r'^.*Elapsed time:[\\t]*(?P<scan_time>\d+:\d+:\d+)\s*'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Zillya Antivirus" /v "AVUpdateTime"'

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.exe_file_path}" path does not exist')

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

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*AVUpdateTime\s*REG_QWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.fromtimestamp(int(last_update_time, 16))
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
