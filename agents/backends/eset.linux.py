from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse


class EsetBackend(AVBackend):
    """
        Sample outputput of esets_scan command:
            ESET Command-line scanner, version 4.0.87, (C) 1992-2013 ESET, spol. s r.o.
            Module loader, version 1069 (20161122), build 1112
            Module perseus, version 1539.1 (20180529), build 1973
            Module scanner, version 17641 (20180701), build 37893
            Module archiver, version 1275 (20180605), build 1347
            Module advheur, version 1188 (20180422), build 1165
            Module cleaner, version 1159 (20180612), build 1221

            Command line: /root/Malware-Test/

            Scan started at:   Sun 01 Jul 2018 08:52:59 AM UTC
            name="/root/Malware-Test/a/mal.pdf", threat="JS/Exploit.Pdfka.NOO trojan", action="cleaned by deleting", info=""
            name="/root/Malware-Test/a/bm[1].pdf", threat="JS/Exploit.Pdfka.QNG trojan", action="cleaned by deleting", info=""

            Scan completed at: Sun 01 Jul 2018 08:52:59 AM UTC
            Scan time:         0 sec (0:00:00)
            Total:             files - 18, objects 28
            Infected:          files - 0, objects 0
            Cleaned:           files - 2, objects 2

    """
    av_name = 'eset'
    title = 'Eset Security'
    service_name = 'esets'
    scan_command = '/opt/eset/esets/sbin/esets_scan'
    last_update_command = 'stat /var/opt/eset/esets/lib/data/updfiles | grep Modify:'
    scan_time_pattern = r'^.*Scan time:\s*(?P<scan_time>\S+)'
    infected_pattern = r'^.*Infected:\s*files\s*-\s*(?P<infected>\d+)'
    version_command = '/opt/eset/esets/sbin/esets_scan --version'

    def on_scan_exit_fail(self, result):
        if result.exited == 50:
            return result.stdout
        elif result.exited == 10:
            raise AVException(f'unable to open due to this: {result.stdout.strip()}')
        else:
            return super().on_scan_exit_fail(result)

    def scan(self, path):
        return super().scan('--clean-mode=none', f'"{path}"')

    def get_version(self):
        output = self._perform_command(self.version_command)
        version = output.split(' ')[-1]
        return version

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        output_list = output.split(' ')
        if len(output_list) > 1:
            try:
                return parse(output_list[1]).date()  # 2021-08-11
            except Exception as e:
                raise AVException(str(e))
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')

    def update(self, path):
        try:
            self.extract(file_path=path, dst='/var/opt/eset/esets/lib/data/updfiles/')
            return True
        except Exception as ex:
            raise AVException(str(ex))
