import os

from django.conf import settings
from core.utils.commanding import execute_local

from six.moves import configparser


class Samba:
    def __init__(self, samba_config_path=settings.SAMBA_CONFIG_PATH):
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(samba_config_path)
        self.samba_config_path = samba_config_path

    def _forbidden_sections(self, section):
        if section in ['DEFAULT', 'global', 'printers', 'print']:
            raise ValueError(f"You can not add/remove this {section}")

    def add_sharepoint(self, name, path, read_only=False, comment='Add share to samba config'):
        """Add a section to samba config"""
        self._forbidden_sections(name)
        path_exists = os.path.exists(path)
        if not path_exists:
            return f"{path} does not mounted"

        if name not in self.config_parser.sections():
            self.config_parser.add_section(name)

        read_only = 'no' if read_only == False else 'yes'
        self.config_parser.set(name, 'comment', comment)
        self.config_parser.set(name, 'path', path)
        self.config_parser.set(name, 'read only', read_only)
        self.config_parser.set(name, 'browsable', 'yes')

        with open(self.samba_config_path, 'w') as config_file:
            self.config_parser.write(config_file)

    def remove_sharepoint(self, name):
        """Remove a section to samba config"""
        self._forbidden_sections(name)
        self.config_parser.remove_section(name)

        with open(self.samba_config_path, 'w') as config_file:
            self.config_parser.write(config_file)

    def restart_service(self):
        execute_local("systemctl restart smbd.service")

    def update_readonly(self, name, readonly):
        pass
