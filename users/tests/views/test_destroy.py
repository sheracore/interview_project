from django.contrib.auth.models import User, Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.models import User
from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)

    def test_ok(self):
        response = self.client.delete(reverse('user-detail', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user_exists = User.objects.filter(pk=self.user.pk).exists()
        self.assertFalse(user_exists)


class Perms(UserTestCase):
    def setUp(self):
        super().setUp()
        self.path = reverse('user-detail', kwargs={'pk': self.user.pk})

    def test_unauthenticated(self):
        response = self.client.delete(self.path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        self.client.force_login(self.admin)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        self.client.force_login(self.super_admin)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_user')
        )
        self.client.force_login(self.user)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='User Destroyers')
        group.permissions.set(
            [Permission.objects.get(codename='delete_user')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.delete(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nobody_can_destroy_superuser(self):
        path = reverse('user-detail', kwargs={'pk': self.super_admin.pk})
        self.client.force_login(self.super_admin)
        response = self.client.delete(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
