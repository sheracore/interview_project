from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase
from core.models.system import System


class Operation(UserTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.path = reverse('system-settings')
        self.data = {
            'max_file_size': 26214400,
            'mimetypes': ['text/plain', 'application/pdf'],
            'ftp_host': '1.1.1.1',
            'ftp_user': 'asdfg',
            'ftp_pass': 'asdfg',
            'ftp_port': 80,
            'delete_file_after_scan': False,
            'clean_acceptance_index': 0.5,
            'valid_acceptance_index': 0.5,
            'log': True,
            'log_http_url': 'http://viruspod.ir',
            'log_http_method': 'POST',
            'log_http_headers': {
                'api-key': 'changeme'
            }
        }
        System.reset_settings()

    def test_ok(self):
        response = self.client.patch(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_pincode_ok(self):
        response = self.client.patch(
                self.path, data={'pincode': 654321}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(System.decrypt_password(response.data['pincode'])), 654321)

    def test_with_max_file_size(self):
        response = self.client.patch(
                self.path, data={'max_file_size': 26214400}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_with_mimetypes(self):
        response = self.client.patch(
                self.path, data={'mimetypes': ['application/pdf']}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    # def test_with_invalid_mimetypes(self):
    #     response = self.client.patch(
    #             self.path, data={'mimetypes': ['appliation/pdf']}
    #         )
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_data(self):
        response = self.client.patch(self.path, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_none_max_file_size(self):
        response = self.client.patch(
                self.path, data={'max_file_size': None}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_empty_mimetypes(self):
    #     response = self.client.patch(
    #             self.path, data={'mimetypes': []}
    #         )
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_none_mimetypes(self):
        response = self.client.patch(
                self.path, data={'mimetypes': None}
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ftp_host_ok(self):
        response = self.client.patch(self.path, data={'ftp_host': '1.1.1.1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_ftp_user_ok(self):
        response = self.client.patch(self.path, data={'ftp_user': 'asdfg'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_ftp_pass_ok(self):
        response = self.client.patch(self.path, data={'ftp_pass': 'asdfg'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_ftp_port_ok(self):
        response = self.client.patch(self.path, data={'ftp_port': 80})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_ftp_port_bad_request(self):
        response = self.client.patch(self.path, data={'ftp_port': None})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_file_after_scan_ok(self):
        response = self.client.patch(self.path, data={'delete_file_after_scan': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_valid_input_slots(self):
        pci_slot = System.get_pci_slots()[0]
        response = self.client.patch(self.path, data={'input_slots': [pci_slot]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_none_input_slots(self):
        response = self.client.patch(self.path, data={'input_slots': None})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_empty_input_slots(self):
        response = self.client.patch(self.path, data={'input_slots': []})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    # def test_invalid_input_slots(self):
    #     response = self.client.patch(self.path, data={'input_slots': ['invalid_slot_name']})
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_clean_acceptance_index_ok(self):
        response = self.client.patch(self.path, data={'clean_acceptance_index': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_clean_acceptance_index_bad_request(self):
        response = self.client.patch(self.path, data={'clean_acceptance_index': 2})
        res = self.client.patch(self.path, data={'clean_acceptance_index': 0})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_acceptance_index_ok(self):
        response = self.client.patch(self.path, data={'valid_acceptance_index': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, System.get_settings())

    def test_valid_acceptance_index_bad_request(self):
        response = self.client.patch(self.path, data={'valid_acceptance_index': 2})
        res = self.client.patch(self.path, data={'valid_acceptance_index': 0})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_syslog_ok(self):
        response = self.client.patch(self.path, data={'syslog_ip': '1.1.1.1', 'syslog_port': 514, 'syslog': True })
        res = self.client.patch(self.path, data={'syslog_ip': '1.1.1.1', 'syslog_port': 514, 'syslog': True })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.path = reverse('system-settings')
        System.reset_settings()

    def test_unauthenticated(self):
        response = self.client.patch(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.patch(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.patch(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='change_app_settings')
        )
        self.client.force_login(self.admin)
        response = self.client.patch(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.patch(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='App Settings Updaters')
        group.permissions.set(
            [Permission.objects.get(codename='change_app_settings')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.patch(self.path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
