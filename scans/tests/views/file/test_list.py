from django.contrib.auth.models import Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from core.models.system import System
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
        System.reset_settings()
        file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create()
        first_file = File.objects.create(file=file, user=self.super_admin,
                                         session=session, progress=100)
        agent = Agent.objects.create(api_ip='192.168.100.158')
        self.scan = Scan.objects.create(
            agent=agent, file=first_file, infected_num=0,
            status_code=200
        )

    def test_all_ok(self):
        url = reverse('file-list')
        with self.assertNumQueries(8):
            response = self.client.get(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_id_ok(self):
        url = reverse('file-list')
        with self.assertNumQueries(15):
            response = self.client.get(url, {'session_id': '1'})

        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], File.objects.all().count())
        self.assertEqual(response.data['results'][0]['scan_progress'], 100)
        self.assertFalse(response.data['results'][0]['infected'])

    def test_none_infected(self):
        self.scan.status_code = 500
        self.scan.infected_num = None
        self.scan.save()
        url = reverse('file-list')
        with self.assertNumQueries(15):
            response = self.client.get(url, {'session_id': '1'})
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], File.objects.all().count())
        self.assertEqual(response.data['results'][0]['scan_progress'], 100)
        self.assertFalse(response.data['results'][0]['infected'])


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        setattr(settings, 'I_AM_A_KIOSK', False)

    def test_unauthenticated_kiosk(self):
        setattr(settings, 'I_AM_A_KIOSK', True)
        url = reverse('file-list')
        # Unauthorized
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated(self):
        url = reverse('file-list')
        # Unauthorized
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        url = reverse('file-list')
        # User and has not the view_file perms
        self.client.force_login(self.user)
        response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        url = reverse('file-list')
        # super admin
        self.client.force_login(self.super_admin)
        response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        url = reverse('file-list')
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        path = reverse('file-list')
        group = Group.objects.create(name='File Viewers')
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
