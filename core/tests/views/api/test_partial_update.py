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
		self.data = {
			'title': 'api_for_test',
		}
		self.path = reverse('api-detail', kwargs={'pk': self.api.pk})

	def tearDown(self):
		super().tearDown()
		self.client.logout()

	def test_ok(self):
		url = self.path
		with self.assertNumQueries(5):
			response = self.client.patch(
				path=url,
				data=self.data
			)
		self.assertEqual(response.status_code, status.HTTP_200_OK)


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
		self.data = {
			'title': 'api_for_test',
		}
		self.path = reverse('api-detail', kwargs={'pk': self.api.pk})

	def test_unauthenticated(self):
		url = self.path
		response = self.client.patch(url)
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_unauthorized(self):
		"""
		return 404
		Because we want the user not to notice that the file exists but the user does not have permission to access
		"""
		url = self.path
		self.client.force_login(self.user)
		response = self.client.patch(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_superuser(self):
		url = self.path
		self.client.force_login(self.super_admin)
		response = self.client.patch(
			path=url,
			data=self.data
		)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_adminuser(self):
		url = self.path
		self.client.force_login(self.admin)
		response = self.client.patch(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_authorized(self):
		url = self.path
		self.admin.user_permissions.add(
			Permission.objects.get(codename='change_api')
		)
		self.client.force_login(self.admin)
		response = self.client.patch(
			path=url,
			data=self.data
		)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_group(self):
		url = self.path
		group = Group.objects.create(
			name='Api Updaters'
		)
		group.permissions.set(
			[Permission.objects.get(codename='change_api')]
		)
		self.admin.groups.add(group)
		self.client.force_login(self.admin)
		response = self.client.patch(
			path=url,
			data=self.data
		)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
