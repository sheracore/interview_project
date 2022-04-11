from django.contrib.auth.models import Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile
from django.conf import settings
from unittest.mock import patch
from celery.result import AsyncResult

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File
from scans.models.scan import Scan
from agents.models import Agent
from scans.tasks import postscan_copy


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create(progress=100)
        self.first_file = File.objects.create(
            file=file, user=self.super_admin,  session=session)
        agent = Agent.objects.create(api_ip='192.168.100.158')
        self.scan = Scan.objects.create(
            agent=agent, file=self.first_file,
            infected_num=1, status_code=200
        )
        self.url = reverse('file-postscan-copy') + '?session_id=1'

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_ok(self, perform_async):
        with self.assertNumQueries(4):
            response = self.client.patch(
                path=self.url, data={'path': './media'})
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perform_async.assert_called_with(
            postscan_copy.si(1, './media'),
            on_commit=False)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        setattr(settings, 'I_AM_A_KIOSK', False)
        file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create(progress=100)
        self.first_file = File.objects.create(
            file=file, user=self.super_admin, session=session)
        agent = Agent.objects.create(api_ip='192.168.100.158')
        self.scan = Scan.objects.create(
            agent=agent, file=self.first_file,
            infected_num=1, status_code=200
        )
        self.url = reverse('file-postscan-copy') + '?session_id=1'
        self.data = {'path': './media'}

    def test_unauthenticated(self):
        # Unauthorized
        response = self.client.patch(self.url, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_unauthenticated_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        # Unauthorized
        response = self.client.patch(self.url, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized(self):
        # User and has not the view_file perms
        self.client.force_login(self.user)
        response = self.client.patch(path=self.url, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_unauthorized_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        # User and has not the view_file perms
        self.client.force_login(self.user)
        response = self.client.patch(path=self.url, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_superuser(self, perform_async):
        # super admin
        self.client.force_login(self.super_admin)
        response = self.client.patch(path=self.url, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.client.force_login(self.admin)
        response = self.client.patch(self.url, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_authorized_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        self.client.force_login(self.admin)
        response = self.client.patch(self.url, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='File Post Scan Copy')
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.patch(self.url, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_group_kiosk(self, perform_async):
        setattr(settings, 'I_AM_A_KIOSK', True)
        group = Group.objects.create(name='File Post Scan Copy')
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.patch(self.url, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
