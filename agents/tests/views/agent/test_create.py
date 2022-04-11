from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.models.api import API

from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('agent-list')

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok(self):
        data = {
            'av_name': 'eset',
            'api_ip': '192.168.182.34',
            'api_key': 'a1b2c33d4e'
        }
        with self.assertNumQueries(4):
            response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_av_name(self):
        data = {
            'av_name': 'invalid',
            'api_ip': '192.168.182.34',
            'api_key': 'a1b2c33d4e'
        }
        with self.assertNumQueries(3):
            response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('agent-list')

    def test_unauthenticated(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_not_staff(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_without_permission(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_with_add_agent_permission(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='add_agent')
        )

        self.client.force_login(self.admin)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_with_group_permissions(self):
        group = Group.objects.create(name='Test Group')
        group.permissions.set(
            [
                Permission.objects.get(codename='add_agent')
            ]
        )
        self.admin.groups.add(group)

        self.client.force_login(self.admin)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_with_api_key(self):
        API.objects.create(key='foobar', owner=self.admin)
        response = self.client.post(self.url, HTTP_X_API_KEY='foobar')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
