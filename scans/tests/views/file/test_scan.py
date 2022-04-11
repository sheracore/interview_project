from celery.result import AsyncResult
from unittest.mock import patch
from rest_framework.reverse import reverse
from django.contrib.auth.models import Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from users.test import UserTestCase
from scans.models.file import File
from scans.models.session import Session
from scans.tasks import scan_file
from agents.models import Agent
from core.models.system import System

from django.conf import settings


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin,session=session)
        self.agent = Agent.objects.create(api_ip='192.168.100.158')
        System.reset_settings()

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_ok(self, perform_async):
        with self.assertNumQueries(10):
            response = self.client.patch(
                reverse('file-scan', kwargs={'pk': self.file.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.file.refresh_from_db()
        perform_async.assert_called_with(
            scan_file.si(File.objects.last().pk, _async=True, extract=None, agent_pks=None),
            session_id=Session.objects.last().pk, #queue=''
        )


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        setattr(settings, 'I_AM_A_KIOSK', False)
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.admin, session=session)
        self.agent = Agent.objects.create(api_ip='192.168.100.158')
        self.path = reverse('file-scan', kwargs={'pk': self.file.pk})
        System.reset_settings()

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthenticated_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        response = self.client.patch(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthenticated(self, perform_async):
        response = self.client.patch(self.path)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthorized_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        self.client.force_login(self.user)
        response = self.client.patch(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthorized(self, perform_async):
        self.client.force_login(self.user)
        response = self.client.patch(self.path)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_superuser(self, perform_async):
        self.client.force_login(self.super_admin)
        response = self.client.patch(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_authorized(self, perform_async):
        self.client.force_login(self.admin)
        response = self.client.patch(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_group(self, perform_async):
        group = Group.objects.create(name='File changer')
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.patch(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
