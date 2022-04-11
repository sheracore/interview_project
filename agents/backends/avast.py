import re
from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class AvastBackend(AVBackend):
    """
    # ----------------------------------------------------------------
    # Number of scanned files: 1
    # Number of scanned folders: 0
    # Number of infected files: 0
    # Total size of scanned files: 1864
    # Virus database: 200928-2, 09/28/20
    # Total scan time: 0:0:0
    """
    av_name = 'avast'
    title = 'Avast'
    # service_name = ''
    scan_command = r'"C:\Program Files\AVAST Software\Avast\ashCmd.exe"'
    scan_time_pattern = r'^.*Total scan time:\s*(?P<scan_time>\d+:\d+:\d+)\s*'
    infected_pattern = r'^.*Number of infected files:\s*(?P<infected>\d+)'
    last_update_command = r'"C:\Program Files\AVAST Software\Avast\ashCmd.exe" --console'
    version_command = r'reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Avast Antivirus" /v DisplayVersion'

    def check(self):
        if self.os.path.exists(r"C:\Program Files\AVAST Software\Avast\ashCmd.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def get_scan_time(self, stdout):
        if not self.scan_time_pattern:
            # raise AVException('Scan time pattern not specified')
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

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            if result.stdout:
                return result.stdout
            elif result.stderr:
                raise AVException(result.stderr)
            else:
                raise AVException('No stdout and stderr returned.')
        else:
            return super().on_scan_exit_fail(result)

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan('/a /c /t=A /_', f'"{path}"')

    def get_version(self):
        output = self._perform_command(self.version_command)
        version = output.split(' ')[-1]
        return version

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'.*Virus database:\s*(?P<last_update>\d+)', repr(output))
        if m:
            last_update = m.groupdict()['last_update']
            last_update = last_update[-2:] + last_update[2:4] + last_update[:2]
            return parse(last_update.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')

    def update(self, path):
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_path = path.replace('/smb/', 'Z:/').replace('/', '\\')

        try:
            final_path = self.extract(file_path=file_path, dst=self.settings.MEDIA_ROOT)
            gen = self.os.walk(final_path)
            for i in gen:
                for file in i[2]:
                    nested_file_path = self.os.path.join(i[0], file)
                    result = self.invoke.run(f'{nested_file_path} /silent', warn=True)
                    if result.exited == 1:
                        error = result.stderr.strip() or result.stdout.strip()
                        raise AVException(error)
            return True

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            self.shutil.rmtree(self.settings.MEDIA_ROOT)

