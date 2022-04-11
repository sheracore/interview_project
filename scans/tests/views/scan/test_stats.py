from django.contrib.auth.models import Permission, Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

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
        Scan.objects.create(agent=self.agent, file=self.file)

    def test_ok(self):
        url = reverse('scan-stats')
        with self.assertNumQueries(6):
            response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        session = Session.objects.create()
        file = ContentFile(b"Some file content", name='test.pdf')
        File.objects.create(file=file, user=self.user, session=session)
        self.path = reverse('scan-stats')

    def test_unauthenticated(self):
        url = self.path

        # Unauthorized
        response = self.client.get(url)
        #kiosk
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized(self):
        url = self.path

        # User and has not the view_stats perms
        self.client.force_login(self.user)
        response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        url = self.path

        # super admin
        self.client.force_login(self.super_admin)
        response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        url = self.path

        # has permission
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_stats')
        )
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        url = self.path
        group = Group.objects.create(name='Scan stats Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_stats')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
