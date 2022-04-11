from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase
from kiosks.models import Kiosk


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.kiosk = Kiosk.objects.create(
            serial='test',
            api_key='testkiosk', api_ip='192.168.182.33'
        )
        self.url = reverse('kiosk-detail', kwargs={'pk': self.kiosk.pk})

    def test_ok(self):
        with self.assertNumQueries(7):
            response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Kiosk.objects.filter(pk=self.user.pk).exists())


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.kiosk = Kiosk.objects.create(
            serial='test',
            api_key='testkiosk', api_ip='192.168.182.33'
        )
        self.url = reverse('kiosk-detail', kwargs={'pk': self.kiosk.pk})

    def test_unauthenticated(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_kiosk')
        )
        self.client.force_login(self.user)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Kiosk Destroyers')
        group.permissions.set(
            [Permission.objects.get(codename='delete_kiosk')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
