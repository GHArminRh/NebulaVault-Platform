"""Django settings for config project."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "accounts", "staff.apps.StaffConfig", "catalog.apps.CatalogConfig", "subscriptions.apps.SubscriptionsConfig",
    "licensing.apps.LicensingConfig", "devices.apps.DevicesConfig",
    "billing.apps.BillingConfig", "audit.apps.AuditConfig",
    "notifications.apps.NotificationsConfig", "portal.apps.PortalConfig",
]

NEBULA_EDITOR_CONFIG = {
    "height": 420,
    "menubar": "file edit view insert format tools table help",
    "plugins": (
        "advlist autolink lists link image charmap preview anchor "
        "searchreplace visualblocks code fullscreen insertdatetime media "
        "table wordcount"
    ),
    "toolbar": (
        "undo redo | blocks | fontfamily fontsize | "
        "bold italic underline strikethrough | "
        "alignleft aligncenter alignright alignjustify | "
        "bullist numlist outdent indent | "
        "forecolor backcolor | link image media table | "
        "removeformat | searchreplace | code fullscreen"
    ),
    "branding": False,
    "promotion": False,
    "resize": True,
    "statusbar": True,
    "convert_urls": False,
    "relative_urls": False,
    "browser_spellcheck": True,
    "paste_data_images": True,
    "automatic_uploads": True,
    "image_caption": True,
    "images_file_types": "jpg,jpeg,png,gif,webp",
    "block_formats": "Paragraph=p; Heading 1=h1; Heading 2=h2; Heading 3=h3; Heading 4=h4; Preformatted=pre; Blockquote=blockquote",
    "content_style": (
        "body { font-family: Arial, Tahoma, sans-serif; font-size: 14px; } "
        "img { max-width: 100%; height: auto; } "
        "table { border-collapse: collapse; max-width: 100%; } "
        "td, th { border: 1px solid #d1d5db; padding: 6px; }"
    ),
}

# Both staff/admin accounts and site customers use UUID4 primary keys.
# Keep the two account types separate: StaffUser owns Django permissions and admin access.
AUTH_USER_MODEL = "staff.StaffUser"
AUTHENTICATION_BACKENDS = [
    "accounts.backends.CustomerAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "portal.middleware.InterfaceLanguageMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "accounts.middleware.UUIDCompatibleAuthenticationMiddleware", "portal.middleware.SeparateStaffAndCustomerSessionsMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "portal.context_processors.cart_context",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql", "NAME": os.environ["DB_NAME"],
    "USER": os.environ["DB_USER"], "PASSWORD": os.environ["DB_PASSWORD"],
    "HOST": os.environ.get("DB_HOST", "127.0.0.1"), "PORT": os.environ.get("DB_PORT", "5432"),
    "CONN_MAX_AGE": 60,
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "fa"
LANGUAGES = [("fa", "فارسی")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else ("django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend"),
)
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "Nebula Vault <no-reply@localhost>")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "15"))
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", "86400"))
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "portal:home"

# Uploaded release installers and archives.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media/"

# The mock checkout is for development/testing only. Enable explicitly via env when needed.
NEBULA_MOCK_PAYMENTS = os.environ.get("NEBULA_MOCK_PAYMENTS", str(DEBUG)).lower() == "true"
