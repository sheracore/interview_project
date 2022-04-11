from .core import AVBackend
from agents.exceptions import AVException
import re
import time
from dateutil.parser import parse


class Totalsecurity360Backend(AVBackend):
    """
    360 Total Security Scan Log\n\nScan Time:2021-12-11 13:02:03\nTime Taken:00:00:01\nObject(s) Scanned:1\n
    Threat(s) Found:1\nThreat(s) Resolved:0\n\nScan Settings\n----------------------\nCompressed Files Scan:No\n
    Scan Engine:KunPeng engine is disabled\n\nScan Scope\n----------------------\nC:\\test.txt\n\nScan Result\n
    ======================\n High-risk Items\n----------------------\n
    C:\\test.txt 44D88612FEA8A8F36DE82E1278ABB02F 3395856CE81F2B7382DEE72602F798B642F14140 70,6,2,4,280,1,256, ||
     0_0_0  [QEX script killing engine][qex.eicar.gen.gen][Quarantined files][]\n\n
    """

    av_name = 'totalsecurity360'
    title = '360 Total Security'
    scan_command = r'"C:\Program Files (x86)\360\Total Security\QHSafeMain.exe" sysmenu'
    exe_file_path = r'C:\Program Files (x86)\360\Total Security\QHSafeMain.exe'
    log_path = r'C:\Program Files (x86)\360\Total Security\Logs\Administrators\virusscan'
    infected_pattern = r'^.*Threat\(s\) Found:\s*(?P<infected>\d+)'
    last_scan_time = ''
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\360TotalSecurity\Update" /v "LastUpdateTime"'

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.exe_file_path}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)

        scan_file = rf'{self.settings.MEDIA_ROOT}\scan_file.txt'
        with self.open(scan_file, 'w') as f:
            f.write(f'[app]\n0={path}')
        files = self.os.listdir(self.log_path)

        self.subprocess.Popen(r'"C:\Program Files (x86)\360\Total Security\safemon\360SPTool.exe" /disablesp 1',
                              shell=True)
        counter = 0
        time.sleep(0.5)
        while counter < 10:
            window = self.pywinauto.findwindows.find_windows(class_name='Q360HIPSClass')
            if window:
                main_app = self.pywinauto.Application(allow_magic_lookup=False)
                app = main_app.connect(handle=window[0])
                if app['Q360HIPSClass']['Button2'] and 'Yes' in app['Q360HIPSClass']['Button2'].texts():
                    app['Q360HIPSClass']['Button2'].click()
                    app['Q360HIPSClass']['&Yes'].click()
                    break
            time.sleep(0.5)
            counter += 1
        for file in files:
            if file.endswith('.log'):
                self.os.remove(self.log_path + '\\' + file)
        self.last_scan_time = self.get_last_scan_time_from_reg()
        return super().scan(scan_file)

    def get_last_scan_time_from_reg(self):
        get_last_scan_time_cmd = r'reg query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\360TotalSecurity\DeepScan" /v ' \
                                 r'"lastscantime" /s'
        last_scan_time_pattern = r'^.*lastscantime\s*REG_DWORD\s*(?P<last_scan_time>0x[a-fA-F0-9]+)'
        result = self.invoke.run(get_last_scan_time_cmd, warn=True)
        if result.exited == 0 and result.ok:
            m = re.match(last_scan_time_pattern, repr(result.stdout))
            if m:
                return m.groupdict()['last_scan_time']

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(1)
        while counter < 10:
            if self.last_scan_time != self.get_last_scan_time_from_reg():
                window_360 = self.pywinauto.findwindows.find_windows(class_name='Q360InternationSafeClass')
                main_app = self.pywinauto.Application(allow_magic_lookup=False)
                app = main_app.connect(handle=window_360[0])
                try:
                    app['Q360InternationSafeClass'].close()
                except:
                    pass
                if self.pywinauto.findwindows.find_windows(class_name='Q360HIPSClass'):
                    app['Q360InternationSafeClass'].send_message(self.pywinauto.win32defines.WM_ENDSESSION)
                break
            time.sleep(1)
            counter += 1

        counter = 0
        time.sleep(0.5)
        while counter < 10:
            files = self.os.listdir(self.log_path)
            for file in files:
                if file.endswith('.log'):
                    path = self.log_path + '\\' + file
                    with self.open(path, 'r', encoding="utf-16") as f:
                        stdout = f.read()
                        if stdout:
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
        m = re.match(r'^.*LastUpdateTime\s*REG_SZ\s*(?P<last_update_time>\d+-\d+-\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
