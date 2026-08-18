import json

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.urls import reverse

from model_bakery import baker
from pyfcm.errors import InvalidDataError
from pyfcm.fcm import FCMNotification
import pytest
import responses
from rest_framework.test import APIClient

from fcm_devices import service
from fcm_devices.api.drf.serializers import DeviceSerializer
from fcm_devices.fcm import FCMBackend, is_apns_unregistered_error
from fcm_devices.models import Device


@pytest.fixture()
def api_client():
    return APIClient()


# tests for service logic

success_response = {
    "multicast_ids": [],
    "success": 1,
    "failure": 0,
    "canonical_ids": 0,
    "results": [],
    "topic_message_id": None,
}


unrecoverable_error_response = {
    "multicast_ids": [],
    "success": 0,
    "failure": 1,
    "canonical_ids": 0,
    "results": [{"error": "InvalidRegistration"}],
    "topic_message_id": None,
}


configuration_error_response = {
    "multicast_ids": [],
    "success": 0,
    "failure": 1,
    "canonical_ids": 0,
    "results": [{"error": "MismatchSenderId"}],
    "topic_message_id": None,
}


@pytest.mark.django_db
def test_update_or_create_device_create(mocker):
    user = baker.make("auth.User")
    assert Device.objects.count() == 0
    device_created_signal = mocker.patch(
        "fcm_devices.service.signals.device_created.send"
    )
    device_updated_signal = mocker.patch(
        "fcm_devices.service.signals.device_updated.send"
    )
    device, created = service.update_or_create_device(
        user=user,
        token="iamfcmroar",
        active=True,
        _type=Device.types.android,
        name="Pixel 2",
    )
    assert Device.objects.count() == 1
    assert created
    assert device_created_signal.called_with_args(sender=Device, device=device)
    assert not device_updated_signal.called


@pytest.mark.django_db
def test_update_or_create_device_update(mocker):
    user = baker.make("auth.User")
    device = Device.objects.create(
        user=user,
        token="iamfcmroar",
        active=True,
        type=Device.types.android,
        name="Pixel 2",
    )
    initial_updated_at = device.updated_at
    assert Device.objects.count() == 1
    device_created_signal = mocker.patch(
        "fcm_devices.service.signals.device_created.send"
    )
    device_updated_signal = mocker.patch(
        "fcm_devices.service.signals.device_updated.send"
    )
    device, created = service.update_or_create_device(
        user=user,
        token="iamfcmroar",
        active=False,
        _type=Device.types.android,
        name="Pixel 2",
    )
    assert Device.objects.count() == 1
    assert not device.active
    assert not created
    assert device.updated_at > initial_updated_at
    assert device_updated_signal.called_with_args(sender=Device, device=device)
    assert not device_created_signal.called


@pytest.mark.django_db
def test_device_model_str(mocker):
    user = baker.make("auth.User", first_name="Ringo")
    device = Device.objects.create(
        user=user,
        token="iamfcmroar",
        active=True,
        type=Device.types.android,
        name="Pixel 2",
    )
    assert str(device) == f"{user} on android w/ token iamfcmroar..."


@responses.activate
@pytest.mark.django_db
@override_settings(FCM_DEVICES_BACKEND_CLASS="fcm_devices.fcm.FCMBackend")
def test_send_notification(api_client):
    responses.add(
        responses.Response(
            method="POST",
            url=FCMNotification.FCM_END_POINT,
            match_querystring=False,
            json=success_response,
            status=200,
        )
    )
    device = baker.make("fcm_devices.Device", active=True)
    response = service.send_notification(
        device, message_title="Test title", message_body="Test content"
    )
    assert response == success_response
    device.refresh_from_db()
    assert device.active


