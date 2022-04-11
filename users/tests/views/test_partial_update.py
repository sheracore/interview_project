from django.contrib.auth.models import User, Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.models import User
from users.test import UserTestCase


class Operation(UserTestCase):
    def setUp(self):
        super().setUp()
        self.path = reverse('user-detail', kwargs={'pk': self.user.pk})
        self.client.force_login(self.super_admin)
        self.data = {
            'username': 'test',
            'password': 't1e2s3t4',
            'full_name': 'Test',
            'email': 'test@test.com',
            'phone_number': '+989127774433',
            'is_deleted': False,
            'is_active': True,
            'is_staff': True,
            'is_superuser': False,
        }

    def test_partial_update_user(self):
        response = self.client.patch(self.path, data=self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_user = User.objects.get(username='test')
        self.assertTrue(new_user.check_password(self.data['password']))

    def test_invalid_update_user(self):
        invalid_data = self.data['username'] = ''
        response = self.client.patch(self.path, data=invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivating_super_user(self):
        data = {'is_active': False}
        path = reverse('user-detail', kwargs={'pk': self.super_admin.pk})
        response = self.client.patch(path, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.data = {
            'username': 'test1',
            'password': 'lll1e2s3t4',
            'full_name': 'Test1',
            'email': 'test@test1.com',
            'phone_number': '+989127774433',
            'is_deleted': False,
            'is_active': True,
            'is_staff': True,
            'is_superuser': False
        }
        self.path = reverse('user-detail', kwargs={'pk': self.user.pk})

    def test_unauthenticated(self):
        response = self.client.patch(self.path, data=self.data)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertNotEqual(response.status_code,
                            status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='change_user')
        )
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertNotEqual(response.status_code,
                            status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.patch(self.path, data=self.data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        group = Group.objects.create(name='User Changer')
        group.permissions.set(
            [Permission.objects.get(codename='change_user')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.patch(self.path, data=self.data)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
