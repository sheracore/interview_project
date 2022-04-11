from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from django.contrib.auth.models import Permission, Group

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File
from scans.models.scan import Scan, ScanReport
from agents.models import Agent


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)
        self.agent = Agent.objects.create(av_name='test', api_ip='192.168.100.158')
        self.scan = Scan.objects.create(agent=self.agent, file=self.file)
        self.path = reverse('scan-add-report')

    def test_ok(self):
        url = self.path
        with self.assertNumQueries(5):
            data = {
                'name': 'test',
            }
            response = self.client.post(path=url, data=data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], Scan.objects.last().pk)


class Perm(UserTestCase):

    def setUp(self):
        super().setUp()
        self.path = reverse('scan-add-report')

    def test_unauthenticated(self):
        url = self.path
        # Unauthorized
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        url = self.path
        self.client.force_login(self.user)
        response = self.client.post(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        url = self.path
        self.client.force_login(self.super_admin)
        data = {
            'name': 'test',
        }
        response = self.client.post(path=url, data=data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

