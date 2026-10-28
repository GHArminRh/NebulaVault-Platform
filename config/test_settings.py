"""Settings for isolated Django tests.

Domain apps without their own migrations are synchronized directly into the
disposable test database. The accounts migration is retained because comment
and blog migrations depend on it.
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
    # Keep accounts migrations enabled: comment.0001_initial depends on it.
    # Other domain apps without migrations are synchronized directly.
    "catalog": None,
    "subscriptions": None,
    "licensing": None,
    "devices": None,
    "billing": None,
    "audit": None,
    "notifications": None,
    "portal": None,
}

# Avoid requiring collectstatic's production manifest during test client requests.
STORAGES = {
    **STORAGES,  # noqa: F405 - inherited from config.settings
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