@responses.activate
@pytest.mark.django_db
@override_settings(FCM_DEVICES_BACKEND_CLASS="fcm_devices.fcm.FCMBackend")
def test_send_notification_invalid_device(api_client, mocker):
    responses.add(
        responses.Response(
            method="POST",
            url=FCMNotification.FCM_END_POINT,
            match_querystring=False,
            json=unrecoverable_error_response,
            status=200,
        )
    )
    device = baker.make("fcm_devices.Device", active=True)
    initial_updated_at = device.updated_at
    device_updated_signal = mocker.patch(
        "fcm_devices.service.signals.device_updated.send"
    )
    response = service.send_notification(
        device, message_title="Test title", message_body="Test content"
    )
    assert response == unrecoverable_error_response
    device.refresh_from_db()
    assert not device.active
    assert device.updated_at > initial_updated_at
    assert device_updated_signal.called_with_args(sender=Device, device=device)


@responses.activate
@pytest.mark.django_db
@override_settings(FCM_DEVICES_BACKEND_CLASS="fcm_devices.fcm.FCMBackend")
def test_send_notification_config_error(api_client, mocker):
    responses.add(
        responses.Response(
            method="POST",
            url=FCMNotification.FCM_END_POINT,
            match_querystring=False,
            json=configuration_error_response,
            status=200,
        )
    )
    device = baker.make("fcm_devices.Device", active=True)
    device_updated_signal = mocker.patch(
        "fcm_devices.service.signals.device_updated.send"
    )
    with pytest.raises(ImproperlyConfigured) as e:
        service.send_notification(
            device, message_title="Test title", message_body="Test content"
        )

    assert e.value.args[0] == (
        f"FCM configuration problem sending to device {device.id}: MismatchSenderId"
    )

    # device should not be deactivated, as if it is a recoverable error we do not
    # need to purge the tokens, we just need to fix the config
    device.refresh_from_db()
    assert device.active
    assert not device_updated_signal.called


# tests for APNs token rejections, which reach us as a 400 rather than the 404
# that PyFCM turns into FCMNotRegisteredError

apns_unregistered_body = json.dumps(
    {
        "error": {
            "code": 400,
            "message": "APNs device token is disabled.",
            "status": "INVALID_ARGUMENT",
            "details": [
                {
                    "@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError",
                    "errorCode": "INVALID_ARGUMENT",
                },
                {
                    "@type": "type.googleapis.com/google.firebase.fcm.v1.ApnsError",
                    "statusCode": 410,
                    "reason": "Unregistered",
                },
            ],
        }
    }
)


malformed_payload_body = json.dumps(
    {
        "error": {
            "code": 400,
            "message": "Request contains an invalid argument.",
            "status": "INVALID_ARGUMENT",
        }
    }
)


@pytest.fixture()
def mock_notify(mocker):
    """
    Stub out credential loading and the FCM client, yielding notify().

    Lets tests drive the backend purely by what PyFCM raises.
    """
    mocker.patch(
        "fcm_devices.fcm.service_account.Credentials.from_service_account_info",
        return_value=mocker.Mock(project_id="a-project"),
    )
    push_service = mocker.patch("fcm_devices.fcm.FCMNotification")
    return push_service.return_value.notify


def test_is_apns_unregistered_error_apns_410():
    assert is_apns_unregistered_error(InvalidDataError(apns_unregistered_body))


def test_is_apns_unregistered_error_without_details():
    assert not is_apns_unregistered_error(InvalidDataError(malformed_payload_body))


def test_is_apns_unregistered_error_non_json():
    # PyFCM also raises InvalidDataError wrapping arbitrary exceptions
    assert not is_apns_unregistered_error(InvalidDataError(ValueError("nope")))


def test_is_apns_unregistered_error_unexpected_details_shape():
    body = json.dumps({"error": {"details": {"statusCode": 410}}})
    assert not is_apns_unregistered_error(InvalidDataError(body))


@pytest.mark.django_db
def test_send_notification_apns_unregistered(mock_notify, mocker):
    mock_notify.side_effect = InvalidDataError(apns_unregistered_body)
    device = baker.make("fcm_devices.Device", active=True)
    initial_updated_at = device.updated_at
    device_updated_signal = mocker.patch("fcm_devices.fcm.device_updated.send")

    result = FCMBackend().send_notification(device, notification_body="Test content")

    assert result is None
    device.refresh_from_db()
    assert not device.active
    assert device.updated_at > initial_updated_at
    device_updated_signal.assert_called_once_with(sender=Device, device=device)


