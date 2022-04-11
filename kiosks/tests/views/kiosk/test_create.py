from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)

    def test_ok(self):
        data = {
            'serial': 'test',
            'settings': 'I_AM_A_KIOSK',
            'api_key': 'testkiosk',
            'api_ip': '192.168.182.33'
        }
        with self.assertNumQueries(5):
            response = self.client.post(reverse('kiosk-list'), data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.data = {
            'serial': 'test',
            'settings': 'I_AM_A_KIOSK',
            'api_key': 'testkiosk',
            'api_ip': '192.168.182.33'
        }
        self.path = reverse('kiosk-list')

    def test_unauthenticated(self):
        response = self.client.post(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authorized(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='add_kiosk')
        )
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_group(self):
        group = Group.objects.create(name='Kiosk Creators')
        group.permissions.set(
            [Permission.objects.get(codename='add_kiosk')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
