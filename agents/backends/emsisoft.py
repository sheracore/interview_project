import uuid
from .core import AVBackend
from agents.exceptions import AVException
import re
from dateutil.parser import parse


class EmsisoftBackend(AVBackend):
    """
           Emsisoft Commandline Scanner - Version 2021.4.0.10765
            2 Last update: N/A
            3 (C) 2003-2021 Emsisoft - www.emsisoft.com
            4
            5
            6 Scan settings:
            7
            8 Scan type:                             Custom Scan
            9 Objects:                               \\192.168.100.1\smb\eicar.com
            10
            11 Detect Potentially Unwanted Programs:  Off
            12 Scan archives:                         Off
            13 Scan mail archives:                    Off
            14 ADS Scan:                              Off
            15 Direct disk access:                    Off
            16
            17 Scan start:                            8/30/2021 2:58:17 PM
            18
           19 \\192.168.100.1\smb\eicar.com   detected: EICAR-Test-File (not a virus) (B)
            20
            21
            22 Scanned           1
            23 Found             1
            24
            25 Scan end:         8/30/2021 2:58:24 PM
            26 Scan time:        0:00:07

    """

    av_name = 'emsisoft'
    title = 'Emsisoft'
    # service_name = ''
    scan_command = r'"C:\EEK\bin64\a2cmd.exe"'
    # scan_time_pattern = ''
    infected_pattern = r'.*Found\s*(?P<infected>\d+)'
    version_command = ''
    last_update_command = r'"C:\EEK\bin64\a2cmd.exe" /updatefeed="1'

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def on_scan_exit_ok(self, result):
        m = re.match(r'.*Scanned\s*(?P<scanned>\d+)', repr(result.stdout))
        if m:
            if int(m.groupdict()['scanned']) == 0:
                raise AVException('File not found')
            else:
                return super().on_scan_exit_ok(result)
        else:
            raise AVException(f'Invalid pattern to check number of files scanned: {result.stdout.strip()}')

    def check(self):
        if self.os.path.exists(r"C:\EEK\bin64\a2cmd.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        # converting /smb/eicar.com to  \\192.168.100.1\smb\eicar.com
        path = r'\\192.168.100.1' + path.replace('/', '\\')
        return super().scan(f'/f="{path}"')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*Update end: \s*(?P<last_update_time>\d+\/\d+\/\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')

    def update(self, path):
        # converting /smb/user_file.zip to  \\192.168.100.1\smb\user_file.zip
        path = r'\\192.168.100.1' + path.replace('/', '\\')
        old_path_name = f"C:\EEK-{str(uuid.uuid4())}"
        try:
            if self.os.path.exists(r"C:\EEK"):
                self.shutil.move(r'C:\EEK', f'{old_path_name}')
                self.extract(file_path=path, dst=r'C:\\')
                self.shutil.rmtree(old_path_name)
            else:
                self.extract(file_path=path, dst=r'C:\\')
            return True

        except Exception as ex:
            if self.os.path.exists(r"C:\EEK") and self.os.path.exists(old_path_name):
                self.shutil.rmtree(r'C:\EEK')
                self.shutil.move(f'{old_path_name}', r'C:\EEK')
            raise AVException(str(ex))
