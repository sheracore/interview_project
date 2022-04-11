from rest_framework.views import status
from django.urls import reverse

from django.contrib.auth.models import Permission, Group

from users.test import UserTestCase

from core.models.api import API


class Operation(UserTestCase):

	def setUp(self):
		super().setUp()
		self.client.force_login(self.super_admin)
		self.api = API.objects.create(
			title='api_for_test',
			allowed_hosts=[
				"1.1.1.1",
				"2.2.2.2"
			],
			key='foobarlablablab',
			owner=self.super_admin
		)
		self.path = reverse('api-detail', kwargs={'pk': self.api.pk})

	def tearDown(self):
		super().tearDown()
		self.client.logout()

	def test_ok(self):
		url = self.path

		with self.assertNumQueries(5):
			response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertFalse(API.objects.filter(pk=self.api.pk).exists())


class Perm(UserTestCase):

	def setUp(self):
		super().setUp()
		self.api = API.objects.create(
			title='just_for_test',
			allowed_hosts=[
				'1.1.1.1',
				'2.2.2.2'
			],
			key='foobarforapikey12',
			owner=self.super_admin
		)
		self.path = reverse('api-detail', kwargs={'pk': self.api.pk})

	def test_unauthenticated(self):
		url = self.path
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_unauthorized(self):
		"""
		return 404
		Because we want the user not to notice that the file exists but the user does not have permission to access
		"""
		url = self.path
		self.client.force_login(self.user)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_superuser(self):
		url = self.path
		self.client.force_login(self.super_admin)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_adminuser(self):
		url = self.path
		self.client.force_login(self.admin)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_authorized_admin(self):
		url = self.path
		self.admin.user_permissions.add(
			Permission.objects.get(codename='delete_api')
		)
		self.client.force_login(self.admin)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_authorized_user(self):
		url = self.path
		self.user.user_permissions.add(
			Permission.objects.get(codename='delete_api')
		)
		self.client.force_login(self.user)
		response = self.client.delete(url)
		self.client.logout()
		self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_group_with_admin(self):
		url = self.path
		group = Group.objects.create(
			name='Api Destroyers'
		)
		group.permissions.set(
			[Permission.objects.get(codename='delete_api')]
		)
		self.admin.groups.add(group)
		self.client.force_login(self.admin)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_group_with_user(self):
		url = self.path
		group = Group.objects.create(
			name='Api Destroyers'
		)
		group.permissions.set(
			[Permission.objects.get(codename='delete_api')]
		)
		self.user.groups.add(group)
		self.client.force_login(self.user)
		response = self.client.delete(url)
		self.client.logout()
		self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
