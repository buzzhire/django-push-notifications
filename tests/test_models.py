import json

from django.test import TestCase
from django.utils import timezone
from push_notifications.gcm import GCMError, send_message
from push_notifications.models import GCMDevice, APNSDevice
from ._mock import mock
import os

# Mock responses

GCM_JSON_RESPONSE = '{"cast_id":108,"success":1,"failure":0,"canonical_ids":0,"results":[{"message_id":"1:08"}]}'
GCM_JSON_RESPONSE_ERROR_NOTREGISTERED = (
	'{"success":1, "failure": 1, "canonical_ids": 0, "cast_id": 6358665107659088804, "results":'
	' [{"error": "NotRegistered"}, {"message_id": "0:1433830664381654%3449593ff9fd7ecd"}]}'
)
GCM_JSON_RESPONSE_ERROR_INVALIDREGISTRATION = (
	'{"success":1, "failure": 1, "canonical_ids": 0, "cast_id": 6358665107659088804, "results":'
	' [{"error": "InvalidRegistration"}, {"message_id": "0:1433830664381654%3449593ff9fd7ecd"}]}'
)
GCM_JSON_RESPONSE_ERROR_MISMATCHSENDERID = (
	'{"success":0, "failure": 1, "canonical_ids": 0, "results":'
	' [{"error": "MismatchSenderId"}]}'
)
GCM_JSON_CANONICAL_ID_RESPONSE = (
	'{"failure":0,"canonical_ids":1,"success":1,"cast_id":7173139966327257000,"results":'
	'[{"registration_id":"NEW_REGISTRATION_ID","message_id":"0:1440068396670935%6868637df9fd7ecd"}]}'
)
GCM_JSON_CANONICAL_ID_SAME_DEVICE_RESPONSE = (
	'{"failure":0,"canonical_ids":1,"success":1,"cast_id":7173139966327257000,"results":'
	'[{"registration_id":"bar","message_id":"0:1440068396670935%6868637df9fd7ecd"}]}'
)

GCM_JSON_MULTIPLE_RESPONSE = (
	'{"multicast_id":108,"success":2,"failure":0,"canonical_ids":0,"results":'
	'[{"message_id":"1:08"}, {"message_id": "1:09"}]}'
)
GCM_JSON_MULTIPLE_RESPONSE_ERROR = (
	'{"success":1, "failure": 2, "canonical_ids": 0, "cast_id": 6358665107659088804, "results":'
	' [{"error": "NotRegistered"}, {"message_id": "0:1433830664381654%3449593ff9fd7ecd"}, '
	'{"error": "InvalidRegistration"}]}'
)
GCM_JSON_MULTIPLE_RESPONSE_ERROR_B = (
	'{"success":1, "failure": 2, "canonical_ids": 0, "cast_id": 6358665107659088804, '
	'"results": [{"error": "MismatchSenderId"}, {"message_id": '
	'"0:1433830664381654%3449593ff9fd7ecd"}, {"error": "InvalidRegistration"}]}'
)
GCM_JSON_MULTIPLE_CANONICAL_ID_RESPONSE = (
	'{"failure":0,"canonical_ids":1,"success":2,"multicast_id":7173139966327257000,"results":'
	'[{"registration_id":"NEW_REGISTRATION_ID","message_id":"0:1440068396670935%6868637df9fd7ecd"},'
	'{"message_id":"0:1440068396670937%6868637df9fd7ecd"}]}'
)
GCM_JSON_MULTIPLE_CANONICAL_ID_SAME_DEVICE_RESPONSE = (
	'{"failure":0,"canonical_ids":1,"success":2,"multicast_id":7173139966327257000,'
	'"results":[{"registration_id":"bar","message_id":"0:1440068396670935%6868637df9fd7ecd"}'
	',{"message_id":"0:1440068396670937%6868637df9fd7ecd"}]}'
)


