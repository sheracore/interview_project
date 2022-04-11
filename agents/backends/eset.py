import re
import uuid
from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class EsetBackend(AVBackend):
    """
        ESET Command-line scanner, version 15.0.16.0, (C) 1992-2021 ESET, spol. s r.o.
        Module loader, version 1023 (20200701), build 1067
        Module perseus, version 1581.1 (20211007), build 2249
        Module scanner, version 24246 (20211105), build 51405
        Module archiver, version 1324 (20211011), build 1394
        Module advheur, version 1211 (20211004), build 1213
        Module cleaner, version 1222 (20210907), build 1356
        Module augur, version 1114 (20210907), build 1115

        Command line: C:\01.exe /base-dir=C:\ESET_Command-line_Scanner\Modules

        Scan started at:   Mon Jan  3 14:08:21 2022
        name="C:\01.exe", result="Eicar test file", action="retained", info=""

        Scan completed at: Mon Jan  3 14:08:21 2022
        Scan time:         0 sec (0:00:00)
        Total:             files - 2, objects 2
        Detected:          files - 1, objects 1
        Cleaned:           files - 0, objects 0
    """
    av_name = 'eset'
    title = 'Eset Security'
    service_name = 'esets'
    scan_command = r'"C:\ESET_CommandLine_Scanner\ecls.exe"'
    scan_time_pattern = r'^.*Scan time:\s*(?P<scan_time>\S+)'
    infected_pattern = r'^.*Detected:\s*files\s*-\s*(?P<infected>\d+)'
    total_pattern = r'^.*\s*Total:\s*files\s*-\s*(?P<total>\d+),'
    # version_pattern = r"^.*version\s*(?P<version>\S*),\s\DC"
    last_update_command = r'"C:\ESET_CommandLine_Scanner\ecls.exe" "" /base-dir="C:\ESET_CommandLine_Scanner\Modules"'

    def check(self):
        if self.os.path.exists(r'C:\ESET_CommandLine_Scanner\ecls.exe'):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_fail(self, result):
        if result.exited == 50:
            return result.stdout
        elif result.exited == 10:
            raise AVException(f'unable to open due to this: {result.stdout.strip()}')
        else:
            return super().on_scan_exit_fail(result)

    def on_scan_exit_ok(self, result):
        m = re.match(self.total_pattern, repr(result.stdout))
        if m:
            if int(m.groupdict()['total']) == 0:
                raise AVException(f'Seems that nothing was scanned: {result.stdout.strip()}')
            else:
                return result.stdout.strip()
        else:
            raise AVException(f'Invalid pattern to check number of files scanned: {result.stdout.strip()}')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan(r'/base-dir="C:\ESET_CommandLine_Scanner\Modules"', path)

    def update(self, path):
        # converting /smb/user_file.zip to  \\192.168.100.1\smb\user_file.zip
        zip_path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        path = self.scan_command.replace('"','')
        path = '\\'.join(path.split('\\')[0:-1])
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
        m = re.match(r'^.*Module scanner, version \d+ \((?P<last_update_time>\d+)\)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
