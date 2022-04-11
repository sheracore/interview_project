from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase


class Operation(UserTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_retrieve(self):
        response = self.client.get(reverse('user-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user.pk)

    def test_update(self):
        data = {
            'username': 'new_username',
            'full_name': 'new_fullname',
            'email': 'new@user.com',
            'phone_number': '+989127774433'
        }
        response = self.client.put(reverse('user-me'), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, data['username'])
        self.assertEqual(response.data['username'], data['username'])

    def test_partial_update(self):
        data = {
            'full_name': 'just_fullname'
        }
        response = self.client.patch(reverse('user-me'), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, data['full_name'])
        self.assertEqual(response.data['full_name'], data['full_name'])

    def test_change_password(self):
        # new password doesn't match re-new password.
        data = {
            'current_password': '1234',
            'new_password': 'new',
            're_new_password': 'newwwwwwwwwww'
        }
        response = self.client.patch(reverse('user-change-my-password'),
                                     data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['non_field_errors'][0].code,
                         'not_equal')

        # current password is wrong.
        data = {
            'current_password': '4321',
            'new_password': 'l4o3l2i1',
            're_new_password': 'l4o3l2i1'
        }
        response = self.client.patch(reverse('user-change-my-password'),
                                     data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['current_password'][0].code,
                         'invalid')

        # new password format is weak.
        data = {
            'current_password': '1234',
            'new_password': 'admin123',
            're_new_password': 'admin123'
        }
        response = self.client.patch(reverse('user-change-my-password'),
                                     data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['new_password'][0].code,
                         'invalid')

        # everything is ok.
        data = {
            'current_password': '1234',
            'new_password': 'l4o3l2i1',
            're_new_password': 'l4o3l2i1'
        }
        response = self.client.patch(reverse('user-change-my-password'),
                                     data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class RetrievePerms(UserTestCase):

    def test_unauthenticated(self):
        path = reverse('user-me')

        response = self.client.get(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        path = reverse('user-me')

        self.client.force_login(self.user)
        response = self.client.get(path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UpdatePerms(UserTestCase):

    def test_unauthenticated(self):
        path = reverse('user-me')

        response = self.client.put(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        path = reverse('user-me')

        self.client.force_login(self.user)
        response = self.client.put(path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PartialUpdatePerms(UserTestCase):

    def test_unauthenticated(self):
        path = reverse('user-me')

        response = self.client.patch(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        path = reverse('user-me')

        self.client.force_login(self.user)
        response = self.client.patch(path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ChangePasswordPerms(UserTestCase):

    def test_unauthenticated(self):
        path = reverse('user-change-my-password')

        response = self.client.patch(path)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        path = reverse('user-change-my-password')

        self.client.force_login(self.user)
        response = self.client.patch(path)
        self.client.logout()
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)