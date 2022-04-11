from celery.result import AsyncResult
from unittest.mock import patch
from django.contrib.auth.models import Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.utils.files import generate_photo_file
from users.test import UserTestCase
from agents.models import Agent
from scans.tasks import create_from_url
from core.models.system import System
from core.models.api import API


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
    def test_from_url_ok(self, perform_async):
        data = {
            'url': 'http://placehold.it/120x120&text=image1',
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': True
        }
        with self.assertNumQueries(7):
            response = self.client.post(
                reverse('file-from-url'), data=data
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(create_from_url.si(
            1, data['url'], save_as=None, scan=True, extract=True,
            agent_pks=[1, 2], owner_id=1), session_id=1)

    def test_bad_request(self):
        data = {
            'url': 'http://placehold.it/120x120&text=image1',
            'scan': True,
            'agents': [10],
            'extract': True
        }
        with self.assertNumQueries(4):
            response = self.client.post(
                reverse('file-from-url'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_empty_agents(self, perform_async):
        data = {
            'url': 'http://placehold.it/120x120&text=image1',
            'scan': True,
            'extract': True,
            'agents': []
        }
        with self.assertNumQueries(5):
            response = self.client.post(
                reverse('file-from-url'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(create_from_url.si(
            1, data['url'], save_as=None, scan=True, extract=True,
            agent_pks=None, owner_id=1), session_id=1)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_no_agents(self, perform_async):
        data = {
            'url': 'http://placehold.it/120x120&text=image1',
            'scan': True,
            'extract': True
        }
        with self.assertNumQueries(5):
            response = self.client.post(
                reverse('file-from-url'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(create_from_url.si(
            1, data['url'], save_as=None, scan=True, extract=True,
            agent_pks=None, owner_id=1), session_id=1)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.agent = Agent.objects.create(api_ip='192.168.100.158', status={})
        self.second_agent = Agent.objects.create(api_ip='192.168.100.229')
        self.file = generate_photo_file()
        self. data = {
            'url': 'http://placehold.it/120x120&text=image1',
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': True
        }
        System.reset_settings()
        self.path = reverse('file-from-url')

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthenticated(self, perform_async):
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthorized(self, perform_async):
        self.client.force_login(self.admin)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_superuser(self, perform_async):
        self.client.force_login(self.super_admin)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_group(self, perform_async):
        group = Group.objects.create(name='File Creators')
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authorized_with_apikey_and_captcha_not_allowed_hosts(self):
        path = self.path
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
           return_value=AsyncResult('test'))
    def test_authorized_with_apikey_and_captcha_with_allowed_hosts(
            self, perform_async):
        path = self.path
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
           return_value=AsyncResult('test'))
    def test_authorized_with_apikey_and_captcha_null_allowed_hosts(
            self, perform_async):
        path = self.path
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
