"""Settings for isolated Django tests.

The repository currently has no migration files for the domain apps below.
Treat them as unmigrated apps in the disposable test database so Django
creates their tables via syncdb after applying the built-in and account
migrations. Production settings are unchanged.
"""
from .settings import *  # noqa: F403

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
