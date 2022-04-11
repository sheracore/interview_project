from celery.result import AsyncResult
from unittest.mock import patch
from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.utils.files import generate_photo_file
from core.models.api import API
from users.test import UserTestCase
from agents.models import Agent
from scans.tasks import scan_file
from core.models.system import System


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.agent = Agent.objects.create(api_ip='192.168.100.158', status={})
        self.second_agent = Agent.objects.create(api_ip='192.168.100.229')
        self.file = generate_photo_file()
        System.reset_settings()

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_from_upload_ok(self, perform_async):
        data = {
            'file': self.file,
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': True
        }
        with self.assertNumQueries(12):
            response = self.client.post(
                reverse('file-list'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(
            scan_file.si(response.data['id'],
                         _async=True, extract=True, agent_pks=[1, 2]),
            session_id=response.data['session_id'],
            #queue=response.data['session_id']
        )

    def test_bad_request(self):
        data = {
            'file': self.file,
            'scan': True,
            'agents': [10],
            'extract': True
        }
        with self.assertNumQueries(4):
            response = self.client.post(
                reverse('file-list'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_empty_agents(self, perform_async):
        data = {
            'file': self.file,
            'scan': True,
            'extract': True,
            'agents': []
        }
        with self.assertNumQueries(10):
            response = self.client.post(
                reverse('file-list'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(
            scan_file.si(response.data['id'],
                         _async=True, extract=True, agent_pks=[]),
            session_id=response.data['session_id'],
            #queue=response.data['session_id']
        )

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_no_agents(self, perform_async):
        data = {
            'file': self.file,
            'scan': True,
            'extract': True
        }
        with self.assertNumQueries(10):
            response = self.client.post(
                reverse('file-list'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(
            scan_file.si(response.data['id'],
                         _async=True, extract=True, agent_pks=[]),
            session_id=response.data['session_id'],
            #queue=response.data['session_id']
        )


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        file = generate_photo_file()
        agent = Agent.objects.create(api_ip='192.168.100.158', status={})
        second_agent = Agent.objects.create(api_ip='192.168.100.229')
        self.data = {
            'owner': self.user.pk,
            'file': file,
            'scan': True,
            'agents': [agent.pk, second_agent.pk]
        }
        System.reset_settings()

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthenticated(self, perform_async):
        path = reverse('file-list')

        response = self.client.post(path, data=self.data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthorized(self, perform_async):
        path = reverse('file-list')

        self.client.force_login(self.admin)
        response = self.client.post(path, data=self.data, format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_superuser(self, perform_async):
        path = reverse('file-list')

        self.client.force_login(self.super_admin)
        response = self.client.post(path, data=self.data, format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_authorized(self, perform_async):
        path = reverse('file-list')

        self.user.user_permissions.add(
            Permission.objects.get(codename='add_file')
        )
        self.client.force_login(self.user)
        response = self.client.post(path, data=self.data, format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_group(self, perform_async):
        path = reverse('file-list')

        group = Group.objects.create(name='File Creators')
        group.permissions.set(
            [Permission.objects.get(codename='add_file')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(path, data=self.data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authorized_with_apikey_and_captcha_not_allowed_hosts(self):
        path = reverse('file-list')
        self.api = API.objects.create(
            title='just_for_test',
            allowed_hosts=[
                '1.1.1.1',
                '2.2.2.2'
            ],
            key='foobarforapikey12',
            owner=self.user
        )
        response = self.client.post(path, data=self.data, format='multipart',
                                    HTTP_X_API_KEY='foobarforapikey12',)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_authorized_with_apikey_and_captcha_with_allowed_hosts(
            self, perform_async):
        path = reverse('file-list')
        self.api = API.objects.create(
            title='just_for_test',
            allowed_hosts=[
                '127.0.0.1',
            ],
            key='foobarforapikey12',
            owner=self.user
        )
        response = self.client.post(
            path, data=self.data, format='multipart',
            HTTP_X_API_KEY='foobarforapikey12',
            HTTP_X_CAPTCHA_KEY='TEST',
            HTTP_X_CAPTCHA_VALUE='PASSED')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_authorized_with_apikey_and_captcha_null_allowed_hosts(
            self, perform_async):
        path = reverse('file-list')
        self.api = API.objects.create(
            title='just_for_test',
            key='foobarforapikey12',
            owner=self.user
        )
        response = self.client.post(
            path, data=self.data, format='multipart',
            HTTP_X_API_KEY='foobarforapikey12',
            HTTP_X_CAPTCHA_KEY='TEST',
            HTTP_X_CAPTCHA_VALUE='PASSED')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
