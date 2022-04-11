from .core import AVBackend
from agents.exceptions import AVException
import re
import time
from dateutil.parser import parse


class VipreBackend(AVBackend):
    """
    TRA 	4220	4256	10/03 11:28:03.820	SBAMSvcLib	CSBWow64Helper::DisableWow64FsRedirection:	Wow64DisableWow64FsRedirection succeeded; Wow64FsRedirection is disabled.
    TRA 	4220	4256	10/03 11:28:10.837	SBAMSvcLib	CSBWow64Helper::RevertWow64FsRedirection:	Wow64RevertWow64FsRedirection succeeded; Wow64FsRedirection is enabled.
    TRA 	4220	4256	10/03 11:28:10.837	SBScanControl	CSBScanControlImpl::ScanFile:	File <C:\test\eicar.com> has threat id <20000001> (0 - not a threat).
    """

    av_name = 'vipre'
    title = 'Vipre'
    scan_command = r'"C:\Program Files (x86)\VIPRE\SBAMCommandLineScanner.exe"'
    infected_pattern = r'^.*\s*has\s*threat\s*id\s*<(?P<infected>\d+)>'
    version_command = ''
    last_update_command = r'"C:\Program Files (x86)\VIPRE\SBAMCommandLineScanner.exe" /displaylocaldefversion'

    def check(self):
        if self.os.path.exists(r"C:\Program Files (x86)\VIPRE\SBAMCommandLineScanner.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            if int(m.groupdict()['infected']) != 0:
                return 1
            else:
                return 0
        else:
            raise AVException(f'Infected pattern not found in following stdout: {stdout}')

    def on_scan_exit_fail(self, result):
        if result.exited == 1:
            return self.read_scan_stdout()
        else:
            return super().on_scan_exit_fail(result)

    def on_scan_exit_ok(self, result):
        return self.read_scan_stdout()

    def read_scan_stdout(self):
        scan_complete = False
        counter = 0
        time.sleep(0.5)
        max_retries = 10
        while (not scan_complete) and (counter < 10):
            with self.open(r"C:\ProgramData\VIPRE\Logs\SBAMSvcLog.csv", "rb") as f:
                stdout = f.read().decode("utf-16")
                if stdout:
                    scan_complete = True
                    break
            time.sleep(0.5)
            counter += 1
        if scan_complete:
            if "Didn't get any result" in stdout:
                raise AVException(
                    f'Invalid pattern to check number of objects processed: {stdout}')
            else:
                return stdout

        else:
            raise AVException(f'After {max_retries} tries, log is still empty')

    def scan(self, path):
        if self.os.path.exists(r"C:\ProgramData\VIPRE\Logs\SBAMSvcLog.csv"):
            self.os.remove(r"C:\ProgramData\VIPRE\Logs\SBAMSvcLog.csv")
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        path = r'\\192.168.100.1' + path.replace('/', '\\')
        file_name = self.os.path.split(path)[-1]
        dst = self.settings.MEDIA_ROOT + '\\' + file_name
        try:
            self.shutil.copyfile(path, dst)
            return super().scan('/scanfile', f'"{dst}"')
        except Exception as ex:
            raise AVException(str(ex))
        finally:
            if self.os.path.exists(dst):
                self.os.remove(dst)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        """
            99434 - 2022-02-27T07:20:00
        """
        m = re.match(r'^.*\d+ \- (?P<last_update_time>\d+-\d+-\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')

    def update(self, path):
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_path = r'\\192.168.100.1' + path.replace('/', '\\')

        try:
            final_path = self.extract(file_path=file_path, dst=self.settings.MEDIA_ROOT)
            gen = self.os.walk(final_path)
            for i in gen:
                for file in i[2]:
                    nested_file_path = self.os.path.join(i[0], file)
                    self._perform_command(f'"c:\Program Files (x86)\VIPRE\SBAMCommandLineScanner.exe" /applydefs {nested_file_path}')
                    self._perform_command('"c:\Program Files (x86)\VIPRE\SBAMCommandLineScanner.exe" /updatedefs')
            return True

        except Exception as ex:
            raise AVException(str(ex))
