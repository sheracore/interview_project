from .core import AVBackend
import re
from agents.exceptions import AVException
from dateutil.parser import parse


class EscanBackend(AVBackend):
    """
    -------------------------------------------------------
                Scan Configuration
    -------------------------------------------------------
    Scan Memory on Execution        : Yes
    Scan Packed                     : Yes
    Scan Archives                   : Yes
    Scan Mails                      : Yes
    Use Heuristics Scanning         : Yes
    Recursive                       : Yes
    Follow Symbolic Links           : No
    Cross File System               : No
    Scan Action                     : Log only
    Exclude extensions              :
    Log Level                       : Infected

    Initializing AV... Done
    Memory Scan Started  Done
    Scan Started. Please wait
    --------------------Scan Statistics--------------------
    Scanned directories             3890
    Scanned objects                 13034
    Infected objects                0
    Suspicious objects              0
    Disinfected objects             0
    Uncurable objects               0
    Viruses found                   0
    Deleted objects                 0
    Rename objects                  0
    Quarantined objects             0
    Corrupt objects                 0
    Encrypted objects               0
    Scan errors                     529
    Actions failed                  0
    -------------------------------------------------------

        """
    av_name = 'escan'
    title = 'e-Scan'
    scan_command = '/opt/MicroWorld/bin/escan'
    # scan_time_pattern = ''
    last_update_command = 'stat /opt/MicroWorld/var/bdplugins/Plugins | grep Modify:'
    infected_pattern = r'^.*Infected objects[\\t\\n]*(?P<infected>\d+)[\\t\\n]*'
    version_command = r'/opt/MicroWorld/bin/escan --version'

    def check(self):
        if self.os.path.exists(self.scan_command):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_ok(self, result):
        if 'Initializing AV... Error initializing AV' in result.stdout.strip():
            raise AVException('Error initializing AV')
        return super().on_scan_exit_ok(result)

    def scan(self, path):
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')

        return super().scan('-ly', f'"{path}"')

    def get_version(self):
        output = self._perform_command(self.version_command)
        m = re.match(r'.*MicroWorld eScan For Linux Version\s:\s(?P<version>\S+)', repr(output))
        if m:
            version = m.groupdict()['version']
            return version
        else:
            return AVException(f'Version pattern not found in: {output.strip()}')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        output_list = output.split(' ')
        if len(output_list) > 1:
            try:
                return parse(output_list[1]).date()    # 2021-08-11
            except Exception as e:
                raise AVException(str(e))
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')

    def update(self, path):
        try:
            self.extract(file_path=path, dst='/opt/MicroWorld/var/bdplugins/Plugins/')
            return True
        except Exception as ex:
            raise AVException(str(ex))
