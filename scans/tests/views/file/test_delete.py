from django.core.files.base import ContentFile
from django.contrib.auth.models import Permission, Group
from rest_framework.reverse import reverse
from rest_framework.views import status

from users.test import UserTestCase
from scans.models.session import Session
from scans.models.file import File


class Operation(UserTestCase):

	def setUp(self):
		super().setUp()
		self.client.force_login(self.super_admin)
		session = Session.objects.create()
		self.file = File.objects.create(
			file=ContentFile(b"Some file content", name='test.pdf'),
			user=self.super_admin, session=session
		)
		self.path = f"{reverse('file-delete')}?session_id={self.file.session_id}"

	def tearDown(self):
		super().tearDown()
		self.client.logout()

	def test_ok(self):
		url = self.path

		with self.assertNumQueries(9):
			response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class Perms(UserTestCase):

	def setUp(self):
		super().setUp()
		session = Session.objects.create()
		self.file = File.objects.create(
			file=ContentFile(b"Some file content", name='test.pdf'),
			user=self.admin, session=session
		)
		self.path = f"{reverse('file-delete')}?session_id={self.file.session_id}"

	def test_unauthenticated(self):
		url = self.path

		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_unauthorized(self):
		url = self.path

		self.client.force_login(self.user)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_superuser(self):
		url = self.path

		self.client.force_login(self.super_admin)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_authorized(self):
		url = self.path

		self.client.force_login(self.admin)
		self.admin.user_permissions.add(
			Permission.objects.get(codename='delete_files')
		)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_group(self):
		url = self.path

		group = Group.objects.create(name='Files Deleter')
		group.permissions.set(
			[Permission.objects.get(codename='delete_files')]
		)
		self.user.groups.add(group)
		self.client.force_login(self.user)
		response = self.client.delete(url)
		self.client.logout()
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
