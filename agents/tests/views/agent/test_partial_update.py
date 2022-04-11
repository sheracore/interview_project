import json
from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from agents.models import Agent
from users.test import UserTestCase


class Operation(UserTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.agent = Agent.objects.create(
            av_name='escan', api_ip='192.168.182.34', api_key='a1b2c33d4e'
        )
        # interval, created = IntervalSchedule.objects.get_or_create(every=10,
        #                                                            period='seconds')
        # self.pt = PeriodicTask.objects.create(
        #     task='agents.tasks.set_status',
        #     interval=interval,
        #     args=json.dumps([self.agent.pk]))
        # self.agent.pt = self.pt
        # self.agent.save()
        self.path = reverse('agent-detail', kwargs={'pk': self.agent.pk})
        self.data = {'api_ip': '192.168.182.33'}

    def test_ok(self):
        with self.assertNumQueries(5):
            response = self.client.patch(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['api_ip'], self.data['api_ip'])

    def test_deactivate(self):
        data = {
            'active': False
        }
        response = self.client.patch(self.path, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()

    def test_activate(self):
        self.agent.active = False
        self.agent.save()
        data = {
            'active': True
        }
        response = self.client.patch(self.path, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.agent = Agent.objects.create(
            av_name='escan', api_ip='192.168.182.34', api_key='a1b2c33d4e'
        )
        self.path = reverse('agent-detail', kwargs={'pk': self.agent.pk})
        self.data = {'av_name': 'eset'}

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
            Permission.objects.get(codename='change_agent')
        )
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Agent Changer')
        group.permissions.set(
            [Permission.objects.get(codename='change_agent')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
