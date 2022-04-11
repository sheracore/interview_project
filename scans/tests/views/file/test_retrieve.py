from rest_framework.reverse import reverse
from django.contrib.auth.models import Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File

from django.conf import settings


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)

    def test_ok(self):
        with self.assertNumQueries(7):
            response = self.client.get(
                reverse('file-detail', kwargs={'pk': self.file.pk}))
        expected = File.objects.get(pk=self.file.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], expected.id)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        setattr(settings, 'I_AM_A_KIOSK', False)
        session = Session.objects.create()
        file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.admin, session=session)
        self.path = reverse('file-detail', kwargs={'pk': file.pk})

    def test_unauthenticated_kiosk(self):
        self.client.force_login(self.user)
        setattr(settings, 'I_AM_A_KIOSK', True)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['id'],
                         File.objects.filter(user=self.admin)[0].pk)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='File Viewers')
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
