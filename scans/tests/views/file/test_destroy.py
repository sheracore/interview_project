from django.core.files.base import ContentFile
from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File

from django.conf import settings


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        generated_file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create()
        self.file = File.objects.create(
            file=generated_file, user=self.super_admin, session=session
        )

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok(self):
        with self.assertNumQueries(7):
            response = self.client.delete(
                reverse('file-detail', kwargs={'pk': self.file.pk})
            )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        setattr(settings, 'I_AM_A_KIOSK', False)
        generated_file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create()
        file = File.objects.create(
            file=generated_file, user=self.admin,
            session=session,
        )
        self.path = reverse('file-detail', kwargs={'pk': file.pk})

    def test_unauthenticated(self):
        response = self.client.delete(self.path)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_kiosk(self):
        setattr(settings, 'I_AM_A_KIOSK', True)
        response = self.client.delete(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.user)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized_kiosk(self):
        setattr(settings, 'I_AM_A_KIOSK', True)
        self.client.force_login(self.user)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_authorized(self):
        self.client.force_login(self.admin)
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_file')
        )
        self.admin.user_permissions.add(
            Permission.objects.get(codename='delete_file')
        )
        response = self.client.delete(self.path)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_group(self):
        response = self.client.delete(self.path)
        group = Group.objects.create(name='File Destroyer')
        group.permissions.set(
            [Permission.objects.get(codename='delete_file')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
