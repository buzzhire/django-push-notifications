from django.test import TestCase
from push_notifications.gcm import send_message, send_bulk_message
from tests.test_models import GCM_JSON_RESPONSE, GCM_JSON_MULTIPLE_RESPONSE
from ._mock import mock


class GCMPushPayloadTest(TestCase):

	def test_fcm_push_payload(self):
		with mock.patch("push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message("abc", {"message": "Hello world"}, cloud_type="FCM")
			p.assert_called_once_with(
				b'{"notification":{"body":"Hello world"},"registration_ids":["abc"]}',
				"application/json", None)

	def test_fcm_push_payload_params(self):
		with mock.patch("push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message(
				"abc",
				{"message": "Hello world", "title": "Push notification", "other": "misc"},
				delay_while_idle=True, time_to_live=3600, foo='bar',
				cloud_type="FCM",
			)
			p.assert_called_once_with(
				b'{"data":{"other":"misc"},"delay_while_idle":true,'
				b'"notification":{"body":"Hello world","title":"Push notification"},'
				b'"registration_ids":["abc"],"time_to_live":3600}',
				"application/json", None)

	def test_fcm_push_payload_many(self):
		with mock.patch("push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE) as p:
			send_bulk_message(["abc", "123"], {"message": "Hello world"}, cloud_type="FCM")
			p.assert_called_once_with(
				b'{"notification":{"body":"Hello world"},"registration_ids":["abc","123"]}',
				"application/json", None)

	def test_fcm_push_payload_with_app_id(self):
		with mock.patch("push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message("abc", {"message": "Hello world"}, "qwerty", cloud_type="FCM")
			p.assert_called_once_with(
				b'{"notification":{"body":"Hello world"},"registration_ids":["abc"]}',
				"application/json", "qwerty")
		with mock.patch("push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message("abc", {"message": "Hello world"}, application_id="qwerty", cloud_type="FCM")
			p.assert_called_once_with(
				b'{"notification":{"body":"Hello world"},"registration_ids":["abc"]}',
				"application/json", "qwerty")

	def test_gcm_push_payload(self):
		with mock.patch("push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message("abc", {"message": "Hello world"}, cloud_type="GCM")
			p.assert_called_once_with(
				b'{"data":{"message":"Hello world"},"registration_ids":["abc"]}',
				"application/json", None)

	def test_gcm_push_payload_params(self):
		with mock.patch("push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message(
				"abc", {"message": "Hello world"}, delay_while_idle=True, time_to_live=3600, foo='bar',
				cloud_type="GCM"
			)
			p.assert_called_once_with(
				b'{"data":{"message":"Hello world"},"delay_while_idle":true,'
				b'"registration_ids":["abc"],"time_to_live":3600}',
				"application/json", None)

	def test_gcm_push_payload_many(self):
		with mock.patch("push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE) as p:
			send_bulk_message(["abc", "123"], {"message": "Hello world"}, cloud_type="GCM")
			p.assert_called_once_with(
				b'{"data":{"message":"Hello world"},"registration_ids":["abc","123"]}',
				"application/json",
				None)

	def test_gcm_push_payload_with_app_id(self):
		with mock.patch("push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message("abc", {"message": "Hello world"}, "qwerty", cloud_type="GCM")
			p.assert_called_once_with(
				b'{"data":{"message":"Hello world"},"registration_ids":["abc"]}',
				"application/json", "qwerty")
		with mock.patch("push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE) as p:
			send_message("abc", {"message": "Hello world"}, application_id="qwerty", cloud_type="GCM")
			p.assert_called_once_with(
				b'{"data":{"message":"Hello world"},"registration_ids":["abc"]}',
				"application/json", "qwerty")
