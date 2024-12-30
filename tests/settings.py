import os


DEBUG = True
USE_TZ = True
TIME_ZONE = "UTC"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tests.urls"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "fcm_devices",
    "tests",
]
SITE_ID = 1

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("TEST_DATABASE_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("TEST_DATABASE_NAME", "fcm_devices"),
        "HOST": os.environ.get("TEST_DATABASE_HOST", "localhost"),
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": True,
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
            ],
        },
    }
]
SECRET_KEY = "fcm-devices-secret-key"

FCM_DEVICES_GOOGLE_SERVICE_ACCOUNT_INFO = {
    "project_id": "foobarbaz123",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_email": "firebase-notarealserviceaccount.gserviceaccount.com",
    # Not a real key, but must be valid format to decode fake credentials
    "private_key": """-----BEGIN RSA PRIVATE KEY-----
MIICXgIBAAKBgQDGhuoq9786XTocvnQRsaZsAei7I6teMIiSxvoXti4aMHgEh1yp
ETLmx0S+ZH1mBDo84x5l2NC+zsDpQAhA394In1WGSBsIDXLowBYcmrgRkZCmyJyS
tC89LQlW7J5SkJcsKPqufG3/5QP8tSL/7BtKYY0Hiufa6Qld9GZlyEazrwIDAQAB
AoGAaWMZT/Hwe6UdwkCAERyDQfbJev52bCvLdE9YV9oIIzLzo0PQNpfAs624mnFx
+APqfoP6kQpF1eSfl7K8LuQoUu82qbjFwABUvvV4jwDH14mfIb6hbs7HhSM6CPSF
/rIL26rY2EKhHJTkiRGxhOfwZpkld2CXgrlSttj+HoE5CcECQQD1pfP+JKGPf+YN
VCprmkK/S/uHz2Wg69QW2ohAiANkKUCHdwJIOM9/7DcuD6ZeM8IbYU5daXuLcHuc
GMftRVUxAkEAzuSebzrBKXvPIPYKT1NQ7CZ5f0QT7CxC712mWAg3XIFdEDnBorTo
aiWxrELDX2O1lzdUw5ll0fe36xjNLNHe3wJBAO2ztaPSXIfYkouJSzcuYbJs2yvz
E/ug2G147+nJ88YjaO7syUeLubampEqtGCcF3KnUAhnALa2jnelRzXya37ECQQDM
BGG/qZ6lO7PK+xS7mJsp497XgthqglMXG7BXCvMcw2xz/aBWxDKTycvk5IkoXXjK
PwPVRkVDwhWZPYHF+sbdAkEApj8UktyjmiYQBMVraY9A7EqlWkLOTeCZZkvfOUVe
w8BA8vTSfdGaKJDyNd6q+PEKEZy+bP3t3hjFY4w75whOiA==
-----END RSA PRIVATE KEY-----""",
}
