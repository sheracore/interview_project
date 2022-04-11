from django.contrib.auth.models import Group
from rest_framework.views import status
from django.urls import reverse
from django.core.files.base import ContentFile

from users.test import UserTestCase
from scans.models.file import File
from scans.models.session import Session


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        session = Session.objects.create(progress=100)
        file = ContentFile(b"Some file content", name='test.pdf')
        self.first_file = File.objects.create(
            file=file, user=self.super_admin, session=session)
        self.url = reverse('file-terminate') + '?session_id=1'

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.patch(path=self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create(progress=100)
        self.first_file = File.objects.create(
            file=file, user=self.super_admin, session=session)
        self.url = reverse('file-terminate') + '?session_id=1'

    def test_unauthenticated(self):
        # Unauthorized
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized(self):
        # User and has not the view_file perms
        self.client.force_login(self.user)
        response = self.client.patch(path=self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        # super admin
        self.client.force_login(self.super_admin)
        response = self.client.patch(path=self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.client.force_login(self.admin)
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='File Terminate')
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
