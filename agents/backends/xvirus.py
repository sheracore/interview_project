from .core import AVBackend
from agents.exceptions import AVException
import time
import re
from dateutil.parser import parse


class XvirusBackend(AVBackend):
    """
        Xvirus Anti-Malware Scan Report
        Date/Time 11/28/2021 11:40:34 AM
        Scanned Files 1
        Detected Threats 1
        C:\test.txt|Malware
    """

    av_name = 'xvirus'
    title = 'Xvirus'
    scan_command = r'"C:\Program Files (x86)\Xvirus Anti-Malware\shellfile.exe"'
    exe_file_path = r'C:\Program Files (x86)\Xvirus Anti-Malware\shellfile.exe'
    infected_pattern = r'^.*Detected Threats \s*(?P<infected>\d+)'
    log_path = r'C:\Program Files (x86)\Xvirus Anti-Malware\logs'
    pathlib = ''

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.exe_file_path}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        files = self.os.listdir(self.log_path)
        for file in files:
            if file.startswith('scanlog'):
                self.os.remove(self.log_path + '\\' + file)
        return super().scan(path)

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        while counter < 20:
            files = self.os.listdir(self.log_path)
            for file in files:
                if file.startswith('scanlog'):
                    path = self.log_path + '\\' + file
                    with self.open(path, 'r') as f:
                        stdout = f.read()
                        if stdout:
                            return stdout
            time.sleep(0.5)
            counter += 1
        raise AVException('After 20 tries, log is still empty')

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()
        return stdout

    def get_last_update(self):
        self.pathlib = self.conn.modules.pathlib.Path
        files = sorted(filter(lambda x: x.name.startswith('updatelog'), self.pathlib(self.log_path).iterdir()),
                       key=self.os.path.getmtime)
        if not files:
            raise AVException(f'Update log file does not exists!')

        update_log_file = files[-1]
        with self.open(update_log_file, 'r') as f:
            output = f.read()
        m = re.match(r'^.*Date\/Time (?P<last_update_time>\d+\/\d+\/\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
