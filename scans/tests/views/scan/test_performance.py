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
            user=self.super_admin, session=session)  # 13785964 ~= 14mb
        self.agent = Agent.objects.create(api_ip='1.1.1.1')
        self.scan = Scan.objects.create(agent=self.agent, file=self.file, scan_time=35)

        # new file
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # 1478640 ~= 1.5mb
        Scan.objects.create(agent=self.agent, file=self.file, scan_time=16)

        # new file
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # ~= 1700000 1.7mb
        Scan.objects.create(agent=self.agent, file=self.file, scan_time=19)

        # new file
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # 18000000 ~= 18mb
        Scan.objects.create(agent=self.agent, file=self.file,  scan_time=68)

        # new file
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # 180000000 ~= 180mb
        Scan.objects.create(agent=self.agent, file=self.file, scan_time=120)

        # new file
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # 2300000000 ~= 2.14Gb
        Scan.objects.create(agent=self.agent, file=self.file, scan_time=3600)

        # new file
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # 180000000 ~= 360mb
        Scan.objects.create(agent=self.agent, file=self.file, scan_time=150)
        self.scans_counter = 4
        self.path = f"{reverse('scan-performance')}?agent={self.agent.pk}"

    def test_ok(self):
        url = self.path
        counter = self.scans_counter

        with self.assertNumQueries(5):
            response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for i in range(counter):
            if response.data['results'][i]['size_range'] == '100-500Mb':
                self.assertEqual(response.data['results'][i]['avg_scan_time'], 135)

            elif response.data['results'][i]['size_range'] == '10-100Mb':
                self.assertEqual(response.data['results'][i]['avg_scan_time'], 51.5)

            elif response.data['results'][i]['size_range'] == '1Kb-10Mb':
                self.assertEqual(response.data['results'][i]['avg_scan_time'], 17.5)

            elif response.data['results'][i]['size_range'] == '1-5Gb':
                self.assertEqual(response.data['results'][i]['avg_scan_time'], 3600)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.agent = Agent.objects.create(api_ip='1.1.1.1')
        session = Session.objects.create()
        self.file = File.objects.create(
            file=ContentFile(b"Some file content", name='test.pdf'),
            user=self.super_admin, session=session)  # 13785964 ~= 14mb
        Scan.objects.create(agent=self.agent, file=self.file, scan_time=35)
        self.path = f"{reverse('scan-performance')}?agent={self.agent.pk}"

    def test_unauthenticated(self):
        url = self.path

        # Unauthorized
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        url = self.path

        self.client.force_login(self.user)
        response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        url = self.path

        self.client.force_login(self.super_admin)
        response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        url = self.path

        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_performance')
        )
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        url = self.path

        group = Group.objects.create(name='Scanners Performance Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_performance')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
