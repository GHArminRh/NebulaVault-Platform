import os
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from staff.management.commands.bootstrap_render_admin import Command


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class AlgoliaBootstrapCommandTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_bootstrap_reindexes_only_once_for_the_same_token(self):
        with (
            patch.dict(os.environ, {"ALGOLIA_REINDEX_ON_BOOT": "test-run-token"}),
            patch("django.core.management.call_command") as call_command,
        ):
            Command().handle()
            Command().handle()

        call_command.assert_called_once_with("reindex_algolia")

    def test_failed_reindex_can_be_retried(self):
        with (
            patch.dict(os.environ, {"ALGOLIA_REINDEX_ON_BOOT": "retry-token"}),
            patch("django.core.management.call_command", side_effect=[RuntimeError("temporary"), None]) as call_command,
        ):
            with self.assertRaisesMessage(RuntimeError, "temporary"):
                Command().handle()
            Command().handle()

        self.assertEqual(call_command.call_count, 2)
