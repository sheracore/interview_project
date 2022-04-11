from rest_framework.views import status
from rest_framework.reverse import reverse
from django.urls import reverse
from django.core.files.base import ContentFile
from core.models import Video
from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        file = ContentFile(b"Some file content", name='test.mp3')
        self.video = Video.objects.create(file=file, is_active=True)
        self.url = reverse('video-current')

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['file'], self.video.file.url)
        self.assertEqual(response.data['is_active'], self.video.is_active)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.file = ContentFile(b"Some file content", name='test.mp3')
        self.url = reverse('video-current')

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
