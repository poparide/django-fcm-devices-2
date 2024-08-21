from django.conf import settings


class AppSettings(object):
    def __init__(self, prefix, defaults):
        self.prefix = prefix
        self.defaults = defaults

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid app setting: {attr}")
        return getattr(settings, f"{self.prefix}_{attr}", self.defaults[attr])


DEFAULTS = {
    # from firebase service account file, found at
    # https://console.firebase.google.com/u/0/project/_/settings/serviceaccounts/adminsdk
    "GOOGLE_SERVICE_ACCOUNT_INFO": None,
    # this is redundant, as it can be inferred from credentials/account info,
    # but alas is a required param for PyFCM at the moment.
    # See https://github.com/olucurious/PyFCM/issues/357
    "GOOGLE_PROJECT_ID": None,

    # allow customisation of how messages are actually sent
    "BACKEND_CLASS": None,
}


app_settings = AppSettings("FCM_DEVICES", DEFAULTS)
