import re
from dateutil.parser import parse
from .core import AVBackend
from agents.exceptions import AVException


class WinessentialsBackend(AVBackend):
    av_name = 'winessentials'
    title = 'Microsoft Security Client'
    scan_command = r'"C:\Program Files\Windows Defender\MpCmdRun.exe"'

    scan_time_pattern = ''
    infected_pattern = r'^.*Scanning.*found\s*(?P<infected>\S+)\s*threats.'
    last_update_command = r'Powershell Get-WmiObject -namespace "Root/Microsoft/Windows/Defender" MSFT_MpComputerStatus'

    def check(self):
        if self.os.path.exists(
                r"C:\Program Files\Windows Defender\MpCmdRun.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            infected = m.groupdict()['infected']
            if infected == 'no':
                return 0
            else:
                return int(infected)
        else:
            raise AVException(f'Infected pattern not found in: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 2:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def scan(self, path):
        path = r'\\192.168.100.1' + path.replace('/', '\\')
        return super().scan(
            '-scan -scantype 3 -disableremediation -file', f'"{path}"'
        )

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
                    self._perform_command(nested_file_path)
            return True

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            if self.os.path.exists(self.settings.MEDIA_ROOT):
                self.shutil.rmtree(self.settings.MEDIA_ROOT)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'.*AntivirusSignatureLastUpdated\s*:\s*(?P<last_update>\d+)', repr(output))
        if m:
            last_update = m.groupdict()['last_update'][:8]
            return parse(last_update.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')
