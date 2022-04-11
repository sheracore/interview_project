from .core import AVBackend
from agents.exceptions import AVException
import time
import re
from dateutil.parser import parse


class McafeeBackend(AVBackend):
    """
        2021-12-06 07:22:49.603Z    |Activity|odsbl               |mfetp                    |      4572|      3192|ODS                 |odsruntask.cpp(5325)                    | 	AMCore content version = 4635.0
        2021-12-06 07:22:49.603Z    |Activity|odsbl               |mfetp                    |      4572|      3192|ODS                 |odsruntask.cpp(1758)                    | 	Scan started	DESKTOP-5RK1JPT\fwutech	Right-Click Scan
        2021-12-06 07:22:49.821Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5096)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech		Scan Summary
        2021-12-06 07:22:49.822Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5102)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Files scanned           : 1
        2021-12-06 07:22:49.822Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5108)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Files with detections   : 0
        2021-12-06 07:22:49.830Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5114)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Files cleaned           : 0
        2021-12-06 07:22:49.831Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5120)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Files deleted           : 0
        2021-12-06 07:22:49.832Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5126)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Files not scanned       : 0
        2021-12-06 07:22:49.833Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5134)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Registry objects scanned: 0
        2021-12-06 07:22:49.833Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5140)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Registry detections     : 0
        2021-12-06 07:22:49.834Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5146)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Registry objects cleaned: 0
        2021-12-06 07:22:49.835Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5152)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Registry objects deleted: 0
        2021-12-06 07:22:49.835Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(5163)                    | 	Scan Summary DESKTOP-5RK1JPT\fwutech	Run time             : 0:00:00
        2021-12-06 07:22:49.836Z    |Activity|odsbl               |mfetp                    |      4572|      1720|ODS                 |odsruntask.cpp(2292)                    | 	Scan completed DESKTOP-5RK1JPT\fwutech	Right-Click Scan (0:00:00)
    """
    av_name = 'mcafee'
    title = 'Mcafee'
    scan_command = r'"C:\Program Files (x86)\McAfee\Endpoint Security\Endpoint Security Platform\MFEConsole.exe" /rightclick=1'
    exe_file_path = r'C:\Program Files (x86)\McAfee\Endpoint Security\Endpoint Security Platform\MFEConsole.exe'
    log_path = r'C:\ProgramData\McAfee\Endpoint Security\Logs\OnDemandScan_Activity.log'
    infected_pattern = r'^.*Files with detections\s*:\s*(?P<infected>\d+)'
    last_update_command = r'Reg Query "HKEY_LOCAL_MACHINE\SOFTWARE\McAfee\AVSolution\DS\DS" /v "szContentCreationDate"'

    def check(self):
        if self.os.path.exists(self.exe_file_path):
            return True
        else:
            raise AVException(f'"{self.exe_file_path}" path does not exist')

    def scan(self, path):
        path = path.replace('/smb/', 'Z:/').replace('/', '\\')
        if not self.os.path.exists(path):
            raise AVException('The File does not exist.')
        if self.os.path.exists(self.log_path):
            self.os.remove(self.log_path)
        return super().scan(rf'/data={path}')

    def read_stdout_from_scan_log(self):
        counter = 0
        time.sleep(0.5)
        while counter < 100:
            if self.os.path.exists(self.log_path):
                with self.open(self.log_path, 'r') as f:
                    stdout = f.read()
                    if stdout and "Scan completed" in stdout:
                        self.os.system(r'taskkill /im "MFEConsole.exe"')
                        return stdout
            time.sleep(0.5)
            counter += 1
        raise AVException('After 100 tries, log is still empty')

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
                    self._perform_command(nested_file_path)
            return True

        except Exception as ex:
            raise AVException(str(ex))

        finally:
            self.shutil.rmtree(self.settings.MEDIA_ROOT)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        m = re.match(r'^.*szContentCreationDate\s*REG_SZ\s*(?P<last_update_time>\d+.-\d+.-\d+)', repr(output))
        if m:
            last_update_time = m.groupdict()['last_update_time']
            return parse(last_update_time.strip()).date()
        else:
            raise AVException(f'Last update pattern not found in: {output}')
