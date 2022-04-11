# from django.test.testcases import TestCase
#
# from agents.models import Agent
# from agents.tasks import set_status
#
#
# class SetStatusTask(TestCase):
#
#     @classmethod
#     def setUpTestData(cls):
#         cls.agent = Agent.objects.create(
#             av_name='eset',
#             api_ip='192.168.182.0',
#             title='eset_av',
#             active=True
#         )
#
#     def test_ok(self):
#         set_status(self.agent.pk)
#         self.agent.refresh_from_db()
#         self.assertEqual(self.agent.status['status_code'], 499)
