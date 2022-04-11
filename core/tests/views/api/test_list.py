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
		self.apis = API.objects.all()
		self.path = reverse('api-list')

	def tearDown(self):
		super().tearDown()
		self.client.logout()

	def test_ok(self):
		url = self.path
		with self.assertNumQueries(5):
			response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['count'], self.apis.count())

class Perm(UserTestCase):

	def setUp(self):
		super().setUp()
		self.api = API.objects.create(
			title='test_api_for_admin',
			allowed_hosts=[
				"1.1.1.1",
				"2.2.2.2"
			],
			key='foobarlablablab',
			owner=self.admin
		)
		self.user_api = API.objects.create(
			title='test_api_for_admin',
			allowed_hosts=[
				"1.1.1.1",
				"2.2.2.2"
			],
			key='foobarlablablzoo',
			owner=self.user
		)
		self.apis = API.objects.all()
		self.path = reverse('api-list')

	def test_unauthenticated(self):
		url = self.path
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_unauthorized(self):
		url = self.path
		self.client.force_login(self.user)
		response = self.client.get(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertLessEqual(response.data['count'], self.apis.count())
		self.assertEqual(response.data['count'], self.apis.filter(owner=self.user).count())

	def test_superuser(self):
		url = self.path
		self.client.force_login(self.super_admin)
		response = self.client.get(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['count'], self.apis.count())

	def test_authorized(self):
		url = self.path
		self.user.user_permissions.add(
			Permission.objects.get(codename='view_api')
		)
		self.user.is_staff = True
		self.user.save()
		self.client.force_login(self.user)
		response = self.client.get(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['count'], self.apis.count())

	def test_group(self):
		url = self.path
		group = Group.objects.create(
			name='API List Viewers'
		)
		group.permissions.set(
			[Permission.objects.get(codename='view_api')]
		)
		self.user.groups.add(group)
		self.user.is_staff = True
		self.user.save()
		self.client.force_login(self.user)
		response = self.client.get(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['count'], self.apis.count())
