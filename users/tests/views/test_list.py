from django.contrib.auth.models import User, Group, Permission
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.models import User
from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)

    def test_all(self):
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], User.objects.count())

    def test_search_by_username(self):
        response = self.client.get(reverse('user-list')+'?search=admin')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['count'],
            User.objects.filter(username__icontains='admin').count()
        )


class Perms(UserTestCase):

    def test_unauthenticated(self):
        path = reverse('user-list')

        response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        path = reverse('user-list')

        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        path = reverse('user-list')

        self.client.force_login(self.super_admin)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized(self):
        path = reverse('user-list')

        self.user.user_permissions.add(
            Permission.objects.get(codename='view_user')
        )
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group(self):
        path = reverse('user-list')

        group = Group.objects.create(name='User Viewers')
        group.permissions.set(
            [Permission.objects.get(codename='view_user')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_200_OK)