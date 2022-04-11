from django.contrib.auth.models import User, Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.models import User
from users.test import UserTestCase


class Operation(UserTestCase):
    def setUp(self):
        super().setUp()
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
        self.client.force_login(self.super_admin)
        self.path = reverse('user-detail', kwargs={'pk': self.user.pk})

    def test_update_user(self):
        response = self.client.put(self.path, self.data)


        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_user = User.objects.get(username='test')
        self.assertTrue(new_user.check_password(self.data['password']))

    def test_invalid_update_user(self):
        response = self.client.put(self.path)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.path = reverse('user-detail', kwargs={'pk': self.user.pk})

    def test_unauthenticated(self):
        response = self.client.put(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='change_user')
        )
        self.client.force_login(self.admin)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.put(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='User Changer')
        group.permissions.set(
            [Permission.objects.get(codename='change_user')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.put(self.path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
