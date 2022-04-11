import socket

from rest_framework.reverse import reverse
from rest_framework.views import status
from unittest.mock import patch

from users.test import UserTestCase
from core.models.system import System


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        System.reset_settings()

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_disks_ok(self):
        response = self.client.get(reverse('system-disks'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_walk_disks_ok(self):
        response = self.client.patch(reverse('system-walk'),
                                     data={'path': './'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sys_info(self):
        response = self.client.get(reverse('system-info'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('rpyc.classic.connect')
    def test_check_printer(self, socket_receive):
        System.set_settings({'printer_ip': '127.0.0.1', 'printer_port': 80})
        response = self.client.patch(reverse('system-check-printer'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        socket_receive.assert_called()


class Perms(UserTestCase):
    pass
