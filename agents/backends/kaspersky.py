import re
from py7zr.helpers import filetime_to_dt
from .core import AVBackend
from agents.exceptions import AVException


class KasperskyBackend(AVBackend):
    """
    ; --- Settings ---
    ; Action on detect:     Report only
    ; Scan objects: All objects
    ; Use iChecker: Yes
    ; Use iSwift:   Yes
    ; Try disinfect:        No
    ; Try delete:   No
    ; Try delete container: No
    ; Scan archives:        No
    ; Exclude by mask:      No
    ; Include by mask:      No
    ; Objects to scan:
    ;       "C:\eicar.com.txt"      Enable = Yes    Recursive = No
    ; ------------------
    2021-05-17 12:14:50     Scan_Objects$2123                          starting   1%
    2021-05-17 12:14:50     Scan_Objects$2123                          running    1%
    2021-05-17 12:14:52     C:\eicar.com.txt        detected        EICAR-Test-File
    2021-05-17 12:14:52     C:\eicar.com.txt        skipped
    2021-05-17 12:14:52     Scan_Objects$2123                          completed
    Info: task 'ods' finished, last error code 0
    ;  --- Statistics ---
    ; Time Start:   2021-05-17 12:14:50
    ; Time Finish:  2021-05-17 12:14:52
    ; Processed objects:    1
    ; Total OK:     0
    ; Total detected:       1
    ; Suspicions:   0
    ; Total skipped:        0
    ; Password protected:   0
    ; Corrupted:    0
    ; Errors:       0
    ;  ------------------
    """
    av_name = 'kaspersky'
    title = 'Kaspersky Security Cloud 21.3'
    scan_command = r'"C:\Program Files (x86)\Kaspersky Lab\Kaspersky Security Cloud 21.3\avp.com"'
    infected_pattern = r'^.*Total detected:[\\t]*(?P<infected>\d+)[\\n]*'
    version_command = r'reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\S-1-5-18\Products\8B21A2FF7BEA0C84598C2E3E6DD7CF2B\InstallProperties /v DisplayVersion'
    update_command = r'"C:\Program Files (x86)\Kaspersky Lab\Kaspersky Security Cloud 21.3\avp.com" update'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\KasperskyLab\AVP21.3\Data" /v "LastSuccessfulUpdate"'

    def on_scan_exit_fail(self, result):
        if result.exited in {2, 3}:  # 2 for clean and infected
            return result.stdout
        else:
            return super().on_scan_exit_fail(result)

    def on_scan_exit_ok(self, result):
        m = re.match(r'^.*Processed objects:[\\t]*(?P<processed>\d+)[\\n]*', repr(result.stdout))
        if m:
            if int(m.groupdict()['processed']) == 0:
                raise AVException(f'Seems that nothing was scanned: {result.stdout.strip()}')
            else:
                return result.stdout.strip()
        else:
            raise AVException(f'Invalid pattern to check number of objects processed: {result.stdout.strip()}')

    def check(self):
        if self.os.path.exists(r"C:\Program Files (x86)\Kaspersky Lab\Kaspersky Security Cloud 21.3\avp.com"):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan('scan', f'"{path}"')

    def get_version(self):
        output = self._perform_command(self.version_command)
        version = output.split(' ')[-1]
        return version

    def update(self, path):
        update_path = r'C:\Users\Fwutech\Desktop\Kaspersky-Update-Files'
        file_path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        for files in self.os.listdir(update_path):
            path = self.os.path.join(update_path, files)
            try:
                self.shutil.rmtree(path)
            except OSError:
                self.os.remove(path)
        try:
            self.extract(file_path=file_path, dst=update_path)
            result = self._perform_command(self.update_command)
            return True
        except Exception as ex:
            raise AVException(str(ex))

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*LastSuccessfulUpdate\s*REG_QWORD\s*(?P<last_update_time>0x[0-9a-fA-F]+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return filetime_to_dt(int(last_update_time, 16)).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
