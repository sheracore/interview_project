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
        self.agent = Agent.objects.create(
            av_name='eset',
            api_ip='1.1.1.1',
            title='eset_av',
            active=False
        )
        generated_file = ContentFile(b"Some file content", name='update.file')
        self.file = UpdateFile.objects.create(
            file=generated_file, status_code=200, agent=self.agent,
        )
        self.url = reverse('updatefile-detail', kwargs={'pk': self.file.pk})

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.file.pk)
        self.assertEqual(response.data['agent'], self.agent.pk)


class Perms(UserTestCase):

    def setUp(self):
        super(Perms, self).setUp()
        self.agent = Agent.objects.create(
            av_name='clam',
            api_ip='1.1.1.1',
            title='clam_av'
        )
        generated_file = ContentFile(b"Some file content", name='update.file')
        self.file = UpdateFile.objects.create(
            file=generated_file, status_code=200, agent=self.agent,
        )
        self.url = reverse('updatefile-detail', kwargs={'pk': self.file.pk})

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
        self.assertEqual(response.data['id'], self.file.pk)
        self.assertEqual(response.data['agent'], self.agent.pk)

    def test_authorized(self):
        path = self.url
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_updatefile")
        )
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.file.pk)

    def test_group(self):
        path = self.url
        group = Group.objects.create(name="UpdateFile viewers")
        group.permissions.set(
            [Permission.objects.get(codename="view_updatefile")]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.file.pk)
