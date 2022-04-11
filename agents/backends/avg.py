from .core import AVBackend
from agents.exceptions import AVException
import re
from dateutil.parser import parse


class AvgBackend(AVBackend):
    """
    C:\01.txt       OK
    # ----------------------------------------------------------------
    # Number of scanned files: 1
    # Number of scanned folders: 0
    # Number of infected files: 0
    # Total size of scanned files: 4
    # Virus database: 220108-2, 1/8/22
    # Total scan time: 0:0:3
    """
    av_name = 'avg'
    title = 'AVG'
    scan_command = r'"C:\Program Files\AVG\Antivirus\ashCmd.exe" --console --archivetype=A'
    infected_pattern = r'^.*Number of infected files: (?P<infected>\d+)'
    scan_time_pattern = r'^.*Total scan time: (?P<scan_time>\d+:\d+:\d+)\s*'
    last_update_command = r'"C:\Program Files\AVG\Antivirus\ashCmd.exe" --console'

    def check(self):
        if self.os.path.exists(r"C:\Program Files\AVG\Antivirus\ashCmd.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def get_scan_time(self, stdout):
        m = re.match(self.scan_time_pattern, repr(stdout))
        if m:
            total_time = m.groupdict()['scan_time']
            seconds = float(total_time.split(':')[0]) * 60 * 60 + float(total_time.split(':')[1]) * 60 +\
                      float(total_time.split(':')[2])
            return seconds
        else:
            raise AVException(f'Scan time pattern not found in: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 1 and result.stdout:
            return result.stdout
        return super().on_scan_exit_fail(result)

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        return super().scan(f'"{path}"')

    def update(self, path):
        """ First extract all zip file and install all files inside that."""

        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_path = path.replace('/smb/', 'Z:/').replace('/', '\\')

        try:
            final_path = self.extract(file_path=file_path, dst=self.settings.MEDIA_ROOT)
            gen = self.os.walk(final_path)
            for i in gen:
                for file in i[2]:
                    nested_file_path = self.os.path.join(i[0], file)
                    result = self.invoke.run(nested_file_path + r' /silent', warn=True)
                    if result.exited == 1:
                        error = result.stderr.strip() or result.stdout.strip()
                        raise AVException(error)
            return True

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            self.shutil.rmtree(self.settings.MEDIA_ROOT) 

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*Virus database: (?P<last_update_time>\d+)', repr(output))  # 09/12/2021
        if m:
            last_update = m.groupdict()['last_update_time']
            last_update = last_update[-2:] + last_update[2:4] + last_update[:2]
            return parse(last_update.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
