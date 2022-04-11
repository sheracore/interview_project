from django.contrib.auth.models import Permission, Group
from django.contrib.auth import get_user_model
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase

User = get_user_model()


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super_admin)

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_ok_and_no_body_can_create_superuser(self):
        data = {
            'username': 'test1',
            'password': 'lll1e2s3t4',
            'full_name': 'Test1',
            'email': 'test@test1.com',
            'phone_number': '+989127774433',
            'is_staff': True,
            'is_superuser': True,
            'groups': [self.group.pk]
        }
        response = self.client.post(reverse('user-list'), data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(username='test1')
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(
            new_user.groups.values('pk'),
            [self.group.pk]
        )
        self.assertTrue(new_user.check_password(data['password']))

    def test_is_active(self):
        data = {
            'username': 'test1',
            'password': 'lll1e2s3t4',
            'full_name': 'Test1',
            'email': 'test@test1.com',
            'phone_number': '+989127774433',
            'is_staff': True,
            'is_active': False
        }
        response = self.client.post(reverse('user-list'), data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(User.objects.last().is_active)

    def test_invalid_password(self):
        data = {
            'username': 'test1',
            'password': '1234',
            'full_name': 'Test1',
            'email': 'test@test1.com',
            'phone_number': '+989127774433',
            'is_staff': True,
            'is_active': False
        }
        response = self.client.post(reverse('user-list'), data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {
            'username': 'test1',
            'password': 'test',
            'full_name': 'Test1',
            'email': 'test@test1.com',
            'phone_number': '+989127774433',
            'is_staff': True,
            'is_active': False
        }
        response = self.client.post(reverse('user-list'), data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class Perms(UserTestCase):

    def test_unauthenticated(self):
        path = reverse('user-list')

        response = self.client.post(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized(self):
        path = reverse('user-list')

        self.client.force_login(self.admin)
        response = self.client.post(path)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser(self):
        path = reverse('user-list')

        self.client.force_login(self.super_admin)
        response = self.client.post(path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized(self):
        path = reverse('user-list')

        self.user.user_permissions.add(
            Permission.objects.get(codename='add_user')
        )
        self.client.force_login(self.user)
        response = self.client.post(path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group(self):
        path = reverse('user-list')

        group = Group.objects.create(name='User Creators')
        group.permissions.set(
            [Permission.objects.get(codename='add_user')]
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)
        response = self.client.post(path)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_superuser_can_set_groups(self):
        path = reverse('user-list')

        self.user.user_permissions.add(
            Permission.objects.get(codename='add_user')
        )
        self.client.force_login(self.user)
        data = {
            'username': 'test1',
            'password': 'lll1e2s3t4',
            'groups': [self.group.pk]
        }
        response = self.client.post(path, data=data)
        self.client.logout()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
