from celery.result import AsyncResult
from datetime import timedelta

from unittest.mock import patch
from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status
from django.utils import timezone
from django.core.files.base import ContentFile

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File
from scans.tasks import cleanup


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        session = Session.objects.create()
        self.first_file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)
        self.first_file.created_at = timezone.now() - timedelta(days=2)
        self.first_file.save()

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_ok(self, perform_async):
        data = {'days_older_than': 2}
        with self.assertNumQueries(3):
            response = self.client.post(
                reverse('file-cleanup'), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perform_async.assert_called_with(cleanup.si(data['days_older_than']),
                                         on_commit=False)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.data = {'days_older_than': 2}
        self.path = reverse('file-cleanup')

    def test_unauthenticated(self):
        response = self.client.post(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test-id'))
    def test_unauthorized(self, perform_async):
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_login(self.admin)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_superuser(self, perform_async):
        self.client.force_login(self.super_admin)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perform_async.assert_called_with(cleanup.si(
            self.data['days_older_than']), on_commit=False
        )

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_authorized(self, perform_async):
        self.user.user_permissions.add(
            Permission.objects.get(codename='cleanup')
        )
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perform_async.assert_called_with(cleanup.si(
            self.data['days_older_than']), on_commit=False
        )

    @patch('core.mixins.AsyncMixin.perform_async',
           return_value=AsyncResult('test'))
    def test_group(self, perform_async):
        group = Group.objects.create(name='File Creators')
        group.permissions.set(
            [Permission.objects.get(codename='cleanup')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perform_async.assert_called_with(cleanup.si(
            self.data['days_older_than']), on_commit=False
        )
