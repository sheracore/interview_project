import re

from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class IkarusBackend(AVBackend):
    """
      Summary:
      ==========================================================
        1 files scanned
        1 files infected
          (1 file contained 0 items, 0 infected)

        Used time: 0:02.406
      ==========================================================
    """
    av_name = 'ikarus'
    title = 'Ikarus'
    # service_name = ''
    scan_command = r'"C:\Program Files (x86)\IKARUS\anti.virus\ikarust3\T3Scan_w64.exe"'
    scan_time_pattern = r'^.*Used time:\s*(?P<scan_time>\d+:\d+)'
    infected_pattern = r'^.*(?P<infected>\d+)\s*file(s*)\s*infected'
    version_command = r'"C:\Program Files (x86)\IKARUS\anti.virus\ikarust3\T3Scan_w64.exe" -version'

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def on_scan_exit_ok(self, result):
        m = re.match(r'^.*(?P<scanned>\d+)\s*file(s*)\s*scanned', repr(result.stdout))
        if m:
            if int(m.groupdict()['scanned']) == 0:
                raise AVException(f'Seems that nothing was scanned: {result.stdout.strip()}')
            else:
                return result.stdout.strip()
        else:
            raise AVException(f'Invalid pattern to check number of files scanned: {result.stdout.strip()}')

    def get_scan_time(self, stdout):
        if not self.scan_time_pattern:
            # raise AVException('Scan time pattern not specified')
            return None
        m = re.match(self.scan_time_pattern, repr(stdout))
        if m:
            total_time = m.groupdict()['scan_time']
            seconds = float(total_time.split(':')[0]) * 60 + \
                      float(total_time.split(':')[1])
            return seconds
        else:
            raise AVException(f'Scan time pattern not found in: {stdout}')

    def check(self):
        if self.os.path.exists(r"C:\Program Files (x86)\IKARUS\anti.virus\ikarust3\T3Scan_w64.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exists')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan(f'"{path}"')

    def get_version(self):
        output = self._perform_command(self.version_command)
        m = re.match(r'.*Engine version:\s(?P<version>\d+.\d+.\d+)', repr(output))
        if m:
            version = m.groupdict()['version']
            return version
        else:
            return AVException(f'Version pattern not found in: {output.strip()}')

    def get_last_update(self):
        output = self._perform_command(self.version_command)
        """
         Volume in drive C has no label.\n Volume Serial Number is 3444-CBA3\n\n Directory of 
         C:\\Program Files (x86)\\IKARUS\\anti.virus\\ikarust3\n\n05/03/2020  12:26 PM         
        """
        m = re.match(r'.*VDB:\s(?P<modify_date>\d+.\d+.\d+)', repr(output))  # 05/03/2020
        if m:
            modify_date = m.groupdict()['modify_date']
            return parse(modify_date.strip()).date()
        else:
            return AVException(f'Last update pattern not found in: {output}')

    def update(self, path):
        file_path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        try:
            self.extract(file_path=file_path,
                                    dst=r'C:\Program Files (x86)\IKARUS\anti.virus\ikarust3\\')
            return True
        except Exception as ex:
            raise AVException(str(ex))
