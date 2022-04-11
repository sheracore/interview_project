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
        with self.assertNumQueries(8):
            response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'), session=session)
        self.agent = Agent.objects.create(api_ip='192.168.100.158')
        self.scan = Scan.objects.create(agent=self.agent, file=self.file)
        self.path = reverse('scan-detail', kwargs={'pk': self.scan.pk})

    def test_unauthenticated(self):
        url = self.path
        # Unauthenticated
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        url = self.path
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        url = self.path
        self.client.force_login(self.super_admin)
        response = self.client.get(url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_authorized(self):
        url = self.path

        # has permission
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_scan')
        )
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.json()['count'], Scan.objects.all().count())

    def test_group(self):
        url = self.path
        group = Group.objects.create(name='Scan Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_scan')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
