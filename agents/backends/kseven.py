import re
import time
from datetime import datetime
from .core import AVBackend
from agents.exceptions import AVException


class KsevenBackend(AVBackend):
    """
        Files Found\t\t :  1\r\n\r\n
        Files Scanned\t\t :  1\r\n\r\n
        Files Infected\t\t :  None\r\n\r\n
        Partition Table Scanned\t :  None\r\n\r\n
        Boot Sectors Scanned\t :  None\r\n\r\n
        Issues to be fixed               \t :  None\r\n\r\n\r\n
    """
    av_name = 'kseven'
    title = 'KSeven'
    scan_command = r'"C:\Program Files (x86)\K7 Computing\K7TSecurity\K7AVScan.exe"'
    infected_pattern = r'.*Files Infected[\\t \s]*:\s*(?P<infected>\d|None+)'
    scanned_pattern = r'.*Files Scanned[\\t \s]*:\s*(?P<scanned>\d|None+)'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\K7 Computing\K7TotalSecurity\CommonInfo\Updates" /v "LastUpdatedOn"'

    def check(self):
        if self.os.path.exists(r"C:\Program Files (x86)\K7 Computing\K7TSecurity\K7AVScan.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if self.os.path.exists(path):
            return super().scan(f'"{path}"')
        raise AVException(f'{path} does not exist')

    def on_scan_exit_ok(self, result):
        counter = 0
        time.sleep(0.5)
        while counter < 10:
            window = self.pywinauto.findwindows.find_windows(class_name='K7WndClass')
            if window:
                main_app = self.pywinauto.Application(allow_magic_lookup=False)
                app = main_app.connect(handle=window[0])
                scan_completed_text = app['K7WndClass'].child_window(control_id=210)
                if scan_completed_text.exists() and scan_completed_text.texts() and 'Scan Completed.' in scan_completed_text.texts()[0]:
                    stdout = app['K7WndClass']['RICHEDIT1'].texts()
                    if stdout:
                        stdout = stdout[0]
                        if 'Close' in app['K7WndClass']['K7CustomBtnV16'].texts():
                            app['K7WndClass']['K7CustomBtnV16'].click()
                        return stdout
            time.sleep(0.5)
            counter += 1
        raise AVException('After 10 tries, log is still invalid!')

    def on_scan_exit_fail(self, result):
        raise AVException(result.strip())

    def get_infected_num(self, stdout):
        m = re.match(self.scanned_pattern, repr(stdout))
        if m:
            scanned = m.groupdict()['scanned']
            if scanned == 'None':
                raise AVException('File is not scanned!')
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            infected = m.groupdict()['infected']
            if infected == 'None':
                return 0
            return int(infected)
        else:
            raise AVException(f'Infected pattern not found in following stdout: {stdout}')

    def _perform_scan_command(self, command):
        if not command:
            raise AVException('No command specified')
        try:
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
            gen = self.os.walk(final_path)
            for i in gen:
                for file in i[2]:
                    nested_file_path = self.os.path.join(i[0], file)
                    result = self._perform_command(f'{nested_file_path} /s')
            return True

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            self.shutil.rmtree(self.settings.MEDIA_ROOT)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LastUpdatedOn\s*REG_DWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            last_update_time = datetime.fromtimestamp(int(last_update_time, 16))
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
