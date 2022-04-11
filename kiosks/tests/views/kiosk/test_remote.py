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

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.get(
                reverse(
                    'kiosk-remote', kwargs={'pk': self.kiosk.pk,
                                            'url': '/scans'}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        kiosk = Kiosk.objects.create(
            serial='test',
            api_key='testkiosk', api_ip='192.168.182.33'
        )
        self.path = reverse('kiosk-remote',
                            kwargs={'pk': kiosk.pk, 'url': '/scans'})

    def test_unauthenticated(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='remote')
        )
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='Kiosk Remote Request')
        group.permissions.set(
            [Permission.objects.get(codename='remote')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
