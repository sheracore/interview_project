import invoke
import subprocess
import platform
import rpyc
import os
import shutil
import base64

from django.conf import settings

from core.exceptions import PrinterError
from core.utils.files import extract_compressed_file


class Printer:
    def __init__(self, host=None, port=18811):
        self.host = host
        self.port = port
        if host:
            self.conn = rpyc.classic.connect(host, port)
            self.conn._config['sync_request_timeout'] = None
            self.os = self.conn.modules.os
            self.open = self.conn.builtins.open
            self.subprocess = self.conn.modules.subprocess
            self.invoke = self.conn.modules.invoke
            self.shutil = self.conn.modules.shutil
            self.settings = self.conn.root.settings
            self.extract = self.conn.root.extract_compressed_file
            if self.conn.modules.platform.uname().system == 'Windows':
                self.pywinauto = self.conn.modules.pywinauto
        else:
            self.conn = None
            self.os = os
            self.open = open
            self.subprocess = subprocess
            self.invoke = invoke
            self.shutil = shutil
            self.settings = settings
            self.extract = extract_compressed_file
            if platform.uname().system == 'Windows':
                import pywinauto
                self.pywinauto = pywinauto

    def __del__(self):
        if self.conn:
            self.conn.close()

    def check(self):
        return True

    def print(self, message):
        file_64_decode = base64.b64decode(message)
        if not self.os.path.exists(self.settings.MEDIA_ROOT):
            self.os.mkdir(self.settings.MEDIA_ROOT)
        full_file_path = self.settings.MEDIA_ROOT + '\\' + 'print_receipt.pdf'
        try:
            with self.open(full_file_path, 'wb') as f:
                f.write(file_64_decode)
            # cmd = r'"C:\PDFXCview\PDFXCview.exe" /print "{path}"'.format(path=full_file_path)
            cmd = r'"C:\pprint.exe" "{path}"'.format(
                path=full_file_path)
            # cmd = r"C:\pprint.exe {path}".format(path=full_file_path)
            # self.os.system(cmd)
            result = self.invoke.run(cmd, warn=True)
            if not result.ok:
                raise PrinterError(result.stderr or result.stdout)
        finally:
            if self.os.path.exists(full_file_path):
                self.os.remove(full_file_path)
