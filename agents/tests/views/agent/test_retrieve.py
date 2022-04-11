from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from agents.models import Agent
from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.agent = Agent.objects.create(
            av_name='escan', api_ip='192.168.182.34', api_key='a1b2c33d4e'
        )
        self.url = reverse('agent-detail', kwargs={'pk': self.agent.pk})

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.get(self.url)
        expected = Agent.objects.get(pk=self.agent.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], expected.id)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.agent = Agent.objects.create(
            av_name='escan', api_ip='192.168.182.34', api_key='a1b2c33d4e'
        )
        self.path = reverse('agent-detail', kwargs={'pk': self.agent.pk})

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
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_agent')
        )
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Agent Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_agent')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
