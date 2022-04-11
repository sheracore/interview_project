from rest_framework.reverse import reverse
from django.contrib.auth.models import Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File
from scans.models.scan import Scan
from agents.models import Agent

from django.conf import settings


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
        self.file.scanned_serial = 3
        self.file.save()
        with self.assertNumQueries(10):
            response = self.client.get(
                reverse('file-scans', kwargs={'pk': self.file.pk})
            )
        expected = Scan.objects.get(file=self.file.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], expected.id)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        setattr(settings, 'I_AM_A_KIOSK', False)
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.admin, session=session)
        self.agent = Agent.objects.create(api_ip='192.168.100.158')
        Scan.objects.create(agent=self.agent, file=self.file)
        self.path = reverse('file-scans', kwargs={'pk': self.file.pk})

    def test_none_owner_unauthenticated(self):
        # tried to scans file without owner
        session = Session.objects.create()
        file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=None, session=session)
        Scan.objects.create(agent=self.agent, file=file)
        response = self.client.get(reverse(
            'file-scans', kwargs={'pk': file.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_kiosk(self):
        # tried to scans file with owner
        setattr(settings, 'I_AM_A_KIOSK', True)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated(self):
        # tried to scans file with owner
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='File Viewers')
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
