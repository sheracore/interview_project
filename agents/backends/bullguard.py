from py7zr.helpers import filetime_to_dt
from .core import AVBackend
from agents.exceptions import AVException
import re
import time
import xml.etree.ElementTree as ET


class BullguardBackend(AVBackend):
    """
    ><FilesScanned>2</FilesScanned><ScanSpeed>2.00 files/sec</ScanSpeed><FilesSkipped>0</FilesSkipped><Problems>1</Problems>
    <RkFilesScanned>0</RkFilesScanned></Statistics><Problems><Infected><Item><Path>c:\test\eicar.com</Path><SubItems><SubItem>
    <Path>C:\test\eicar.com</Path><VirusName>Eicar-Test-Signature</VirusName><Type>1</Type><Status>2</Status><ActionsPerformed/>
    </SubItem></SubItems></Item></Infected><Skipped/></Problems></Antivirus>
    """
    av_name = 'bullguard'
    title = 'Bullguard'
    scan_command = r'"C:\Program Files\BullGuard Ltd\BullGuard\BgScan.exe"'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\BullGuard Ltd.\BullGuard\Update\Information" /v "LastUpdate"'
    log_path = r"C:\Users\fwutech\AppData\Roaming\BullGuard\Antivirus\ScanLogs"

    def close_window(self):
        counter = 0
        time.sleep(0.5)
        complete = False
        while counter < 10 and not complete:
            windows = self.pywinauto.findwindows.find_windows(title='BullGuard Scan')
            main_app = self.pywinauto.Application(allow_magic_lookup=False)
            for win in windows:
                complete = True
                app = main_app.connect(handle=win)
                if app['BullGuard Scan']['Button1'] and 'Close' in app['BullGuard Scan']['Button1'].texts():
                    app['BullGuard Scan']['Button1'].click()
                elif app['BullGuard Scan']['Button2'] and 'Cancel' in app['BullGuard Scan']['Button2'].texts():
                    app['BullGuard Scan']['Button2'].click()
                else:
                    complete = False
            time.sleep(0.5)
            counter += 1

    def read_stdout_from_scan_log(self):
        scan_complete = False
        counter = 0
        time.sleep(0.5)
        while (not scan_complete) and (counter < 10):
            if self.os.path.exists(self.log_path):
                files = self.os.listdir(self.log_path)
                for file in files:
                    if file.startswith('Custom'):
                        path = self.log_path + '\\' + file
                        with self.open(path, 'r') as f:
                            stdout = f.read()
                            if stdout:
                                self.close_window()
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
        tree = ET.fromstring(stdout)
        infected = tree[2].find('Problems').text
        if int(infected) == 0 or 1:
            return int(infected)
        else:
            raise AVException(f'Seems that nothing was scanned: {stdout}')

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

    def check(self):
        if self.os.path.exists(r"C:\Program Files\BullGuard Ltd\BullGuard\BgScan.exe"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        if self.os.path.exists(self.log_path):
            files = self.os.listdir(self.log_path)
            for file in files:
                if file.startswith('Custom'):
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

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LastUpdate\s*REG_BINARY\s*(?P<last_update_time>[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            time_list = re.findall('..', last_update_time)
            time_list = list(map(lambda x: int(x, 16), time_list))
            last_update_time = filetime_to_dt(((((((time_list[7]*256 + time_list[6])*256 + time_list[5])*256 +
                                                  time_list[4])*256 + time_list[3])*256 + time_list[2])*256 +
                                               time_list[1])*256 + time_list[0])
            return last_update_time.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
