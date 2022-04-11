# from django.contrib.auth.models import Group, Permission
# from rest_framework.views import status
# from django.urls import reverse
# from django.core.files.base import ContentFile
#
# from users.test import UserTestCase
# from scans.models import File, Scan
# from agents.models import Agent
#
#
# class Operation(UserTestCase):
#
#     def setUp(self):
#         super().setUp()
#         self.client.force_login(self.super_admin)
#         file = ContentFile(b"Some file content", name='test.pdf')
#         self.first_file = File.objects.create(
#             file=file, owner=self.super_admin, ext_match=False, size=1024,
#             scanned_serial=4, session_id='testprogress')
#         agent = Agent.objects.create(api_ip='192.168.100.158')
#         self.scan = Scan.objects.create(
#             agent=agent, file=self.first_file,
#             serial=4, infected_num=1, status_code=200
#         )
#         self.url = reverse('file-postscan') + '?session_id=testprogress'
#
#     def test_ok(self):
#         with self.assertNumQueries(8):
#             response = self.client.get(path=self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         scanned_file = Scan.objects.filter(file=self.first_file)
#         self.assertEqual(response.data['total'], File.objects.all().count())
#         self.assertEqual(response.data['scanned'], scanned_file.count())
#         self.assertEqual(response.data['infected'],
#                          scanned_file.filter(infected_num=1).count())
#
#
# class Perms(UserTestCase):
#
#     def setUp(self):
#         super().setUp()
#         file = ContentFile(b"Some file content", name='test.pdf')
#         self.first_file = File.objects.create(
#             file=file, owner=self.super_admin, ext_match=False, size=1024,
#             scanned_serial=4, session_id='testprogress')
#         agent = Agent.objects.create(api_ip='192.168.100.158')
#         self.scan = Scan.objects.create(
#             agent=agent, file=self.first_file,
#             serial=4, infected_num=1, status_code=200
#         )
#         self.url = reverse('file-postscan') + '?session_id=testprogress'
#
#     def test_unauthenticated(self):
#         # Unauthorized
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_unauthorized(self):
#         # User and has not the view_file perms
#         self.client.force_login(self.user)
#         response = self.client.get(path=self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_superuser(self):
#         # super admin
#         self.client.force_login(self.super_admin)
#         response = self.client.get(path=self.url)
#         self.client.logout()
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_authorized(self):
#         self.client.force_login(self.admin)
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_group(self):
#         group = Group.objects.create(name='File Post Scan')
#         self.user.groups.add(group)
#         self.client.force_login(self.user)
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
