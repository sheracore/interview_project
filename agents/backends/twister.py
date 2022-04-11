from .core import AVBackend
from agents.exceptions import AVException
import time
import string


class TwisterBackend(AVBackend):

    av_name = 'twister'
    title = 'Twister'
    scan_command = r'"C:\Program Files (x86)\Filseclab\Twister\twsscan.exe"'
    exe_file_path = r'C:\Program Files (x86)\Filseclab\Twister\twsscan.exe'
    log_path = r'C:\Program Files (x86)\Filseclab\Twister\logs'
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
        self.pathlib = self.conn.modules.pathlib.Path
        files = sorted(self.pathlib(self.log_path).iterdir(), key=self.os.path.getmtime)
        if len(files) > 1:
            for file in files:
                if file == files[0]:
                    continue
                elif file.name.endswith('.scn'):
                    self.os.system(f'del /f "{self.log_path}\\{file.name}"')
        try:
            return super().scan(path)
        finally:
            self.os.system('taskkill /f /im twsscan.exe')

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        while counter < 10:
            files = sorted(self.pathlib(self.log_path).iterdir(), key=self.os.path.getmtime)
            for file in files:
                if file == files[0]:
                    continue
                elif file.name.endswith('.scn'):
                    path = self.log_path + '\\' + file.name
                    with self.open(path, 'r', encoding="latin1") as f:
                        stdout = f.read()
                        if stdout:
                            stdout = "".join(filter(lambda x: x in set(string.printable), stdout))
                            return stdout
            time.sleep(0.5)
            counter += 1

        raise AVException('After 10 tries, log is still empty')

    def on_scan_exit_fail(self, result):
        raise AVException(result.strip())

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()
        return stdout

    def get_infected_num(self, stdout):
        return stdout.count("Virus.")

    def _perform_scan_command(self, command):
        if not command:
            raise AVException(
                f'No command specified')
        try:
            result = self.subprocess.Popen(command, shell=True)
            return self.on_scan_exit_ok(result)
        except self.subprocess.CalledProcessError as error:
            result = error.output.decode()
            return self.on_scan_exit_fail(result)
