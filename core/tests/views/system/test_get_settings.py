from rest_framework.views import status
from django.urls import reverse

from users.test import UserTestCase
from core.models.system import System


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('system-settings')
        System.reset_settings()

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.get(path=self.url)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), System.get_settings())


# class Perms(UserTestCase):
#
#     def setUp(self):
#         super().setUp()
#         self.url = reverse('file-settings')
#         initiate_settings()
#
#     def test_unauthenticated(self):
#         # Unauthorized
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#
#     def test_unauthorized(self):
#         # User and has not the view_file perms
#         self.client.force_login(self.user)
#         response = self.client.get(path=self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
#
#     def test_superuser(self):
#         # super admin
#         self.client.force_login(self.super_admin)
#         response = self.client.get(path=self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_authorized(self):
#         # has permission
#         self.admin.user_permissions.add(
#             Permission.objects.get(codename='view_settings')
#         )
#         self.client.force_login(self.admin)
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_group(self):
#         group = Group.objects.create(name='Max Settings Viewers')
#         group.permissions.set(
#             [Permission.objects.get(codename='view_settings')]
#         )
#         self.user.groups.add(group)
#         self.client.force_login(self.user)
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
