from rest_framework.views import status
from rest_framework.reverse import reverse
from django.urls import reverse
from django.core.files.base import ContentFile
from django.contrib.auth.models import Permission, Group
from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.file = ContentFile(b"Some file content", name='test.mp3')
        self.url = reverse('video-list')

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok(self):
        response = self.client.post(
            path=self.url,
            data={
                'file': self.file,
                'is_active': True
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.file = ContentFile(b"Some file content", name='test.mp3')
        self.url = reverse('video-list')

    def test_unauthenticated(self):
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Video Create')
        group.permissions.set(
            [Permission.objects.get(codename='add_video')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