class GCMModelTestCase(TestCase):
	def _create_devices(self, devices):
		for device in devices:
			GCMDevice.objects.create(registration_id=device, cloud_message_type="GCM")

	def _create_fcm_devices(self, devices):
		for device in devices:
			GCMDevice.objects.create(registration_id=device, cloud_message_type="FCM")

	def test_can_save_gcm_device(self):
		device = GCMDevice.objects.create(registration_id="a valid registration id", cloud_message_type="GCM")
		assert device.id is not None
		assert device.date_created is not None
		assert device.date_created.date() == timezone.now().date()

	def test_can_create_save_device(self):
		device = APNSDevice.objects.create(registration_id="a valid registration id")
		assert device.id is not None
		assert device.date_created is not None
		assert device.date_created.date() == timezone.now().date()

	def test_gcm_send_message(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="GCM")
		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"data": {"message": "Hello world"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_gcm_send_message_with_app_id(self):
		device = GCMDevice.objects.create(
			registration_id="abc",
			application_id="qwerty",
			cloud_message_type="GCM"
		)
		with mock.patch("push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE) as p:
			device.send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"data": {"message": "Hello world"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", "qwerty")

	def test_gcm_send_message_extra(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="GCM")
		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world", extra={"foo": "bar"}, collapse_key="test_key")
			p.assert_called_once_with(
				json.dumps({
					"collapse_key": "test_key",
					"data": {"message": "Hello world", "foo": "bar"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_gcm_send_message_collapse_key(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="GCM")
		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world", collapse_key="test_key")
			p.assert_called_once_with(
				json.dumps({
					"data": {"message": "Hello world"},
					"registration_ids": ["abc"],
					"collapse_key": "test_key"
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_gcm_send_message_to_multiple_devices(self):
		self._create_devices(["abc", "abc1"])

		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE
		) as p:
			GCMDevice.objects.all().send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"data": {"message": "Hello world"},
					"registration_ids": ["abc", "abc1"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_gcm_send_message_active_devices(self):
		GCMDevice.objects.create(registration_id="abc", active=True, cloud_message_type="GCM")
		GCMDevice.objects.create(registration_id="xyz", active=False, cloud_message_type="GCM")

		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE
		) as p:
			GCMDevice.objects.all().send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"data": {"message": "Hello world"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_gcm_send_message_collapse_to_multiple_devices(self):
		self._create_devices(["abc", "abc1"])

		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE
		) as p:
				GCMDevice.objects.all().send_message("Hello world", collapse_key="test_key")
				p.assert_called_once_with(
					json.dumps({
						"collapse_key": "test_key",
						"data": {"message": "Hello world"},
						"registration_ids": ["abc", "abc1"]
					}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_gcm_send_message_to_single_device_with_error(self):
		# these errors are device specific, device.active will be set false
		devices = ["abc", "abc1"]
		self._create_devices(devices)

		errors = [GCM_JSON_RESPONSE_ERROR_NOTREGISTERED, GCM_JSON_RESPONSE_ERROR_INVALIDREGISTRATION]
		for index, error in enumerate(errors):
			with mock.patch(
				"push_notifications.gcm._gcm_send", return_value=error):
				device = GCMDevice.objects.get(registration_id=devices[index])
				device.send_message("Hello World!")
				assert GCMDevice.objects.get(registration_id=devices[index]).active is False

	def test_gcm_send_message_to_single_device_with_error_mismatch(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="GCM")

		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_RESPONSE_ERROR_MISMATCHSENDERID
		):
			# these errors are not device specific, GCMError should be thrown
			with self.assertRaises(GCMError):
				device.send_message("Hello World!")
			assert GCMDevice.objects.get(registration_id="abc").active is True

	def test_gcm_send_message_to_multiple_devices_with_error(self):
		self._create_devices(["abc", "abc1", "abc2"])
		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE_ERROR
		):
			devices = GCMDevice.objects.all()
			devices.send_message("Hello World")
			assert not GCMDevice.objects.get(registration_id="abc").active
			assert GCMDevice.objects.get(registration_id="abc1").active
			assert not GCMDevice.objects.get(registration_id="abc2").active

	def test_gcm_send_message_to_multiple_devices_with_error_b(self):
		self._create_devices(["abc", "abc1", "abc2"])

		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE_ERROR_B
		):
			devices = GCMDevice.objects.all()
			with self.assertRaises(GCMError):
				devices.send_message("Hello World")
			assert GCMDevice.objects.get(registration_id="abc").active is True
			assert GCMDevice.objects.get(registration_id="abc1").active is True
			assert GCMDevice.objects.get(registration_id="abc2").active is False

	def test_gcm_send_message_to_multiple_devices_with_canonical_id(self):
		self._create_devices(["foo", "bar"])
		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_MULTIPLE_CANONICAL_ID_RESPONSE
		):
			GCMDevice.objects.all().send_message("Hello World")
			assert not GCMDevice.objects.filter(registration_id="foo").exists()
			assert GCMDevice.objects.filter(registration_id="bar").exists()
			assert GCMDevice.objects.filter(registration_id="NEW_REGISTRATION_ID").exists() is True

	def test_gcm_send_message_to_single_user_with_canonical_id(self):
		old_registration_id = "foo"
		self._create_devices([old_registration_id])

		with mock.patch(
			"push_notifications.gcm._gcm_send", return_value=GCM_JSON_CANONICAL_ID_RESPONSE
		):
			GCMDevice.objects.get(registration_id=old_registration_id).send_message("Hello World")
			assert not GCMDevice.objects.filter(registration_id=old_registration_id).exists()
			assert GCMDevice.objects.filter(registration_id="NEW_REGISTRATION_ID").exists()

	def test_gcm_send_message_to_same_devices_with_canonical_id(self):
		first_device = GCMDevice.objects.create(registration_id="foo", active=True, cloud_message_type="GCM")
		second_device = GCMDevice.objects.create(registration_id="bar", active=False, cloud_message_type="GCM")

		with mock.patch(
			"push_notifications.gcm._gcm_send",
			return_value=GCM_JSON_CANONICAL_ID_SAME_DEVICE_RESPONSE
		):
			GCMDevice.objects.all().send_message("Hello World")

		assert first_device.active is True
		assert second_device.active is False

	def test_gcm_send_message_with_no_reg_ids(self):
		self._create_devices(["abc", "abc1"])

		with mock.patch("push_notifications.gcm._cm_send_request", return_value="") as p:
			GCMDevice.objects.filter(registration_id="xyz").send_message("Hello World")
			p.assert_not_called()

		with mock.patch("push_notifications.gcm._cm_send_request", return_value="") as p:
			reg_ids = [obj.registration_id for obj in GCMDevice.objects.all()]
			send_message(reg_ids, {"message": "Hello World"}, cloud_type="GCM")
			p.assert_called_once_with(
				[u"abc", u"abc1"], {"message": "Hello World"}, None, cloud_type="GCM"
			)

	def test_fcm_send_message(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="FCM")
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"notification": {"body": "Hello world"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_with_app_id(self):
		device = GCMDevice.objects.create(
			registration_id="abc",
			application_id="qwerty",
			cloud_message_type="FCM"
		)
		with mock.patch("push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE) as p:
			device.send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"notification": {"body": "Hello world"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", "qwerty")

	def test_fcm_send_message_extra_data(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="FCM")
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world", extra={"foo": "bar"})
			p.assert_called_once_with(
				json.dumps({
					"data": {"foo": "bar"},
					"notification": {"body": "Hello world"},
					"registration_ids": ["abc"],
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_extra_options(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="FCM")
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world", collapse_key="test_key", foo="bar")
			p.assert_called_once_with(
				json.dumps({
					"collapse_key": "test_key",
					"notification": {"body": "Hello world"},
					"registration_ids": ["abc"],
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_extra_notification(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="FCM")
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message("Hello world", extra={"icon": "test_icon"}, title="test")
			p.assert_called_once_with(
				json.dumps({
					"notification": {"body": "Hello world", "title": "test", "icon": "test_icon"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_extra_options_and_notification_and_data(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="FCM")
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE
		) as p:
			device.send_message(
				"Hello world",
				extra={"foo": "bar", "icon": "test_icon"},
				title="test",
				collapse_key="test_key"
			)
			p.assert_called_once_with(
				json.dumps({
					"notification": {"body": "Hello world", "title": "test", "icon": "test_icon"},
					"data": {"foo": "bar"},
					"registration_ids": ["abc"],
					"collapse_key": "test_key"
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_to_multiple_devices(self):
		self._create_fcm_devices(["abc", "abc1"])

		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE
		) as p:
			GCMDevice.objects.all().send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"notification": {"body": "Hello world"},
					"registration_ids": ["abc", "abc1"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_active_devices(self):
		GCMDevice.objects.create(registration_id="abc", active=True, cloud_message_type="FCM")
		GCMDevice.objects.create(registration_id="xyz", active=False, cloud_message_type="FCM")

		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE
		) as p:
			GCMDevice.objects.all().send_message("Hello world")
			p.assert_called_once_with(
				json.dumps({
					"notification": {"body": "Hello world"},
					"registration_ids": ["abc"]
				}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_collapse_to_multiple_devices(self):
		self._create_fcm_devices(["abc", "abc1"])

		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE
		) as p:
				GCMDevice.objects.all().send_message("Hello world", collapse_key="test_key")
				p.assert_called_once_with(
					json.dumps({
						"collapse_key": "test_key",
						"notification": {"body": "Hello world"},
						"registration_ids": ["abc", "abc1"]
					}, separators=(",", ":"), sort_keys=True).encode("utf-8"), "application/json", None)

	def test_fcm_send_message_to_single_device_with_error(self):
		# these errors are device specific, device.active will be set false
		devices = ["abc", "abc1"]
		self._create_fcm_devices(devices)

		errors = [GCM_JSON_RESPONSE_ERROR_NOTREGISTERED, GCM_JSON_RESPONSE_ERROR_INVALIDREGISTRATION]
		for index, error in enumerate(errors):
			with mock.patch(
				"push_notifications.gcm._fcm_send", return_value=error):
				device = GCMDevice.objects.get(registration_id=devices[index])
				device.send_message("Hello World!")
				assert GCMDevice.objects.get(registration_id=devices[index]).active is False

	def test_fcm_send_message_to_single_device_with_error_mismatch(self):
		device = GCMDevice.objects.create(registration_id="abc", cloud_message_type="FCM")

		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_RESPONSE_ERROR_MISMATCHSENDERID
		):
			# these errors are not device specific, GCMError should be thrown
			with self.assertRaises(GCMError):
				device.send_message("Hello World!")
			assert GCMDevice.objects.get(registration_id="abc").active is True

	def test_fcm_send_message_to_multiple_devices_with_error(self):
		self._create_fcm_devices(["abc", "abc1", "abc2"])
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE_ERROR
		):
			devices = GCMDevice.objects.all()
			devices.send_message("Hello World")
			assert not GCMDevice.objects.get(registration_id="abc").active
			assert GCMDevice.objects.get(registration_id="abc1").active
			assert not GCMDevice.objects.get(registration_id="abc2").active

	def test_fcm_send_message_to_multiple_devices_with_error_b(self):
		self._create_fcm_devices(["abc", "abc1", "abc2"])

		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_RESPONSE_ERROR_B
		):
			devices = GCMDevice.objects.all()
			with self.assertRaises(GCMError):
				devices.send_message("Hello World")
			assert GCMDevice.objects.get(registration_id="abc").active is True
			assert GCMDevice.objects.get(registration_id="abc1").active is True
			assert GCMDevice.objects.get(registration_id="abc2").active is False

	def test_fcm_send_message_to_multiple_devices_with_canonical_id(self):
		self._create_fcm_devices(["foo", "bar"])
		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_MULTIPLE_CANONICAL_ID_RESPONSE
		):
			GCMDevice.objects.all().send_message("Hello World")
			assert not GCMDevice.objects.filter(registration_id="foo").exists()
			assert GCMDevice.objects.filter(registration_id="bar").exists()
			assert GCMDevice.objects.filter(registration_id="NEW_REGISTRATION_ID").exists() is True

	def test_fcm_send_message_to_single_user_with_canonical_id(self):
		old_registration_id = "foo"
		self._create_fcm_devices([old_registration_id])

		with mock.patch(
			"push_notifications.gcm._fcm_send", return_value=GCM_JSON_CANONICAL_ID_RESPONSE
		):
			GCMDevice.objects.get(registration_id=old_registration_id).send_message("Hello World")
			assert not GCMDevice.objects.filter(registration_id=old_registration_id).exists()
			assert GCMDevice.objects.filter(registration_id="NEW_REGISTRATION_ID").exists()

	def test_fcm_send_message_to_same_devices_with_canonical_id(self):
		first_device = GCMDevice.objects.create(registration_id="foo", active=True, cloud_message_type="FCM")
		second_device = GCMDevice.objects.create(registration_id="bar", active=False, cloud_message_type="FCM")

		with mock.patch(
			"push_notifications.gcm._fcm_send",
			return_value=GCM_JSON_CANONICAL_ID_SAME_DEVICE_RESPONSE
		):
			GCMDevice.objects.all().send_message("Hello World")

		assert first_device.active is True
		assert second_device.active is False

	def test_fcm_send_message_with_no_reg_ids(self):
		self._create_fcm_devices(["abc", "abc1"])

		with mock.patch("push_notifications.gcm._cm_send_request", return_value="") as p:
			GCMDevice.objects.filter(registration_id="xyz").send_message("Hello World")
			p.assert_not_called()

		with mock.patch("push_notifications.gcm._cm_send_request", return_value="") as p:
			reg_ids = [obj.registration_id for obj in GCMDevice.objects.all()]
			send_message(reg_ids, {"message": "Hello World"}, cloud_type="GCM")
			p.assert_called_once_with(
				[u"abc", u"abc1"], {"message": "Hello World"}, None, cloud_type="GCM"
			)

	def test_apns_send_message(self):
		device = APNSDevice.objects.create(registration_id="abc")
		socket = mock.MagicMock()

		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			device.send_message("Hello world", socket=socket, expiration=1)
			p.assert_called_once_with("abc", b'{"aps":{"alert":"Hello world"}}', 0, 1, 10)

	def test_apns_send_message_extra(self):
		device = APNSDevice.objects.create(registration_id="abc")
		socket = mock.MagicMock()

		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			device.send_message(
				"Hello world", extra={"foo": "bar"}, socket=socket,
				identifier=1, expiration=2, priority=5
			)
			p.assert_called_once_with("abc", b'{"aps":{"alert":"Hello world"},"foo":"bar"}', 1, 2, 5)

	def test_can_save_wsn_device(self):
		device = GCMDevice.objects.create(registration_id="a valid registration id")
		self.assertIsNotNone(device.pk)
		self.assertIsNotNone(device.date_created)
		self.assertEqual(device.date_created.date(), timezone.now().date())

	def test_apns_send_message_cert(self):
		device = APNSDevice.objects.create(registration_id="abc")
		socket = mock.MagicMock()

		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			with mock.patch("push_notifications.apns._apns_create_socket") as cs:
				cs.return_value = socket
				device.send_message(
					"Hello world", extra={"foo": "bar"},
					identifier=1, expiration=2, priority=5,
					certfile="12345"
				)
				p.assert_called_once_with("abc", b'{"aps":{"alert":"Hello world"},"foo":"bar"}', 1, 2, 5)
				cs.assert_called_once_with(('gateway.push.apple.com', 2195), application_id=None, certfile='12345')


class APNSModelWithSettingsTestCase(TestCase):
	def test_apns_send_message_with_app_id(self):
		from django.conf import settings
		path = os.path.join(os.path.dirname(__file__), "test_data", "good_revoked.pem")
		device = APNSDevice.objects.create(
			registration_id="abc",
			application_id="asdfg"
		)
		device2 = APNSDevice.objects.create(
			registration_id="def",
		)
		settings.PUSH_NOTIFICATIONS_SETTINGS['APNS_CERTIFICATE'] = path
		settings.PUSH_NOTIFICATIONS_SETTINGS['APNS_CERTIFICATES'] = {
			'asdfg': path
		}
		settings.PUSH_NOTIFICATIONS_SETTINGS['APNS_HOSTS'] = {
			'asdfg': "111.222.333"
		}
		settings.PUSH_NOTIFICATIONS_SETTINGS['APNS_PORTS'] = {
			'asdfg': 334
		}
		import ssl
		socket = mock.MagicMock()
		with mock.patch("ssl.wrap_socket", return_value=socket) as s:
			with mock.patch("push_notifications.apns._apns_pack_frame") as p:
				device.send_message("Hello world", expiration=1)
				p.assert_called_once_with("abc", b'{"aps":{"alert":"Hello world"}}', 0, 1, 10)
				s.assert_called_once_with(*s.call_args[0], ca_certs=None, certfile=path, ssl_version=ssl.PROTOCOL_TLSv1)
				socket.connect.assert_called_with(("111.222.333", 334))
		socket = mock.MagicMock()
		with mock.patch("ssl.wrap_socket", return_value=socket) as s:
			with mock.patch("push_notifications.apns._apns_pack_frame") as p:
				device2.send_message("Hello world", expiration=1)
				p.assert_called_once_with("def", b'{"aps":{"alert":"Hello world"}}', 0, 1, 10)
				s.assert_called_once_with(*s.call_args[0], ca_certs=None, certfile=path, ssl_version=ssl.PROTOCOL_TLSv1)
				socket.connect.assert_called_with(("gateway.push.apple.com", 2195))

	def test_apns_send_multi_message_with_app_id(self):
		from django.conf import settings
		path = os.path.join(os.path.dirname(__file__), "test_data", "good_revoked.pem")
		device = APNSDevice.objects.create(
			registration_id="abc",
			application_id="asdfg"
		)
		device = APNSDevice.objects.create(
			registration_id="def",
			application_id="asdfg"
		)
		settings.PUSH_NOTIFICATIONS_SETTINGS['APNS_CERTIFICATES'] = {
			'asdfg': path
		}
		import ssl
		socket = mock.MagicMock()
		with mock.patch("ssl.wrap_socket", return_value=socket) as s:
			with mock.patch("push_notifications.apns._apns_pack_frame") as p:
				APNSDevice.objects.all().send_message("Hello world", expiration=1)
				device.send_message("Hello world", expiration=1)
				p.assert_any_call("abc", b'{"aps":{"alert":"Hello world"}}', 0, 1, 10)
				p.assert_any_call("def", b'{"aps":{"alert":"Hello world"}}', 0, 1, 10)
				s.assert_any_call(*s.call_args_list[0][0], ca_certs=None, certfile=path, ssl_version=ssl.PROTOCOL_TLSv1)


class GCMModelWithSettingsTestCase(TestCase):
	def test_fcm_send_message_with_app_id(self):
		from django.conf import settings
		device = GCMDevice.objects.create(
			registration_id="abc",
			application_id="asdfg",
			cloud_message_type="FCM"
		)
		settings.PUSH_NOTIFICATIONS_SETTINGS['FCM_API_KEYS'] = {
			'asdfg': 'uiopkey'
		}
		try:
			from StringIO import StringIO
		except ImportError:
			from io import StringIO
		with mock.patch("push_notifications.gcm.urlopen", return_value=StringIO(GCM_JSON_RESPONSE)) as u:
			device.send_message("Hello world")
			request = u.call_args[0][0]
			assert request.headers['Authorization'] == 'key=uiopkey'

	def test_fcm_send_multi_message_with_app_id(self):
		from django.conf import settings
		device = GCMDevice.objects.create(
			registration_id="abc",
			application_id="asdfg",
			cloud_message_type="FCM"
		)
		device = GCMDevice.objects.create(
			registration_id="def",
			application_id="asdfg",
			cloud_message_type="FCM"
		)
		settings.PUSH_NOTIFICATIONS_SETTINGS['FCM_API_KEYS'] = {
			'asdfg': 'uiopkey'
		}
		try:
			from StringIO import StringIO
		except ImportError:
			from io import StringIO
		import json
		with mock.patch("push_notifications.gcm.urlopen", return_value=StringIO(GCM_JSON_RESPONSE)) as u:
			GCMDevice.objects.all().send_message("Hello world")
			assert u.call_count == 1
			request = u.call_args[0][0]
			assert request.headers['Authorization'] == 'key=uiopkey'

	def test_gcm_send_multi_message_with_different_app_id(self):
		from django.conf import settings
		device = GCMDevice.objects.create(
			registration_id="abc",
			application_id="asdfg",
			cloud_message_type="FCM"
		)
		device = GCMDevice.objects.create(
			registration_id="def",
			application_id="uiop",
			cloud_message_type="FCM"
		)
		settings.PUSH_NOTIFICATIONS_SETTINGS['FCM_API_KEYS'] = {
			'asdfg': 'asdfgkey',
			'uiop': 'uiopkey'
		}
		try:
			from StringIO import StringIO
		except ImportError:
			from io import StringIO
		import json
		requests = []

		def c():
			def f(r, **kw):
				requests.append(r)
				return StringIO(GCM_JSON_RESPONSE)
			return f
		with mock.patch("push_notifications.gcm.urlopen", new_callable=c) as u:
			GCMDevice.objects.all().send_message("Hello world")
			keys = set(r.headers['Authorization'] for r in requests)
			assert len(keys) == 2
			assert 'key=asdfgkey' in keys
			assert 'key=uiopkey' in keys
