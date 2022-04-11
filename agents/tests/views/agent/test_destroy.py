from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.models.api import API
from agents.models import Agent
from users.test import UserTestCase


class Operation(UserTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.agent = Agent.objects.create(
            av_name='escan', api_ip='192.168.182.34', api_key='a1b2c33d4e'
        )
        # interval, created = IntervalSchedule.objects.get_or_create(every=10,
        #                                                   period='seconds')
        # pt = PeriodicTask.objects.create(
        #     task='agents.tasks.set_status',
        #     interval=interval,
        #     args=json.dumps([cls.agent.pk]))
        # cls.agent.pt = pt
        # cls.agent.save()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('agent-detail', kwargs={'pk': self.agent.pk})

    def test_ok(self):
        with self.assertNumQueries(7):
            response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Agent.objects.filter(pk=self.agent.pk).exists())


class Perms(UserTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.agent = Agent.objects.create(
            av_name='escan', api_ip='192.168.182.34', api_key='a1b2c33d4e'
        )
        # interval, created = IntervalSchedule.objects.get_or_create(every=10,
        #                                                   period='seconds')
        # pt = PeriodicTask.objects.create(
        #     task='agents.tasks.set_status',
        #     interval=interval,
        #     args=json.dumps([cls.agent.pk]))
        # cls.agent.pt = pt
        # cls.agent.save()

    def setUp(self):
        super().setUp()
        self.url = reverse('agent-detail', kwargs={'pk': self.agent.pk})

    def test_unauthenticated(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_not_staff(self):
        self.client.force_login(self.user)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_without_permission(self):
        self.client.force_login(self.admin)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_with_delete_agent_permission(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='delete_agent')
        )

        self.client.force_login(self.admin)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_with_group_permissions(self):
        group = Group.objects.create(name='Test Group')
        group.permissions.set(
            [
                Permission.objects.get(codename='delete_agent')
            ]
        )
        self.admin.groups.add(group)

        self.client.force_login(self.admin)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.delete(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_with_api_key(self):
        API.objects.create(key='foobar', owner=self.admin)
        response = self.client.delete(self.url, HTTP_X_API_KEY='foobar')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
