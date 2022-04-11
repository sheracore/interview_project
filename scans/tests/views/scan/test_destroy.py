from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from django.contrib.auth.models import Permission, Group

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File
from scans.models.scan import Scan
from agents.models import Agent


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)
        self.agent = Agent.objects.create(api_ip='192.168.100.158')
        self.scan = Scan.objects.create(agent=self.agent, file=self.file)
        self.path = reverse('scan-detail', kwargs={'pk': self.scan.pk})

    def test_ok(self):
        url = self.path
        with self.assertNumQueries(5):
            response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Scan.objects.filter(pk=self.scan.pk).exists())


class Perm(UserTestCase):

    def setUp(self):
        super().setUp()
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)
        self.agent = Agent.objects.create(api_ip='192.168.100.158')
        self.scan = Scan.objects.create(agent=self.agent, file=self.file)
        self.path = reverse('scan-detail', kwargs={'pk': self.scan.pk})

    def test_unauthenticated(self):
        url = self.path

        # delete scan object
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        url = self.path

        # now login with user
        self.client.force_login(self.admin)
        response = self.client.delete(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        url = self.path

        # login with superuser
        self.client.force_login(self.super_admin)
        response = self.client.delete(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_authorized(self):
        url = self.path

        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_scan')
        )
        self.client.force_login(self.user)
        response = self.client.delete(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_group(self):
        url = self.path

        group = Group.objects.create(name='Scan Destroyers')
        group.permissions.set(
            [Permission.objects.get(codename='delete_scan')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.delete(url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
