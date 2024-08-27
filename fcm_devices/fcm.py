from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from pyfcm import FCMNotification
from pyfcm.errors import FCMNotRegisteredError, FCMServerError

from .settings import app_settings
from .signals import device_updated
from google.oauth2 import service_account


class FCMBackend(object):
    """You can override this class to customise sending of notifications."""

    def send_notification(self, device, **kwargs):
        credentials = service_account.Credentials.from_service_account_info(
            app_settings.GOOGLE_SERVICE_ACCOUNT_INFO,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        # PyFCM supports loading from service file directly, OR passing in credentials.
        # unfortunately we can't pass in the info to be loaded there, so for now
        # I'm just adding the oauth client to this lib, loading the creds, then passing them in.
        push_service = FCMNotification(
            # Annoyingly service_account_file and project_id are positional args, when really PyFCM should
            # be checking for the existence of credentials first. Project ID can be inferred from credentials.
            # but for now we'll just pass it as its own setting. TODO create PyFCM issue/PR to fix
            service_account_file=None,
            project_id=app_settings.GOOGLE_PROJECT_ID,
            credentials=credentials
        )
        # NOTE: In PyFCM 2.x, the response from `notify` is simply a dictionary with one field, 'name',
        # which is the identifier of the message sent, in the format of projects/*/messages/{message_id}.
        # Errors are raised and there is no longer a 'failure' key in the response to parse.
        result = None
        try:
            result = push_service.notify(
                fcm_token=device.token,
                **kwargs,
            )

        # missing, unregistered, and invalid. see
        # https://firebase.google.com/docs/reference/fcm/rest/v1/ErrorCode
        except FCMNotRegisteredError as e:
            self.update_device_on_registration_error(device)

        # SENDER_ID_MISMATCH - PyFCM should be able to parse the 403 specifically.
        # See https://github.com/olucurious/PyFCM/pull/358
        except FCMServerError as e:
            if "Unexpected status code 403" in str(e):
                self.update_device_on_registration_error(device)
                raise ImproperlyConfigured(
                    "The authenticated sender ID is different from the sender ID"
                    " of the registration token."
                )
            raise e

        return result

    def update_device_on_registration_error(self, device):
        """
        If a device fails to be sent a notification due to an unrecoverable
        issue we want to ensure we don't try again.
        """
        device.active = False
        device.save(update_fields=("active", "updated_at"))
        device_updated.send(sender=device.__class__, device=device)


class ConsoleFCMBackend(FCMBackend):
    """Console FCM backend for development environments."""

    def send_notification(self, device, **kwargs):
        print(f"Push to {device}\nPyFCM kwargs: {kwargs}\n")
        return {"name": "my/message/resource/:foobarbaz123"}


def get_fcm_backend():
    cls = app_settings.BACKEND_CLASS
    if cls is None:
        # default to console to avoid accidental push notifications
        return ConsoleFCMBackend()
    return import_string(cls)()
