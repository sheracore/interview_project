from rest_framework.reverse import reverse
from django.contrib.auth.models import Group, Permission
from rest_framework.views import status
from django.urls import reverse

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

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.get(
                reverse('kiosk-detail', kwargs={'pk': self.kiosk.pk}))
        expected = Kiosk.objects.get(pk=self.kiosk.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], expected.id)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        kiosk = Kiosk.objects.create(
            serial='test',
            api_key='testkiosk', api_ip='192.168.182.33'
        )
        self.path = reverse('kiosk-detail', kwargs={'pk': kiosk.pk})

    def test_unauthenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized(self):
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.client.force_login(self.admin)
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_kiosk')
        )
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='Kiosk Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_kiosk')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
