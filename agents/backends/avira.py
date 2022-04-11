from .core import AVBackend
from agents.exceptions import AVException
import re
import time
from dateutil.parser import parse


class AviraBackend(AVBackend):
    """
       The scan has been done completely.

      0 Scanned directories
      1 Files were scanned
      1 Viruses and/or unwanted programs were found
      0 Files were classified as suspicious
      0 Files were deleted
      0 Viruses and unwanted programs were repaired
      0 Files were moved to quarantine
      0 Files were renamed
      0 Files cannot be scanned
      0 Files not concerned
      0 Archives were scanned
      1 Warnings
      0 Notes
    """

    av_name = 'avira'
    title = 'avira'
    scan_command = r'"C:\Program Files (x86)\Avira\Antivirus\avscan.exe"'
    last_update_command = r'dir /T:W "C:\Program Files (x86)\Avira\Antivirus\local000.vdf"'
    scan_time_pattern = ''
    infected_pattern = r'.*(?P<infected>\d+)\s*Viruses and/or unwanted programs were found'
    log_path = r'C:\ProgramData\Avira\Antivirus\LOGFILES'

    def read_stdout_from_scan_log(self):
        scan_complete = False
        counter = 0
        time.sleep(0.5)
        while (not scan_complete) and (counter < 10):
            files = self.os.listdir(self.log_path)
            for file in files:
                if file.startswith('AVSCAN'):
                    path = self.log_path + '\\' + file
                    with self.open(path, 'rb') as f:
                        stdout = f.read()
                        stdout = stdout.decode("utf-16")
                        if stdout and ("The scan has been done completely." in stdout):
                            return stdout
            time.sleep(0.5)
            counter += 1
        else:
            raise AVException('After 10 tries, log is still empty')

    def on_scan_exit_fail(self, result):
        if result.exited == 200:
            return self.read_stdout_from_scan_log()
        else:
            raise AVException(result.stdout)

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()

        if stdout:
            m = re.match(r'.*\s*(?P<scanned>\d+)\s+Files were scanned', repr(stdout))
            if m:
                if int(m.groupdict()['scanned']) == 0:
                    raise AVException(f'Seems that nothing was scanned: {stdout}')
                else:
                    return stdout
            else:
                raise AVException(
                    f'Invalid pattern to check number of objects processed: {stdout}')
        else:
            raise AVException('After 10 tries, log is still empty')

    def check(self):
        if self.os.path.exists(r'C:\Program Files (x86)\Avira\Antivirus\avscan.exe'):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        files = self.os.listdir(self.log_path)
        for file in files:
            if file.startswith('AVSCAN'):
                self.os.remove(self.log_path + '\\' + file)
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan('/CFG="C:\\filescan.avp"', f'/PATH="{path}"')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        """
         Volume in drive C has no label.\n Volume Serial Number is 46D8-DDF8\n\n 
         Directory of C:\\Program Files (x86)\\Avira\\Antivirus\n\n09/12/2021  03:09 PM       104,747,008 local000.vdf\n 
         1 File(s)    104,747,008 bytes\n               0 Dir(s)   4,912,402,432 bytes free\n
        """

        m = re.match(r'^.*(?P<modify_date>\d+./\d+./\d+)', repr(output))  # 09/12/2021
        if m:
            modify_date = m.groupdict()['modify_date']
            return parse(modify_date.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
