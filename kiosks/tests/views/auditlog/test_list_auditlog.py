from django.contrib.auth.models import Permission, Group

from rest_framework.reverse import reverse
from rest_framework.views import status

from core.models.api import API

from users.test import UserTestCase

from kiosks.models import Kiosk, KioskAuditLog


class Operation(UserTestCase):
    """Test view functionality"""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.api = API.objects.create(key='changeme', owner=self.super_admin)
        self.kiosk = Kiosk.objects.create(
            serial='test',
            api_key=self.api.key, api_ip='192.168.182.33'
        )
        self.auditlog = KioskAuditLog.objects.create(
            kiosk=self.kiosk,
            action='device_add'
        )

        self.path = reverse('kioskauditlog-list')

    def test_list_auditlog_ok(self):
        """Test create auditlog by superuser"""
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'],
                         KioskAuditLog.objects.all().count())
        self.assertEqual(response.data['results'][0]['kiosk']['id'],
                         self.auditlog.kiosk.pk)
        self.assertEqual(response.data['results'][0]['action'],
                         self.auditlog.action)


class Perms(UserTestCase):
    """Test view authentications and authurizations(permissions)"""

    def setUp(self):
        super().setUp()
        self.path = reverse('kioskauditlog-list')

    def test_unauthenticated(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_kioskauditlog',
                                   content_type__app_label='kiosks')
        )
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='Auditlog Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_kioskauditlog',
                                    content_type__app_label='kiosks')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
