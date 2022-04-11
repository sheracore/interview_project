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
        # pt = PeriodicTask.objects.create(
        #     task='agents.tasks.set_status',
        #     interval=interval,
        #     args=json.dumps([self.agent.pk]))
        # self.agent.pt = pt
        # self.agent.save()

    def test_av_given(self):
        data = {'av_name': 'eset',
                     'api_ip': '192.168.182.38',
                     'api_key': 'w8m2p33k0p'}
        path = reverse('agent-detail', kwargs={'pk': self.agent.pk})
        with self.assertNumQueries(5):
            response = self.client.put(path, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['api_ip'], data['api_ip'])
        self.assertEqual(response.data['av_name'], self.agent.av_name)

    def test_not_given(self):
        dat = {'api_ip': '192.168.182.38',
                   'api_key': 'w8m2p33k0p'}
        path_ = reverse('agent-detail', kwargs={'pk': self.agent.pk})
        with self.assertNumQueries(5):
            res = self.client.patch(path_, dat)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.path = reverse('agent-detail', kwargs={'pk': self.user.pk})

    def test_unauthenticated(self):
        response = self.client.put(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='change_agent')
        )
        self.client.force_login(self.admin)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Agent Changer')
        group.permissions.set(
            [Permission.objects.get(codename='change_agent')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.put(self.path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
