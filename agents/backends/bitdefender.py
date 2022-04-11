import os
from .core import AVBackend
from agents.exceptions import AVException


class BitdefenderBackend(AVBackend):
    """
        Sample outputput:
                /opt/BitDefender-scanner/bin/bdscan mal.pdf

        BitDefender Antivirus Scanner for Unices v7.141118 Linux-amd64
        Copyright (C) 1996-2014 BitDefender. All rights reserved.
        Trial key found. 30 days remaining.

        Infected file action: ignore
        Suspected file action: ignore
        Loading plugins, please wait
        Plugins loaded.

        /root/a/mal.pdf  ok
        /root/a/mal.pdf=>(JAVASCRIPT)  infected: Exploit.PDF-JS.Gen
        /root/a/mal.pdf=>(NAME)  infected: Exploit.PDF-Name.Gen
        /root/a/mal.pdf=>(INFECTED_JS)  infected: Exploit.CVE-2008-2992.Gen
        /root/a/mal.pdf=>(CODE 1)  ok


        Results:
        Folders            : 0
        Files              : 5
        Packed             : 1
        Archives           : 0
        Infected files     : 3
        Suspect files      : 0
        Identified viruses : 3
        I/O errors         : 0
        Files/second       : 2
        Scan time          : 00:00:02

        """

    av_name = 'bitdefender'
    title = 'BitDefender'
    scan_command = '/opt/BitDefender-scanner/bin/bdscan'
    # last_update_command = ''
    # scan_time_pattern = ''
    # infected_pattern = ''

    def check(self):
        if os.path.exists(self.scan_command):
            return True
        else:
            raise AVException(f'"{self.scan_command}" path does not exist')

    def scan(self, path):
        return super().scan(f"'{path}'")

