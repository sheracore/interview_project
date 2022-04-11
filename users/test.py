from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from django.contrib.auth.models import Group
from core.models.system import System


User = get_user_model()


class UserTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        System.reset_settings()
        cls.super_admin = User.objects.create_superuser(
            username='super_admin', email='super@admin.com', password='1234',
        )

        cls.admin = User.objects.create_user(username='admin',
                                             email='admin@admin.com',
                                             is_staff=True,
                                             password='1234')

        cls.user = User.objects.create_user(username='user',
                                            email='user@user.com',
                                            password='1234')
        cls.group = Group.objects.create(name='Test')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for user in User.objects.all():
            user.user_permissions.all().delete()
            user.groups.all().delete()
