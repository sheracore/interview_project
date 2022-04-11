from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from users.models import User


class ModelTest(APITestCase):

    def test(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='1234',
            full_name='Admin'
        )

        self.user = User.objects.create_user(
            username='lol',
            email='lol@example.com',
            password='lolica123456',
            full_name='Lol'
        )
        self.user.clean()
        self.user.get_full_name()
        self.user.email_user('subject', 'message')

        try:
            self.user = User.objects.create_user(
                username='',
                email='lol@example.com',
                password='lolica123456',
                full_name='Lol'
            )

        except ValueError as e:
            self.assertEqual(str(e), 'The username not given.')

        try:
            self.user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='1234',
                full_name='Admin',
                is_staff=False
            )

        except ValueError as e:
            self.assertEqual(str(e), 'Superuser must have is_staff=True.')

        try:
            self.user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='1234',
                full_name='Admin',
                is_superuser=False
            )

        except ValueError as e:
            self.assertEqual(str(e), 'Superuser must have is_superuser=True.')
