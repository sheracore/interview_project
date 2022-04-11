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
        url = reverse('kiosk-list')
        with self.assertNumQueries(5):
            response = self.client.get(path=url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], Kiosk.objects.all().count())
        self.assertEqual(
            response.data['results'][0]['api_ip'], self.kiosk.api_ip
        )
        self.assertEqual(
            response.data['results'][0]['api_key'], self.kiosk.api_key
        )


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('kiosk-list')

    def test_unauthenticated(self):
        # Unauthorized
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        # User and has not the view_file perms
        self.client.force_login(self.user)
        response = self.client.get(path=self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        # super admin
        self.client.force_login(self.super_admin)
        response = self.client.get(path=self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_kiosk')
        )
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='Kiosk Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_kiosk')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
