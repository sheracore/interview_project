from .core import AVBackend
from agents.exceptions import AVException


class ArcabitBackend(AVBackend):
    """
        C:\test.txt        CLEAN
        C:\eicar.txt       INFECTED        EICAR-Test_File (not a virus)
    """
    av_name = 'arcabit'
    title = 'Arcabit'
    scan_command = r'"C:\Program Files\Arcabit\bin\amcmd.exe"'

    def check(self):
        if self.os.path.exists(r"C:\Program Files\Arcabit\bin\amcmd.exe"):
            return True
        else:
            raise AVException(f'{self.scan_command} path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        return super().scan(f'"{path}"')

    def get_infected_num(self, stdout):
        if 'INFECTED' in stdout:
            return 1
        elif 'CLEAN' in stdout:
            return 0
        raise AVException(f'Invalid stdout: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)
