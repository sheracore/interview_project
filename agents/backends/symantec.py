import re
import time
from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class SymantecBackend(AVBackend):
    """
    fwutech-symantec rtvscand: Scan Complete:  Threats: 0   Scanned: 1   Files/Folders/Drives Omitted: 0
    """
    av_name = 'symantec'
    title = 'Symantec'
    service_name = 'rtvscand'
    scan_command = '/opt/Symantec/symantec_antivirus/sav'
    infected_pattern = r'^.*Threats:\s*(?P<infected>\d+)'
    version_command = '/opt/Symantec/symantec_antivirus/sav info -p'
    license_command = '/opt/Symantec/symantec_antivirus/sav manage -l'
    last_update_command = '/opt/Symantec/symantec_antivirus/sav info -d'
    """
    Product Type: Enterprise
    Category Type: Never Expires
    Expiration Status: Not Expired
    """

    def on_scan_exit_ok(self, result):
        scan_complete = False
        counter = 0
        while (not scan_complete) and (counter < 10):
            """
            To avoid conflict between scans log, we need run celery service with --concurrency=1 
            Because we do not want the syslog file to be rewritten for another scan.  
            """
            with self.open("/var/log/syslog", "r") as f:
                if "rtvscand: Scan Complete" in f.read():
                    scan_complete = True
                    break
            time.sleep(1)
            counter += 1
        if scan_complete:
            stdout = self._perform_command('cat /var/log/syslog | grep -i "rtvscand: Scan Complete"')  # find log of last scan from syslog
            m = re.match(r'^.*Scanned:\s*(?P<scanned>\d+)', repr(stdout))
            if m:
                if int(m.groupdict()['scanned']) == 0:
                    raise AVException(f'Seems that nothing was scanned: {stdout}')
                else:
                    return stdout
            else:
                raise AVException(
                    f'Invalid pattern to check number of objects processed: {stdout}')
        else:
            raise AVException('After 10 tries, could not find "rtvscand: Scan Complete" in sys log')

    def scan(self, path):
        self._perform_command("> /var/log/syslog")  # empty syslog
        return super().scan('manualscan -s', path)  # write log of scan on syslog

    def get_version(self):
        return self._perform_command(self.version_command)

    def get_last_update(self):
        result = self._perform_command(self.last_update_command)
        if result:
            result = result.split(' ')[0]
            return parse(result).date()
        else:
            raise AVException(f'Last update pattern not found in: {result.strip()}')

    def update(self, path):
        try:
            if not self.os.path.exists(self.settings.MEDIA_ROOT):
                self.os.mkdir(self.settings.MEDIA_ROOT)
            self.extract(file_path=path, dst=self.settings.MEDIA_ROOT)
            self._perform_command(rf"sudo chmod +x {self.settings.MEDIA_ROOT}/*.sh")
            self._perform_command(rf"sudo {self.settings.MEDIA_ROOT}/*.sh")
            return True
        except Exception as ex:
            raise AVException(str(ex))
        finally:
            self.shutil.rmtree(self.settings.MEDIA_ROOT)
