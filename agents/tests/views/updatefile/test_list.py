from django.contrib.auth.models import Group, Permission
from rest_framework.reverse import reverse
from rest_framework.views import status

from agents.models import Agent, UpdateFile
from users.test import UserTestCase
from django.core.files.base import ContentFile


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('updatefile-list')
        self.agent = Agent.objects.create(
            av_name='eset',
            api_ip='1.1.1.1',
            title='eset_av',
            active=False
        )
        self.agent1 = Agent.objects.create(
            av_name='clamav',
            api_ip='1.1.1.2',
            title='clam_av',
            active=False
        )
        generated_file = ContentFile(b"Some file content", name='test.pdf')
        self.file = UpdateFile.objects.create(
            file=generated_file, status_code=200, agent=self.agent,
        )
        generated_file1 = ContentFile(b"Some file content", name='1test.pdf')
        self.file = UpdateFile.objects.create(
            file=generated_file1, status_code=0, agent=self.agent1,
        )
        generated_file2 = ContentFile(b"Some file content", name='2-test.pdf')
        self.file = UpdateFile.objects.create(
            file=generated_file2, status_code=400, agent=self.agent1,
        )

    def test_ok(self):
        with self.assertNumQueries(5):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], UpdateFile.objects.all().count())

    def test_by_filter_agent(self):
        path = f"{self.url}?agent={self.agent.pk}"
        with self.assertNumQueries(6):
            response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], UpdateFile.objects.filter(agent=self.agent).count())

        path = f"{self.url}?agent={self.agent1.pk}"
        with self.assertNumQueries(6):
            response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], UpdateFile.objects.filter(agent=self.agent1).count())


class Perms(UserTestCase):

    def setUp(self):
        super(Perms, self).setUp()
        self.url = reverse('updatefile-list')
        self.agent = Agent.objects.create(
            av_name='clam',
            api_ip='1.1.1.1',
            title='clam_av',
            active=False
        )
        generated_file = ContentFile(b"Some file content", name='update.file')
        self.file = UpdateFile.objects.create(
            file=generated_file, status_code=200, agent=self.agent,
        )

    def test_unauthenticated(self):
        path = self.url
        response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        path = self.url
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        path = self.url
        self.client.force_login(self.super_admin)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], UpdateFile.objects.all().count())

    def test_authorized(self):
        path = self.url
        self.user.user_permissions.add(
            Permission.objects.get(codename='view_updatefile')
        )
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        path = self.url
        group = Group.objects.create(name='UpdateFile Viewrs')
        group.permissions.set(
            [Permission.objects.get(codename='view_updatefile')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
