from requests.exceptions import RequestException
from django.db import models
from django.core.validators import validate_ipv4_address

from core.mixins import AsyncMixin
from core.fields import SafeCharField, SafeTextField
from core.utils.http import request as _request
from core.utils.commanding import execute_remote
from core.models.mixins import DateMixin, UpdateModelMixin


class Server(DateMixin, UpdateModelMixin, AsyncMixin):
    title = SafeCharField(max_length=64, blank=True)
    api_ip = SafeCharField(validators=[validate_ipv4_address],
                           max_length=16)
    api_port = models.PositiveIntegerField(default=80)
    api_key = SafeCharField(max_length=255, default='changeme')

    # remote connection specs. Left none if connection is local
    ssh_ip = SafeCharField(max_length=16, null=True, blank=True,
                           validators=[validate_ipv4_address])
    ssh_port = models.PositiveSmallIntegerField(null=True)
    ssh_username = SafeCharField(max_length=64, blank=True)
    ssh_password = SafeCharField(max_length=64, blank=True)

    status = models.JSONField(null=True, editable=False)
    note = SafeTextField(max_length=4096, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.title == '':
            self.title = f'{self.api_ip}:{self.api_port}'
        super(Server, self).save(*args, **kwargs)

    def get_url(self):
        return f'http://{self.api_ip}:{self.api_port}/api/v1/'

    def request(self, url, method='GET', json=None, data=None, files=None,
                extra_headers=None,
                timeout=10, params=None):
        h = {}
        if extra_headers:
            h = extra_headers
        h['X-API-KEY'] = self.api_key
        url = self.get_url() + url.strip('/') + '/'

        params = params or {}
        querystrings = '&'.join(
            [f'{key}={value}' for key, value in params.items()])
        if querystrings:
            url += f'?{querystrings}'

        return _request(url, method, json=json, data=data, files=files,
                        headers=h, timeout=timeout)

    def perform(self, url, method='GET', json=None, data=None, files=None,
                extra_headers=None, timeout=10, params=None):
        try:
            response = self.request(url, method=method, json=json, data=data,
                                    files=files,
                                    extra_headers=extra_headers,
                                    timeout=timeout, params=params)
            if 'json' in response.headers.get('Content-Type', ''):
                data = {
                    'status_code': response.status_code,
                    **response.json()
                }
            else:
                data = {
                    'status_code': response.status_code,
                    'detail': response.text
                }

        except RequestException as request_error:
            data = {
                'status_code': 500,
                'detail': str(request_error)
            }
        return data

    def execute(self, command):
        return execute_remote(self.ssh_ip, command, self.ssh_username,
                              self.ssh_password, self.ssh_port)
