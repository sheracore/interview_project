from django.contrib.auth.models import Group, Permission
from rest_framework.reverse import reverse
from rest_framework.views import status

from agents.models import Agent
from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File
from scans.models.scan import Scan
from django.core.files.base import ContentFile
from core.models.api import API


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('agent-list')
        self.agent = Agent.objects.create(
            av_name='eset',
            api_ip='192.168.182.34',
            title='eset_av',
            active=False
        )
        generated_file = ContentFile(b"Some file content", name='test.pdf')
        session = Session.objects.create()
        self.file1 = File.objects.create(
            file=generated_file, user=self.super_admin, session=session
        )
        session = Session.objects.create()
        self.file2 = File.objects.create(
            file=generated_file, user=self.super_admin, session=session
        )
        session = Session.objects.create()
        self.file3 = File.objects.create(
            file=generated_file, user=self.super_admin, session=session
        )
        self.scan = Scan.objects.create(
            agent=self.agent,
            file=self.file1,
            infected_num=1,
            scan_time=2
        )
        self.scan_2 = Scan.objects.create(
            agent=self.agent,
            file=self.file2,
            infected_num=0,
            scan_time=None
        )
        self.scan_3 = Scan.objects.create(
            agent=self.agent,
            file=self.file3,
            infected_num=3,
            scan_time=1
        )

    def test_all(self):
        with self.assertNumQueries(5):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        infected_count = Agent.objects.filter(
            scans__infected_num__gt=0).count()
        clean_count = Agent.objects.filter(scans__infected_num=0).count()
        total_scan_count = Scan.objects.all().count()
        mysterious_count = total_scan_count - (infected_count + clean_count)
        total_scan_time = int(self.scan.scan_time) + int(self.scan_3.scan_time)
        self.assertEqual(response.data['count'], Agent.objects.count())
        self.assertEqual(response.data['results'][0]['infected_count'],
                         infected_count)
        self.assertEqual(response.data['results'][0]['clean_count'],
                         clean_count)
        self.assertEqual(response.data['results'][0]['mysterious_count'],
                         mysterious_count)
        self.assertEqual(response.data['results'][0]['avg_scan_time'],
                         total_scan_time/2)

    def test_search_by_av_name(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?search_av_name={self.agent.av_name}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.filter(av_name__icontains=self.agent.av_name).count()
        )

    def test_search_by_api_ip(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?search_api_ip={self.agent.api_ip}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.filter(api_ip__icontains=self.agent.api_ip).count()
        )

    def test_search_by_title(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?search_title={self.agent.title}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.filter(title__icontains=self.agent.title).count()
        )

    def test_filter_by_title(self):
        with self.assertNumQueries(5):
            response = self.client.get(self.url + f'?title={self.agent.title}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.filter(title=self.agent.title).count()
        )

    def test_filter_by_api_ip(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?api_ip={self.agent.api_ip}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.filter(api_ip=self.agent.api_ip).count()
        )

    def test_filter_by_active(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?active={self.agent.active}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.filter(active=self.agent.active).count()
        )

    def test_order_by_title(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?ordering={self.agent.title}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['results'][0]['id'],
            Agent.objects.all().order_by('title').first().pk
        )

    def test_order_by_active(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?ordering={self.agent.active}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['results'][0]['id'],
            Agent.objects.all().order_by('active').first().pk
        )

    def test_order_by_created_at(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?ordering={self.agent.created_at}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.all().order_by('created_at').count()
        )

    def test_order_by_modified_at(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?ordering={self.agent.modified_at}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.all().order_by('modified_at').count()
        )

    def test_order_by_av_name(self):
        with self.assertNumQueries(5):
            response = self.client.get(
                self.url + f'?ordering={self.agent.av_name}'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            Agent.objects.all().order_by('av_name').count()
        )


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('agent-list')

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='view_agent')
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized_with_api_key_and_allowed_hosts(self):
        path = self.url
        self.api = API.objects.create(
            title='for-test',
            allowed_hosts=[
                '127.0.0.1'
            ],
            key='foobar',
            owner=self.user
        )
        response = self.client.get(path, HTTP_X_API_KEY='foobar')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized_with_api_key_and_bad_allowed_hosts(self):
        path = self.url
        self.api = API.objects.create(
            title='for-test',
            allowed_hosts=[
                '1.1.1.1'
            ],
            key='foobar',
            owner=self.user
        )
        response = self.client.get(path, HTTP_X_API_KEY='foobar')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authorized_with_api_key_and_none_allowed_hosts(self):
        path = self.url
        self.api = API.objects.create(
            title='for-test',
            key='foobar',
            owner=self.user
        )
        response = self.client.get(path, HTTP_X_API_KEY='foobar')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='Agent Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_agent')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
