
from rest_framework.reverse import reverse
from rest_framework.views import status

from core.models.api import API

from users.test import UserTestCase

from kiosks.models import Kiosk


class Operation(UserTestCase):
    """Test view functionality"""

    def setUp(self):
        super().setUp()
        # self.client.force_login(self.super_admin)
        self.api = API.objects.create(key='changeme', owner=self.super_admin)
        self.kiosk = Kiosk.objects.create(
            serial='test',
            api_key=self.api.key, api_ip='192.168.182.33'
        )
        self.path = reverse('kiosk-add-audit-log', kwargs={'pk': self.kiosk.pk})

    def test_create_auditlog_ok(self):
        """Test create auditlog by superuser"""
        data = {
            'kiosk': self.kiosk.pk,
            'action': 'device_add',
            'level': 'INFO',
            'message': 'message text'
        }
        headers = {'HTTP_X_API_KEY': self.api.key}
        response = self.client.post(self.path, data=data, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class Perms(UserTestCase):
    """Test view authentications and authurizations(permissions)"""

    def setUp(self):
        super().setUp()
        self.api = API.objects.create(key='changeme', owner=self.super_admin)
        self.kiosk = Kiosk.objects.create(
            serial='test',
            api_key=self.api.key, api_ip='192.168.182.33'
        )
        self.path = reverse('kiosk-add-audit-log', kwargs={'pk': self.kiosk.pk})
        self.data = {
            'kiosk': self.kiosk.pk,
            'action': 'device_add',
            'level': 'INFO',
            'message': 'message text'
        }

    def test_unauthenticated(self):
        response = self.client.post(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authorized(self):
        headers = {'HTTP_X_API_KEY': self.api.key}
        response = self.client.post(self.path, data=self.data, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
