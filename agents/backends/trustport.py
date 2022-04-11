from .core import AVBackend
from agents.exceptions import AVException
import time
import uuid
import xml.etree.ElementTree as ET


class TrustportBackend(AVBackend):
    """
        <scanreport>
        <filereport engine="TrustPort" path="C:\test2.txt" origpath="C:\test2.txt" result="-1604" resid="11057"
         restext="Infected!" name="EICAR (Test file)" cleanresult="1620" cleanrestext="Omitted"></filereport>
        </scanreport>
        <statistics>
            <bootrecord scanned="0" infected="0" repaired="0"></bootrecord>
            <filereport scanned="1" infected="0" repaired="0" renamed="0" quarantined="0" deleted="0"></filereport>
            <regreport scanned="0" infected="0" repaired="0" deleted="0"></regreport>
        </statistics>
    """

    av_name = 'trustport'
    title = 'TrustPort'
    scan_command = r'"C:\Program Files (x86)\TrustPort\Antivirus\bin\avcc.exe" -nms -rs'
    exe_file_path = r'C:\Program Files (x86)\TrustPort\Antivirus\bin\avcc.exe'
    log_path = ''

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
        self.log_path = rf'{self.settings.MEDIA_ROOT}\TP_{str(uuid.uuid4())}.xml'
        return super().scan(f'-r="{self.log_path}" "{path}"')

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        complete_log = False
        while counter < 10:
            if self.os.path.exists(self.log_path):
                with self.open(self.log_path, 'r', encoding="utf-16") as f:
                    stdout = f.read()
                    if stdout and 'scanprotocol' in stdout:
                        complete_log = True
                        break
            time.sleep(0.5)
            counter += 1
        self.os.remove(self.log_path)
        if complete_log:
            return stdout
        raise AVException('After 10 tries, log is still empty')

    def on_scan_exit_ok(self, result):
        stdout = self.read_stdout_from_scan_log()
        return stdout

    def on_scan_exit_fail(self, result):
        raise AVException(result.strip())

    def get_infected_num(self, stdout):
        if 'scanreport' not in stdout:
            raise AVException('Invalid log file!')
        tree = ET.fromstring(stdout)
        scan_report = tree.find('scanreport')
        return len(scan_report.getchildren())

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
