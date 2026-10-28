"""Settings for isolated Django tests.

The project contains legacy domain models whose migration graph is incomplete.
Use Django's syncdb path for disposable test databases only; production
migration behavior is unchanged.
"""

from .settings import *  # noqa: F403

# Keep test throttles isolated; production uses the shared database cache.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nebula-tests",
    }
}

# Build the test schema from current models in one pass. This ensures foreign
# keys between migrated and legacy/unmigrated apps are created only after all
# referenced tables exist. This setting applies to test databases only.
DATABASES["default"].setdefault("TEST", {})["MIGRATE"] = False  # noqa: F405

# Preserve the small amount of seed data previously supplied by comment's
# initial migration, since migrations are intentionally disabled in tests.
from django.db.models.signals import post_migrate


def seed_comment_defaults(sender, **kwargs):
    CommentSettings = apps.get_model("comment", "CommentSettings")  # noqa: N806
    React = apps.get_model("comment", "React")  # noqa: N806
    CommentSettings.objects.get_or_create(
        slug="default-config", defaults={"name": "Nebula Vault Blog"}
    )
    React.objects.get_or_create(slug="like", defaults={"emoji": "👍"})
    React.objects.get_or_create(slug="dislike", defaults={"emoji": "👎"})


from django.apps import apps

post_migrate.connect(
    seed_comment_defaults,
    dispatch_uid="nebula_test_seed_comment_defaults",
    weak=False,
)

# Avoid requiring collectstatic's production manifest during test client requests.
STORAGES = {
    **STORAGES,  # noqa: F405 - inherited from config.settings
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
