from django.contrib.auth.models import Group, Permission
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.models.api import API
from agents.models import Agent
from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('agent-avs')

    def test_ok(self):
        with self.assertNumQueries(3):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], Agent.av_names)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('agent-avs')

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_not_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_without_permission(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_with_add_agent_permission(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='add_agent')
        )

        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_with_change_agent_permission(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='change_agent')
        )

        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_with_group_permissions(self):
        group = Group.objects.create(name='Test Group')
        group.permissions.set(
            [
                Permission.objects.get(codename='add_agent'),
                Permission.objects.get(codename='change_agent')
            ]
        )
        self.admin.groups.add(group)

        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_with_api_key(self):
        API.objects.create(key='foobar', owner=self.admin)
        response = self.client.get(self.url, HTTP_X_API_KEY='foobar')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
