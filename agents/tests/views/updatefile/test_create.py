from django.contrib.auth.models import Group, Permission
from rest_framework.reverse import reverse
from rest_framework.views import status

from agents.models import Agent, UpdateFile
from users.test import UserTestCase
from django.core.files.base import ContentFile
from rest_framework.test import APIRequestFactory


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
        self.url = reverse('agent-update-from-upload', kwargs={'pk': self.agent.pk})

        self.generated_file = ContentFile(b"Some file content", name='test.tar.gz')

    def test_ok(self):
        response = self.client.patch(self.url, format='multipart', data={'file': self.generated_file})
