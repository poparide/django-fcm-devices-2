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
    # firebase credentials file, found at
    # https://console.firebase.google.com/u/0/project/_/settings/serviceaccounts/adminsdk
    # need to figure out how to load this... is it a path or a file?
    # it's loaded via google.oauth2.service_account.Credentials.from_service_account_file
    # https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.service_account.html#module-google.oauth2.service_account
    # so we can also do from_service_account_info if we have it stored, which may be preferable...
    # and in PyFCM we can pass credentials instead of service_account_file,
    # so maybe just want to do that instead (pass in FCM credentials from our own project settings)
    # Loaded in Credentials and sent off to backend.
    "GOOGLE_SERVICE_ACCOUNT_INFO": None,
     # this is redundant, as it can be inferred from credentials/account info,
     # but alas is a required param for PyFCM at the moment
    "GOOGLE_PROJECT_ID": None,

    # allow customisation of how messages are actually sent
    "BACKEND_CLASS": None,
}


app_settings = AppSettings("FCM_DEVICES", DEFAULTS)
