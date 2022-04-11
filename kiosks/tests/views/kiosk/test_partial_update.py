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
        self.path = reverse('kiosk-detail', kwargs={'pk': self.kiosk.pk})
        self.data = {'api_ip': '192.168.182.33'}

    def test_ok(self):
        with self.assertNumQueries(5):
            response = self.client.patch(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['api_ip'], self.data['api_ip'])


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.kiosk = Kiosk.objects.create(
            serial='test',
            api_key='testkiosk', api_ip='192.168.182.33'
        )
        self.path = reverse('kiosk-detail', kwargs={'pk': self.kiosk.pk})
        self.data = {'api_ip': '192.168.182.33'}

    def test_unauthenticated(self):
        response = self.client.patch(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='change_kiosk')
        )
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Kiosk Changer')
        group.permissions.set(
            [Permission.objects.get(codename='change_kiosk')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
