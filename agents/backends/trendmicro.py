from .core import AVBackend
from agents.exceptions import AVException
from dateutil.parser import parse
import re
import time
from datetime import datetime, timedelta


class TrendmicroBackend(AVBackend):
    """
        ENTRY_ID=134217730
    LOG_LEVEL=0
    EVENT_LOCAL_DATE=2021/09/26
    EVENT_LOCAL_TIME=09:39:20
    TIMEZONE_DIFFERENCE=-240
    REASON_CODE_DESCRIPTION=
    end_time=2021/09/26 09:39:20
    virus_count=2
    attachment_count=0
    REASON_CODE=0
    COMPONENT_CODE=8
    PRODUCT_PLATFORM_CODE=8
    message_count=1185
    PRODUCT_CODE=51
    start_time=2021/09/26 09:39:14
    DAYLIGHT_SAVING_ACTIVE=1
    SEVERITY_CODE=3
    PRODUCT_LANGUAGE_CODE=1701707776
    PRODUCT_VERSION=3.0
    COMPUTER_NAME=TrendMicro.TrendMicro
    function_code=12
    action_result=21
    action=2
    REASON_CODE_SOURCE=0
    REASON_CODE_SYMBOL=reason is ?
    """
    av_name = 'trendmicro'
    title = 'Trendmicro'
    scan_command = '/opt/TrendMicro/SProtectLinux/SPLX.vsapiapp/splxmain'
    last_update_command = 'stat /opt/TrendMicro/SProtectLinux/SPLX.vsapiapp/splxmain | grep Modify'
    scan_time_pattern = ''
    infected_pattern = r'.*virus_count=\s*(?P<infected>\d+)'

    def check(self):
        if self.os.path.exists(self.scan_command):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def on_scan_exit_ok(self, result):
        scan_complete = False
        counter = 0
        time.sleep(0.5)
        max_retries = 10
        while (not scan_complete) and (counter < max_retries):
            files = self.os.listdir(r"/var/log/TrendMicro/SProtectLinux")
            date_time = datetime.now().strftime("%Y%m%d")
            for file in files:
                if file.startswith('Scan.' + date_time):
                    path = r"/var/log/TrendMicro/SProtectLinux" + '/' + file
                    with self.open(path, 'r') as f:
                        stdout = f.read()
                        break
            time.sleep(0.5)
            counter += 1

        if stdout:
            m = re.match(self.infected_pattern, repr(stdout))
            if m:
                return stdout
            else:
                raise AVException(
                    f'Invalid pattern to check number of objects processed: {stdout}')
        else:
            raise AVException(f'After {max_retries} tries, log is still empty')

    def scan(self, path):
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        file_name = self.os.path.split(path)[-1]
        dst = self.settings.MEDIA_ROOT
        tomorrow = datetime.now() + timedelta(days=1)
        prefix_log = tomorrow.strftime("%Y-%m-%d")
        try:
            f"/opt/TrendMicro/SProtectLinux/SPLX.vsapiapp/splxmain -g {prefix_log}"
            self.shutil.copyfile(path, dst + '/' + file_name)
            return super().scan('-m', f'"{dst}"')
        except Exception as ex:
            raise AVException(str(ex))
        finally:
            if self.os.path.exists(dst):
                self.shutil.rmtree(dst)

    def get_last_update(self):
        output = self._perform_command(self.last_update_command)
        output_list = output.split(' ')
        if len(output_list) > 1:
            try:
                return parse(output_list[1]).date()    # 2020-03-19
            except Exception as e:
                raise AVException(str(e))
        else:
            raise AVException(f'Last update pattern not found in: {output.strip()}')
