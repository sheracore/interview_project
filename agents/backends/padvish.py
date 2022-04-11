import re

from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class PadvishBackend(AVBackend):
    """
    Sample outputput of padvish:
        [
            {
                "FilePath" : "C:\\Padvish\\app2.py",
                "FileStatus" : "Clean",
                "MalwareName" : "",
                "PadvishVersion" : "2.3.190.2675",
                "UpdateTime" : "1529959081",
            }
        ]
    """
    av_name = 'padvish'
    title = 'Padvish'
    exec_process = 'APCcSvc.exe'  # or PadvishUI.exe
    scan_command = r'"C:\Padvish\PadvishVirusKav.exe"'
    # scan_time_pattern = ''
    infected_pattern = r'^.*"FileStatus"\s*:\s*"(?P<infected>\S+)",'
    last_update_command = r'dir /T:W "C:\Program Files (x86)\Padvish AV"'
    version_command = r'reg query HKLM\software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\AmnPardazAntiVirus /v DisplayVersion'

    def on_scan_exit_ok(self, result):
        m = re.match(
            r'^.*"FileStatus"\s*:\s*"(?P<status>.+)"', repr(result.stdout)
        )
        if m:
            if m.groupdict()['status'] == 'AccessDenied':
                raise AVException('Access denied')
            elif m.groupdict()['status'] == 'Scan Failed':
                raise AVException('Scan Failed (The license may have expired)')
            else:
                return result.stdout.strip()
        else:
            raise AVException(f'Invalid pattern to check file status: {result.stdout.strip()}')

    def check(self):
        status = self._perform_command(f'tasklist /FI "IMAGENAME eq {self.exec_process}" /NH')
        """
        if process is running return something like this, else return None
        av_name.exe                 5580 Console                    1     37,128 K
        """
        if 'No tasks are running' not in status and self.os.path.exists(r"C:\Padvish\PadvishVirusKav.exe"):
            return True
        else:
            raise AVException(f'"{self.exec_process} is not Running')

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            infected = m.groupdict()['infected']
            if infected == 'Clean':
                return 0
            elif infected == 'Malware':
                return 1
            else:
                raise AVException(f'Infected type not recognized in: {stdout}')
        else:
            raise AVException(f'Infected pattern not found in: {stdout}')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_name = self.os.path.split(path)[-1]
        dst = self.settings.MEDIA_ROOT + '\\' + file_name
        try:
            self.shutil.copyfile(path, dst)
            return super().scan('-s', f'"{dst}"')
        finally:
            if self.os.path.exists(dst):
                self.os.remove(dst)

    def get_version(self):
        output = self._perform_command(self.version_command)
        version = output.split(' ')[-1]
        return version

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.findall(r'.*(?P<modify_date>\d+/\d+/\d+)', repr(output))
        if m:
            dates = []
            for i in m:
                date = parse(i).date()
                dates.append(date)
            return max(dates)
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')

    def update(self, path):
        update_file_path = self.settings.MEDIA_ROOT + "\\" + "update_files"
        if not self.os.path.exists(update_file_path):
            self.os.mkdir(update_file_path)
        file_path = path.replace('/smb/', 'Z:/').replace('/', '\\')

        try:
            final_path = self.extract(file_path=file_path, dst=update_file_path)
            gen = self.os.walk(final_path)
            for i in gen:
                for file in i[2]:
                    nested_file_path = self.os.path.join(i[0], file)
                    stdout = self._perform_command(fr'"C:\Padvish\PadvishVirusKav.exe" -u "{nested_file_path}"')
                    if stdout.lower() == 'update bundle failed':
                        raise AVException(stdout)
            return True

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            self.shutil.rmtree(update_file_path)




