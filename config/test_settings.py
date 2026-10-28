"""Settings for isolated Django tests.

The repository currently has no migration files for the domain apps below.
Treat them as unmigrated apps in the disposable test database so Django
creates their tables via syncdb after applying the built-in and staff
migrations. Production settings are unchanged.
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
    # Customer tables are created by the application's custom initial migration
    # only when run against an established database; sync them directly here.
    "accounts": None,
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
