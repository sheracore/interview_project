from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)
        self.url = reverse('mimetype-list')

    def test_ok(self):
        with self.assertNumQueries(4):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.data['results'], mimetypes)


# class Perms(UserTestCase):
#
#     def setUp(self):
#         super().setUp()
#         self.url = reverse('file-mimetypes')
#
#     def test_unauthenticated(self):
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#
#     def test_unauthorized(self):
#         self.client.force_login(self.user)
#         response = self.client.get(self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
#
#     def test_superuser(self):
#         self.client.force_login(self.super_admin)
#         response = self.client.get(self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_authorized(self):
#         self.user.user_permissions.add(
#             Permission.objects.get(codename='view_settings')
#         )
#         self.client.force_login(self.user)
#         response = self.client.get(self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#         self.user.user_permissions.add(
#             Permission.objects.get(codename='view_settings')
#         )
#         self.client.force_login(self.user)
#         response = self.client.get(self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_group(self):
#         group = Group.objects.create(name='Mimetypes Viewer')
#         group.permissions.set(
#             [Permission.objects.get(codename='view_settings')]
#         )
#         self.user.groups.add(group)
#         self.client.force_login(self.user)
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
