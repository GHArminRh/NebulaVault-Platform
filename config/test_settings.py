"""Settings for isolated Django tests.

Domain apps without a test migration graph are synchronized directly into the
disposable test database. Production settings and migrations are unchanged.
"""

from .settings import *  # noqa: F403

# Keep test throttles isolated; production uses the shared database cache.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nebula-tests",
    }
}

MIGRATION_MODULES = {
    # These apps are synchronized directly in test databases.
    "accounts": None,
    "catalog": None,
    "subscriptions": None,
    "licensing": None,
    "devices": None,
    "billing": None,
    "audit": None,
    "notifications": None,
    "portal": None,
    # These legacy app migrations depend on each other and on accounts.
    # For isolated tests, synchronize their tables together rather than
    # resolving a migration graph whose parent migrations are disabled.
    "comment": None,
    "blog": None,
}

# Avoid requiring collectstatic's production manifest during test client requests.
STORAGES = {
    **STORAGES,  # noqa: F405 - inherited from config.settings
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
