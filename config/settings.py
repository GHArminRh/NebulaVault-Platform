"""Django settings for config project."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Core Django settings
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Django apps
INSTALLED_APPS = [
    "django_admin_dracula",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "easy_thumbnails",
    "filer",
    "image_uploader_widget",
    # Django Control Room: register the shared base, official panels, then hub.
    "dj_control_room_base",
    "dj_redis_panel",
    "dj_cache_panel",
    "dj_celery_panel",
    "dj_urls_panel",
    "dj_signals_panel",
    "dj_error_panel",
    "dj_control_room",
    "staff.apps.StaffConfig",
    "import_export",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "api.apps.ApiConfig",
    "tinymce",
    "rating.apps.RatingConfig",
    "comment.apps.CommentConfig",
    "blog.apps.BlogConfig",
    "accounts",
    "catalog.apps.CatalogConfig",
    "subscriptions.apps.SubscriptionsConfig",
    "licensing.apps.LicensingConfig",
    "devices.apps.DevicesConfig",
    "billing.apps.BillingConfig",
    "audit.apps.AuditConfig",
    "notifications.apps.NotificationsConfig",
    "portal.apps.PortalConfig",
]

TINYMCE_DEFAULT_CONFIG = {
    "height": 420,
    "menubar": "file edit view insert format tools table help",
    "plugins": "advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table wordcount",
    "toolbar": "undo redo | blocks | fontfamily fontsize | bold italic underline strikethrough | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | forecolor backcolor | link image media table | removeformat | searchreplace | code fullscreen",
    "branding": False,
    "promotion": False,
    "resize": True,
    "statusbar": True,
    "convert_urls": False,
    "relative_urls": False,
    "browser_spellcheck": True,
    "paste_data_images": True,
    "automatic_uploads": True,
    "images_upload_url": "/admin/editor-upload/",
    "images_upload_credentials": True,
    "image_caption": True,
    "images_file_types": "jpg,jpeg,png,gif,webp",
    "content_style": "body { font-family: Arial, Tahoma, sans-serif; font-size: 14px; } img { max-width: 100%; height: auto; } table { border-collapse: collapse; max-width: 100%; } td, th { border: 1px solid #d1d5db; padding: 6px; }",
}

AUTH_USER_MODEL = "staff.StaffUser"
AUTHENTICATION_BACKENDS = [
    "accounts.backends.CustomerAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "portal.middleware.InterfaceLanguageMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # This layer then resolves the active UUID-backed staff/customer identity.
    "accounts.middleware.UUIDCompatibleAuthenticationMiddleware",
    "portal.middleware.SeparateStaffAndCustomerSessionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "portal.context_processors.cart_context",
                "accounts.context_processors.turnstile",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    import dj_database_url  # noqa: E402
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL, conn_max_age=60, ssl_require=not DEBUG
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ["DB_USER"],
            "PASSWORD": os.environ["DB_PASSWORD"],
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
SITE_ID = 1
X_FRAME_OPTIONS = "SAMEORIGIN"
LANGUAGES = [("en", "English"), ("fa", "Persian")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Media storage is independent of django CMS. Keep the legacy environment
# variable as a fallback so existing Render S3 media configuration continues
# to work without requiring an environment-variable rename during this removal.
MEDIA_STORAGE_BACKEND = os.environ.get(
    "MEDIA_STORAGE_BACKEND",
    os.environ.get("CMS_MEDIA_STORAGE_BACKEND", "local"),
).strip().lower()
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "").strip()
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "").strip() or None
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", "").strip() or None
AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN", "").strip() or None
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = (
    os.environ.get("AWS_QUERYSTRING_AUTH", "False").strip().lower() == "true"
)
MEDIA_S3_STORAGE_ENABLED = bool(
    MEDIA_STORAGE_BACKEND == "s3"
    and AWS_STORAGE_BUCKET_NAME
    and AWS_ACCESS_KEY_ID
    and AWS_SECRET_ACCESS_KEY
)
DEFAULT_MEDIA_STORAGE = (
    {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "region_name": AWS_S3_REGION_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "custom_domain": AWS_S3_CUSTOM_DOMAIN,
            "file_overwrite": False,
            "default_acl": None,
            "querystring_auth": AWS_QUERYSTRING_AUTH,
        },
    }
    if MEDIA_S3_STORAGE_ENABLED
    else {"BACKEND": "django.core.files.storage.FileSystemStorage"}
)
STORAGES = {
    "default": DEFAULT_MEDIA_STORAGE,
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media/"
DJANGORESIZED_DEFAULT_FORMAT_EXTENSIONS = {"WEBP": ".webp", "JPEG": ".jpg"}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 10000},
    }
}
LOGIN_URL = "login"

EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "15"))

if os.environ.get("RESEND_API_KEY", "").strip():
    _default_email_backend = "accounts.email_backends.ResendEmailBackend"
else:
    _default_email_backend = (
        "django.core.mail.backends.smtp.EmailBackend"
        if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
        else (
            "django.core.mail.backends.console.EmailBackend"
            if DEBUG
            else "django.core.mail.backends.smtp.EmailBackend"
        )
    )
if os.environ.get("RESEND_API_KEY", "").strip():
    EMAIL_BACKEND = "accounts.email_backends.ResendEmailBackend"
else:
    EMAIL_BACKEND = os.environ.get("DJANGO_EMAIL_BACKEND", _default_email_backend)

if os.environ.get("RESEND_API_KEY", "").strip():
    DEFAULT_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev").strip()
else:
    DEFAULT_FROM_EMAIL = os.environ.get(
        "DJANGO_DEFAULT_FROM_EMAIL",
        EMAIL_HOST_USER or "Nebula Vault <no-reply@localhost>",
    )

EMAIL_API_TIMEOUT = int(os.environ.get("EMAIL_API_TIMEOUT", "15"))
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", "86400"))
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "portal:home"

ZARINPAL_MERCHANT_ID = os.environ.get("ZARINPAL_MERCHANT_ID", "").strip()
ZARINPAL_SANDBOX = os.environ.get("ZARINPAL_SANDBOX", "False").lower() == "true"
ZARINPAL_ENABLED = os.environ.get("ZARINPAL_ENABLED", "True").lower() == "true"

TURNSTILE_ENABLED = (
    os.environ.get("TURNSTILE_ENABLED", "True").strip().lower()
    in {"1", "true", "yes", "on"}
)
TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "").strip()
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

COMMENT_SETTINGS = {"URLHASH_LENGTH": 12, "OFFLINE_IMPORTS": True, "PROFILE_IMAGE_FIELD": None}
RATING_SETTINGS = {"URLHASH_LENGTH": 8}
# Upstream django-rating-system seeds settings by downloading images during its
# second migration. Keep its schema migration local and deterministic instead.
MIGRATION_MODULES = {"rating": "config.rating_migrations"}


# Django REST Framework defaults: customer authentication is handled by the
# project's dual-user-model session middleware or revocable Bearer API tokens.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.CustomerBearerAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "user": "1000/day",
        "token_login": "5/minute",
        "ratings": "20/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Nebula Vault API",
    "DESCRIPTION": (
        "Versioned API for public products, releases, plans and blog content, "
        "plus authenticated customer profile, subscriptions, orders and ratings."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
