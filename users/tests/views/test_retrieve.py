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
        response = self.client.get(reverse('user-detail', kwargs={'pk': self.user.pk}))
        expected = User.objects.get(pk=self.user.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], expected.id)


class Perms(UserTestCase):

    def setUp(self):
        super().setUp()
        self.path = reverse('user-detail', kwargs={'pk': self.user.pk})

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
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_user')
        )
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self):
        self.client.force_login(self.user)
        response = self.client.get(self.path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        group = Group.objects.create(name='User Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_user')]
        )
        self.admin.groups.add(group)
        self.client.force_login(self.admin)
        response = self.client.get(self.path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
