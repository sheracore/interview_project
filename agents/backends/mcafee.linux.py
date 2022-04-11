from agents.exceptions import AVException
from .core import AVBackend


class McafeeBackend(AVBackend):
    """
            [OUTPUT]:
        McAfee VirusScan Command Line for Linux32 Version: 6.1.2.226
        Copyright (C) 2018 McAfee, Inc.
        (408) 988-3832 EVALUATION COPY - November 13 2018

        AV Engine version: 6000.8403 for Linux32.
        Dat set version: 9075 created Nov 12 2018
        Scanning for 668683 viruses, trojans and variants.

        /opt/fwutech-files/infected/a/mal.pdf [MD5:7707e05c896acb36c25cd4c12e105b73] ... Found the Exploit-PDF.bk.gen trojan !!!


        Summary Report on /opt/fwutech-files/infected/a/mal.pdf
        File(s)
                Total files:...................     1
                Clean:.........................     0
                Not Scanned:...................     0
                Possibly Infected:.............     1


        Time: 00:00.00


        Thank you for choosing to evaluate VirusScan Command Line from McAfee.
        This  version of the software is for Evaluation Purposes Only and may be
        used  for  up to 30 days to determine if it meets your requirements.  To
        license  the  software,  or to  obtain  assistance during the evaluation
        process,  please call (408) 988-3832.  If you  choose not to license the
        software,  you  need  to remove it from your system.  All  use  of  this
        software is conditioned upon compliance with the license terms set forth
        in the README.TXT file.

        """
    av_name = 'mcafee'
    title = 'McAfee'
    scan_command = '/usr/local/uvscan/uvscan'

    scan_time_pattern = ''
    infected_pattern = r'^.*Possibly Infected:\s*(?P<infected>\d+)'

    def check(self):
        if self.os.path.exists(self.scan_command):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exists')

    def scan(self, path):
        return super().scan('--SECURE --SUMMARY', path)
