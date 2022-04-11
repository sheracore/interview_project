from rest_framework.views import status
from rest_framework.reverse import reverse
from django.urls import reverse
from django.core.files.base import ContentFile
from django.contrib.auth.models import Permission, Group
from users.test import UserTestCase
from core.models import Video


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        file = ContentFile(b"Some file content", name='test.mp3')
        self.video = Video.objects.create(file=file, is_active=True)
        self.url = reverse('video-activation', kwargs={'pk': self.video.pk})

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok(self):
        url = self.url
        response = self.client.patch(
            path=url,
            data={
                'is_active': 'true'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()

        file = ContentFile(b"Some file content", name='test.mp3')
        self.video = Video.objects.create(file=file, is_active=False)
        self.url = reverse('video-activation', kwargs={'pk': self.video.pk})

    def test_unauthenticated(self):
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        url = self.url
        self.client.force_login(self.user)
        response = self.client.patch(url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_video')
        )
        self.client.force_login(self.user)
        response = self.client.patch(self.url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='Video Change')
        group.permissions.set(
            [Permission.objects.get(codename='change_video')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.patch(self.url)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
