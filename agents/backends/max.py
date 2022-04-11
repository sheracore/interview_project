import re
from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class MaxBackend(AVBackend):
    r"""
        C:\Users\vagrant>"C:\Program Files\Max Secure Anti Virus Plus\MaxCMDScanner.exe" /V /C /E /L /EX /CM /DRIVES:C:\Users\vagrant\Desktop\infected\pow-setup-7[1].bin

        Please Press ESCAPE Key if You Want To Stop the Scan.....
        @@@@@@Start Scan Time : 13:07:14


        Scanning Files (Signature and Virus Scan)...
        $$$$$ FOUND :File  Trojan.Malware.73553554.susgen       c:\users\vagrant\desktop\infected\pow-setup-7[1].bin
        Scanning for Special Spyware...

         >>>>>>>  1 Spyware Found
        Exiting Scanner
        Finished Scanning........

        @@@@@@ Scan End Time : 13:07:22
        @@@@@@ Total Elapsed Time : 00:00:08
        """
    av_name = 'max'
    title = 'Max Secure Anitvirus Plus'
    scan_command = r'"C:\Program Files\Max Secure Anti Virus Plus\MaxCMDScanner.exe"'
    last_update_command = r'reg query HKLM\software\\"max secure anti virus plus" /v LastLiveUpdate'
    scan_time_pattern = r'^.*Total Elapsed Time\s:\s(?P<scan_time>\d+:\d+:\d+)'
    infected_pattern = r'^.*>\s*(?P<infected>\S+)\s*Spyware Found'

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            infected = m.groupdict()['infected']
            if infected == 'No':
                return 0
            else:
                return int(infected)
        else:
            raise AVException(f'Infected pattern not found in: {stdout}')

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

    def check(self):
        if self.os.path.exists(r"C:\Program Files\Max Secure Anti Virus Plus\MaxCMDScanner.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exists')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        return super().scan('/C /V /CM /E /DRIVES:', f'"{path}"')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        output_list = output.split(' ')
        if len(output_list) > 1:
            try:
                return parse(output_list[-1]).date()      #31-Jul-2021
            except Exception as e:
                raise AVException(str(e))
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')

