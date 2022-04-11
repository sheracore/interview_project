import re
import uuid

from datetime import datetime
from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class GdataBackend(AVBackend):
    r"""
    G DATA Command Line Scanner. Version 5.5.21203.72.
    Copyright (C) G DATA Software AG. All rights reserved.

    Processing command:  /scan:"C:\01.exe"

    ------------------------------------------------------------
    Scan settings:
        ------------------------------------------------------------
        Engine mode:         Engine A + B (Always both)
        Engine A:            AVA 25.31960, 08.01.2022
        Engine B:            GD 27.25798, 08.01.2022
        Action (Files):      Log only
        Action (Archives):   Log only
        ------------------------------------------------------------

        Infected:            C:\01.exe; Virus: EICAR-Test-File (not a virus) (Engine A), EICAR_TEST_FILE (Engine B)

        ------------------------------------------------------------
        Scan statistics:
            ------------------------------------------------------------
            Scanned files:       1
            Infected files:      1
            Possibly infected:   0
            Cured files:         0
            Deleted files:       0
            Quarantined files:   0
            Access denied:       0
            Password protected:  0
            Bombs:               0
            Start time:          06:21:08
            Stop time:           06:21:09
            Scan duration:       00:00:01 (1s)
            ------------------------------------------------------------


            C:\Users\fwutech\Desktop>pause
            Press any key to continue . . .

    """
    av_name = 'gdata'
    title = 'Gdata Security'
    service_name = 'gdatas'
    scan_command = r'"C:\Program Files (x86)\G DATA\AntiVirus\AVK\avkcmd.exe"'
    scan_time_pattern = r'^.*Scan duration:\s*(?P<scan_time>\S*)'
    infected_pattern = r'^.*Infected files:\s*(?P<infected>\d+)'
    total_pattern = r'^.*Scanned files:\s*(?P<total_scan>\d+)'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\G Data\AVStatus" /v "SigDate"'
    # version_pattern = r"^.*version\s*(?P<version>\S*),\s\DC"

    def check(self):
        if self.os.path.exists(self.scan_command.replace('"','')):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def get_scan_time(self, stdout):
        m = re.match(self.scan_time_pattern, repr(stdout))
        time_string = m.groupdict()['scan_time']
        date_time = datetime.strptime(time_string, "%H:%M:%S")
        a_timedelta = date_time - datetime(1900, 1, 1)
        seconds = a_timedelta.total_seconds()
        if m:
            return float(seconds)
        else:
            raise AVException(f'Scan time pattern not found in following stdout: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            m = re.match(self.total_pattern, repr(result.stdout.strip()))
            if m:
                if int(m.groupdict()['total_scan']) == 0:
                    raise AVException(f'Seems that nothing was scanned: {result.stdout.strip()}')
                else:
                    return result.stdout.strip()
            else:
                raise AVException(f'Invalid pattern to check number of files scanned: {result.stdout.strip()}')
        else:
            return super().on_scan_exit_fail(result)

    def on_scan_exit_ok(self, result):
        m = re.match(self.total_pattern, repr(result.stdout.strip()))
        if m:
            if int(m.groupdict()['total_scan']) == 0:
                raise AVException(f'Seems that nothing was scanned: {result.stdout.strip()}')
            else:
                return result.stdout.strip()
        else:
            raise AVException(f'Invalid pattern to check number of files scanned: {result.stdout.strip()}')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan('/scan:', path)

    def update(self, path):
        # converting /smb/user_file.zip to  \\192.168.100.1\smb\user_file.zip
        zip_path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        path_splited = path.split('.')
        path, extension = path_splited[0], path_splited[1]
        path_old = f"{path}-{str(uuid.uuid4())}"
        try:
            if self.os.path.exists(path):
                self.shutil.move(path, path_old)
                self.extract(file_path=zip_path, dst=r'C:\\')
                self.shutil.rmtree(path_old)
            else:
                self.extract(file_path=zip_path, dst=r'C:\\')
            return True

        except Exception as ex:
            if self.os.path.exists(path) and self.os.path.exists(path_old):
                self.shutil.rmtree(path)
                self.shutil.move(path_old, path)
            raise AVException(str(ex))

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*SigDate\s*REG_SZ\s*(?P<last_update_time>\d+-\d+-\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
