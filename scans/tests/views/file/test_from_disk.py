from celery.result import AsyncResult
from unittest.mock import patch
from django.contrib.auth.models import Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.utils.files import generate_photo_file
from users.test import UserTestCase
from agents.models import Agent
from scans.tasks import bulk_create_from_disk
from core.models.system import System

from django.conf import settings


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
    def test_from_disk_ok(self, perform_async):
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': True
        }
        with self.assertNumQueries(7):
            response = self.client.post(
                reverse('file-from-disk'), data=data
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(bulk_create_from_disk.si(
            1, data['paths'], scan=True, extract=True,
            agent_pks=[1, 2], owner_id=1), session_id=1)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_with_extract_setting_none_and_given_true(self, perform_async):
        _settings = System.get_settings()
        _settings['extract'] = None
        System.set_settings(_settings)
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': True
        }
        with self.assertNumQueries(7):
            response = self.client.post(
                reverse('file-from-disk'), data=data
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(bulk_create_from_disk.si(
            1, data['paths'], scan=True, extract=True,
            agent_pks=[1, 2], owner_id=1), session_id=1)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_with_extract_setting_none_and_given_false(self, perform_async):
        _settings = System.get_settings()
        _settings['extract'] = None
        System.set_settings(_settings)
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': False
        }
        with self.assertNumQueries(7):
            response = self.client.post(
                reverse('file-from-disk'), data=data
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(bulk_create_from_disk.si(
            1, data['paths'], scan=True, extract=False,
            agent_pks=[1, 2], owner_id=1), session_id=1)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_with_extract_setting_true_and_given_false(self, perform_async):
        _settings = System.get_settings()
        _settings['extract'] = True
        System.set_settings(_settings)
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': False
        }
        with self.assertNumQueries(7):
            response = self.client.post(
                reverse('file-from-disk'), data=data
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(bulk_create_from_disk.si(
            1, data['paths'], scan=True, extract=True,
            agent_pks=[1, 2], owner_id=1), session_id=1)

    def test_bad_request(self):
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'agents': [10],
            'extract': True
        }
        with self.assertNumQueries(4):
            response = self.client.post(
                reverse('file-from-disk'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_empty_agents(self, perform_async):
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'extract': True,
            'agents': []
        }
        with self.assertNumQueries(5):
            response = self.client.post(
                reverse('file-from-disk'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(bulk_create_from_disk.si(
            1, data['paths'], scan=True, extract=True,
            agent_pks=None, owner_id=1),session_id=1)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_no_agents(self, perform_async):
        data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'extract': True
        }
        with self.assertNumQueries(5):
            response = self.client.post(
                reverse('file-from-disk'), data=data, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        perform_async.assert_called_with(bulk_create_from_disk.si(
            1, data['paths'], scan=True, extract=True,
            agent_pks=None, owner_id=1), session_id=1)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.agent = Agent.objects.create(api_ip='192.168.100.158', status={})
        self.second_agent = Agent.objects.create(api_ip='192.168.100.229')
        self.file = generate_photo_file()
        self. data = {
            'paths': ['./scans/tests/test_files/download.png'],
            'scan': True,
            'agents': [self.agent.pk, self.second_agent.pk],
            'extract': True
        }
        System.reset_settings()
        setattr(settings, 'I_AM_A_KIOSK', False)
        self.path = reverse('file-from-disk')

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthenticated_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauth_kiosk_login_required(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        System.update_settings({'login_required': True})
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_auth_kiosk_login_required(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        System.update_settings({'login_required': True})
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
        self.assertEqual(settings.I_AM_A_KIOSK, False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthorized_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_group_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        group = Group.objects.create(name='File Creators')
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
