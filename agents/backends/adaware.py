import re
import uuid
from datetime import datetime
from .core import AVBackend
from agents.exceptions import AVException


class AdawareBackend(AVBackend):
    r"""
    "C:\AdAwareCommandLineScanner\adawareCommandLineScanner.exe" --scan-archives --scan-result-stdou --custom "C:/01.exe"
    Initializing engine, please wait...
    Initializing engine completed
    Scan started
    Object Path: C:\01.exe. Parent Containers: (null). Inner Object: (null)

    <?xml version="1.0"?>
    <Summary>
        <ScanInfo ScanType="Custom" StartTime="20220110T154520.487692" EndTime="20220110T154533.487545" />
        <ScanPaths>
                <Path Value="C:/01.exe" />
        </ScanPaths>
        <InfectedObjects>
                <InfectedObject ObjectType="File" ObjectPath="C:\01.exe" ParentContainers="" InnerObject="" ObjectFlags="" ArchiveFlags="0" ScanStatus="Infected" ScanStatusFlags="0" ThreatType="Virus" Pid="0" RegKey="0" ThreatName="EICAR-Test-File (not a virus)" SysObjParentContainers="" SysObjInnerObject="" TempPath="" DepthLevel="0" ScanAction="None" />
        </InfectedObjects>
    </Summary>
    """
    av_name = 'adaware'
    title = 'Adaware'
    scan_command = r'"C:\AdAwareCommandLineScanner\adawareCommandLineScanner.exe"'
    scan_completed_pattern = r'^.*\s*(?P<completed>Scan complete)'
    infected_pattern = r'^.*ScanStatus=\"(?P<infected>\S*)\"'
    scan_time_pattern = r'^.*Request duration:\s*(?P<scan_time>\S*)'
    file_path_pattern = r'^.*Object Path: (?P<file_path>\S*)'
    thread_pattern = r"^.*ThreatName=\"(?P<thraet>\S*)"
    last_update_command = r'"C:\AdAwareCommandLineScanner\adawareCommandLineScanner.exe" --definitions-info'

    def check(self):
        if self.os.path.exists(self.scan_command.replace('"', '')):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_ok(self, result):
        m = re.match(self.file_path_pattern, repr(result.stdout.strip()))
        if m:
            return result.stdout.strip()
        else:
            raise AVException(f'Could not open/read file')

    def get_infected_num(self, stdout):
        if not self.infected_pattern:
            raise AVException('Infected pattern not specified')

        completed = re.match(self.scan_completed_pattern, repr(stdout))
        m = re.match(self.infected_pattern, repr(stdout))
        if m:
            if m.groupdict()['infected'] == 'Infected':
                return 1
        else:
            if completed.groupdict()['completed'] == 'Scan complete':
                return 0
            raise AVException(f'Infected pattern not found in following stdout: {stdout}')

    def get_scan_time(self, stdout):
        m = re.match(self.scan_time_pattern, repr(stdout))
        time_string = m.groupdict()['scan_time'].replace("'", '')
        date_time = datetime.strptime(time_string, "%H:%M:%S.%f")
        a_timedelta = date_time - datetime(1900, 1, 1)
        seconds = a_timedelta.total_seconds()
        if m:
            return float(seconds)
        else:
            raise AVException(f'Scan time pattern not found in following stdout: {stdout}')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        return super().scan('--scan-archives --scan-result-stdou --custom', f'"{path}"')

    def update(self, path):
        zip_path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        path = self.scan_command.replace('"', '')
        path = '\\'.join(path.split('\\')[0:-1])
        path_old = f"{path}-{str(uuid.uuid4())}"
        try:
            if self.os.path.exists(path):
                self.shutil.move(path, path_old)
                self.extract(file_path=zip_path, dst=r'C:\\')
                self.shutil.rmtree(path_old)
            else:
                self.extract(file_path=zip_path, dst=r'C:\\')
            return True

        except Exception as ex:
            if self.os.path.exists(path) and self.os.path.exists(path_old):
                self.shutil.rmtree(path)
                self.shutil.move(path_old, path)
            raise AVException(str(ex)) 

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*Database release date: (?P<last_update_time>\d+\/\d+\/\d+)', repr(output))
        if m:
            last_update = m.groupdict()['last_update_time']
            last_update = datetime.strptime(last_update, '%m/%d/%Y')
            return last_update.date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
