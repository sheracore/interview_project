import time
import re
from datetime import datetime

from .core import AVBackend
from agents.exceptions import AVException


class SecureaplusBackend(AVBackend):
    """
        2022-03-15T00:48:55.371-07:00 Number of file(s): 1,
        h: 1FADD34854912DD2628B2247F058848C83E96B4E9D1ECF12CC051C6B53C31B78
        2022-03-15T00:48:55.371-07:00 Number of threat(s) detected: 1, h:
    """
    av_name = 'secureaplus'
    title = 'SecureAPlus'
    scan_command = r'"C:\Program Files\SecureAge\AntiVirus\SAScanner.exe"'
    log_path = r'C:\ProgramData\SecureAge Technology\SecureAge\log\AntiVirus.log'
    infected_pattern = r'^.*Number of threat\(s\) detected: (?P<infected>\d+)'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\SecureAge Technology\SecureAge\Applications\Vulnerability" /v "PrevJobTime"'

    def check(self):
        if self.os.path.exists(r"C:\Program Files\SecureAge\AntiVirus\SAScanner.exe"):
            return True
        else:
            raise AVException(f'{self.scan_command} path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        if self.os.path.exists(self.log_path):
            self.os.remove(self.log_path)
        return super().scan(rf'"{path}"')

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        while counter < 10:
            if self.os.path.exists(self.log_path):
                with self.open(self.log_path, 'r') as f:
                    stdout = f.read()
                    if stdout and "Number of threat(s) detected:" in stdout:
                        self.os.system(r'taskkill /f /im "SAScanner.exe" /t')
                        return stdout
            time.sleep(0.5)
            counter += 1
        raise AVException('After 10 tries, log is still empty')

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()
        return stdout

    def on_scan_exit_fail(self, result):
        raise AVException(result.strip())

    def _perform_scan_command(self, command):
        if not command:
            raise AVException('No command specified')
        try:
            result = self.subprocess.Popen(command, shell=True)
            return self.on_scan_exit_ok(result)
        except self.subprocess.CalledProcessError as error:
            result = error.output.decode()
            return self.on_scan_exit_fail(result)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*PrevJobTime\s*REG_QWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.fromtimestamp(int(last_update_time, 16))
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
