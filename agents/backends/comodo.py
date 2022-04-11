from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class ComodoBackend(AVBackend):
    """
        b'-----== Scan Start ==-----
        /smb/2021_03_03_19_29_24/eventlog_provider.dll.38666fbe23b816a1a47669d51f906659 ---> Not Virus
        -----== Scan End ==-----
        Number of Scanned Files: 1
        Number of Found Viruses: 0
        """
    av_name = 'comodo'
    title = 'Comodo'
    scan_command = '/opt/COMODO/cmdscan'
    last_update_command = 'stat /opt/COMODO/scanners/bases.cav | grep Modify:'
    # scan_time_pattern = ''
    infected_pattern = r'^.*Number of Found Viruses:\s*(?P<infected>\d+)'

    def check(self):
        if self.os.path.exists(self.scan_command):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        return super().scan('-s', f"'{path}'", '-v')

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        output_list = output.split(' ')
        if len(output_list) > 1:
            try:
                return parse(output_list[1]).date()         # 2020-01-04
            except Exception as e:
                raise AVException(str(e))
        else:
            raise AVException(f'Last update pattern not found in {output.strip()}')

    def update(self, path):
        try:
            self.extract(file_path=path, dst='/opt/COMODO/scanners/')
            return True
        except Exception as ex:
            raise AVException(str(ex))

    def get_version(self):
        return None

    def get_license_key(self):
        return 'Free'

    def get_license_expiry(self):
        return 'Free'