@pytest.mark.django_db
def test_send_notification_invalid_data_not_apns(mock_notify, mocker):
    """A genuinely malformed payload is our bug to fix, so it must still raise."""
    mock_notify.side_effect = InvalidDataError(malformed_payload_body)
    device = baker.make("fcm_devices.Device", active=True)
    device_updated_signal = mocker.patch("fcm_devices.fcm.device_updated.send")

    with pytest.raises(InvalidDataError):
        FCMBackend().send_notification(device, notification_body="Test content")

    device.refresh_from_db()
    assert device.active
    assert not device_updated_signal.called


@pytest.mark.django_db
def test_send_notification_to_user_has_multiple_devices(mocker):
    user = baker.make("auth.User")
    active_device = baker.make("fcm_devices.Device", user=user, active=True)
    second_active_device = baker.make("fcm_devices.Device", user=user, active=True)
    baker.make("fcm_devices.Device", user=user, active=False)
    mocked_send_notification = mocker.patch("fcm_devices.service.send_notification")
    service.send_notification_to_user(
        user, message_title="Test title", message_body="Test content"
    )
    assert mocked_send_notification.call_count == 2
    mocked_send_notification.assert_any_call(
        active_device, message_body="Test content", message_title="Test title"
    )
    mocked_send_notification.assert_any_call(
        second_active_device, message_body="Test content", message_title="Test title"
    )


# tests for API


@pytest.mark.django_db
def test_device_serializer_output():
    device = baker.make("fcm_devices.Device")
    data = DeviceSerializer(device).data
    assert data == {
        "name": device.name,
        "active": device.active,
        "type": device.type,
        "token": device.token,
    }


@pytest.mark.django_db
def test_create_device_not_authenticated(api_client):
    response = api_client.post(
        reverse("devices-list"),
        {
            "name": "Steve's iBlackberry",
            "active": True,
            "type": "ios",
            "token": "iamalovelytokenindeed",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_device(api_client):
    user = baker.make("auth.User")
    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("devices-list"),
        {
            "name": "Steve's iBlackberry",
            "active": True,
            "type": "ios",
            "token": "iamalovelytokenindeed",
        },
    )
    assert response.status_code == 201
    device = user.devices.first()
    assert response.data == DeviceSerializer(device).data


@pytest.mark.django_db
def test_create_device_duplicate(api_client):
    """
    Should not be possible to create duplicates as if there
    is a conflict the create will be commuted to an update.
    """
    device = baker.make("fcm_devices.Device")
    api_client.force_authenticate(device.user)
    response = api_client.post(
        reverse("devices-list"),
        {
            "name": "Steve's iBlackberry",
            "active": True,
            "type": "ios",
            "token": device.token,
        },
    )
    assert response.status_code == 201
    new_device = device.user.devices.last()
    assert new_device == device


# test admin send action


@pytest.mark.django_db
@responses.activate
@override_settings(FCM_DEVICES_BACKEND_CLASS="fcm_devices.fcm.FCMBackend")
def test_send_test_notification_action(client, mocker):
    responses.add(
        responses.Response(
            method="POST",
            url=FCMNotification.FCM_END_POINT,
            match_querystring=False,
            json=success_response,
            status=200,
        )
    )

    device = baker.make(
        "fcm_devices.Device", user__is_staff=True, user__is_superuser=True
    )
    responses.add(
        responses.Response(
            method="POST",
            url=FCMNotification.FCM_END_POINT,
            match_querystring=False,
            json=success_response,
            status=200,
        )
    )

    client.force_login(device.user)

    send_url = reverse("admin:fcm_devices_device_changelist")
    data = {
        "action": "send_notification",
        "select_across": "0",
        "index": "0",
        "_selected_action": device.id,
    }

    response = client.post(send_url, data=data)

    assert response.status_code == 302
    assert len(responses.calls) == 1
    assert json.loads(responses.calls[0].response.text) == success_response
