import re
import time
from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class QuickhealBackend(AVBackend):
    """
    Scan started at:17:11:45
    Scan finished at:17:11:49
    Boot/Partition viruses   - 0
    Files scanned   - 1
    Files quarantined   - 1
    Files deleted   - 0
    Threats detected   - 1
    Files repaired   - 0
    Archive/Packed   - 0
    DNAScan warnings   - 0
    Adware detected   - 0
    """
    av_name = 'quickheal'
    title = 'QuickHeal'
    scan_command = r'"C:\Program Files\Quick Heal\Quick Heal AntiVirus Pro\scanner.exe" /silent'
    exe_file_path = r'C:\Program Files\Quick Heal\Quick Heal AntiVirus Pro\scanner.exe'
    log_path = r'C:\Program Files\Quick Heal\Quick Heal AntiVirus Pro\REPORT'
    scan_time_pattern = r''
    infected_pattern = r'^.*Threats detected\s\s\s-\s(?P<infected>\d+)'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\Quick Heal\Quick Heal Antivirus Pro" ' \
                          r'/v "LatestVirusDefsDate"'
    version_command = r''
    update_command = r'"C:\Program Files\Quick Heal\Quick Heal AntiVirus Pro\QUICKUP.EXE" /qhdir*'

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        files = self.os.listdir(self.log_path)
        files = list(filter(lambda x: x.startswith("SCN") and x.endswith('.SNR'), files))
        for file in files:
            self.os.remove(self.log_path + '\\' + file)
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        file_name = self.os.path.split(path)[-1]
        dst = self.settings.MEDIA_ROOT + '\\' + file_name
        try:
            self.shutil.copyfile(path, dst)
            return super().scan(f'"{dst}"')
        except Exception as ex:
            raise AVException(str(ex))
        finally:
            if self.os.path.exists(dst):
                self.os.remove(dst)

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        while counter < 10:
            files = self.os.listdir(self.log_path)
            files = list(filter(lambda x: x.startswith("SCN") and x.endswith('.SNR'), files))
            for file in files:
                path = self.log_path + '\\' + file
                with self.open(path, 'rb') as f:
                    stdout = f.read().decode("utf-16")
                    if stdout and 'Scan finished' in stdout:
                        return stdout
            time.sleep(0.5)
            counter += 1
        raise AVException('After 10 tries, log is still empty')

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()
        return stdout

    def on_scan_exit_fail(self, result):
        raise AVException(result.strip())

    def get_scan_time(self, stdout):
        start = re.match(r"^.*Scan started at:(?P<start>\d+:\d+)", repr(stdout))
        finish = re.match(r"^.*Scan finished at:(?P<finish>\d+:\d+)", repr(stdout))
        if start and finish:
            scan_time = int(finish.groupdict()['finish'].replace(':', '')) -\
                        int(start.groupdict()['start'].replace(':', ''))
            return scan_time
        else:
            raise AVException(f'Scan time pattern not found in following stdout: {stdout}')

    def _perform_scan_command(self, command):
        if not command:
            raise AVException('No command specified')
        try:
            self.os.system(r'taskkill /f /im "quhlpsvc.exe" /t')
            result = self.subprocess.Popen(command, shell=True)
            return self.on_scan_exit_ok(result)
        except self.subprocess.CalledProcessError as error:
            result = error.output.decode()
            return self.on_scan_exit_fail(result)

    def update(self, path):
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_path = path.replace('/smb/', 'Z:/').replace('/', '\\')

        try:
            final_path = self.extract(file_path=file_path, dst=self.settings.MEDIA_ROOT)
            self.subprocess.Popen(f'{self.update_command}{final_path}', shell=True)
            counter = 0
            time.sleep(0.5)
            while not self.pywinauto.findwindows.find_windows(title='Quick Update') and counter < 10:
                time.sleep(0.5)
                counter += 1
                continue
            if not self.pywinauto.findwindows.find_windows(title='Quick Update'):
                raise AVException('Update process does not start')
            counter = 0
            time.sleep(0.5)
            while counter < 10:
                window_qh = self.pywinauto.findwindows.find_windows(title='Quick Update')
                main_app = self.pywinauto.Application(allow_magic_lookup=False)
                app = main_app.connect(handle=window_qh[0])
                if app['Quick Update']['&Finish'].exists():
                    app['Quick Update']['&Finish'].click()
                    return True
                time.sleep(0.5)
                counter += 1
            raise AVException('Update process does not finished after 10 tries')

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            if self.os.path.exists(self.settings.MEDIA_ROOT):
                self.shutil.rmtree(self.settings.MEDIA_ROOT)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LatestVirusDefsDate\s*REG_SZ\s*(?P<last_update_time>\d+.-\d+.-\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
