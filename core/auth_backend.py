import ldap
from django.contrib.auth.backends import ModelBackend
from django_auth_ldap.backend import LDAPBackend, LDAPSettings
from django_auth_ldap.config import LDAPSearch
from core.models.system import System


class CustomBackend(ModelBackend, LDAPBackend):

    @property
    def settings(self):
        system_settings = System.get_settings()
        if not (system_settings.get('ldap_server_uri') and system_settings.get('ldap_bind_dn') and
                system_settings.get('ldap_password') and system_settings.get('ldap_user_search')):
            return None
        if self._settings is None:
            self._settings = LDAPSettings(self.settings_prefix, self.default_settings)
        self._settings.SERVER_URI = system_settings['ldap_server_uri']
        self._settings.BIND_DN = system_settings['ldap_bind_dn']
        self._settings.BIND_PASSWORD = System.decrypt_password(system_settings['ldap_password'])
        self._settings.USER_SEARCH = LDAPSearch(system_settings['ldap_user_search'],
                                                ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)")
        return self._settings

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_auth = ModelBackend.authenticate(self, request, username=username, password=password, **kwargs)
        if not user_auth and self.settings:
            user_auth = LDAPBackend.authenticate(self, request, username=username, password=password, **kwargs)
        return user_auth

    def get_user(self, user_id):
        user = ModelBackend.get_user(self, user_id)
        if not user and self.settings:
            user = LDAPBackend.get_user(self, user_id)
        return user
