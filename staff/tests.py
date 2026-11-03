import os
from unittest.mock import call, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from staff.management.commands.bootstrap_render_admin import Command
from staff.management.commands.render_startup import Command as RenderStartupCommand


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
            patch(
                "django.core.management.call_command",
                side_effect=[RuntimeError("temporary"), None],
            ) as call_command,
        ):
            with self.assertRaisesMessage(RuntimeError, "temporary"):
                Command().handle()
            Command().handle()

        self.assertEqual(call_command.call_count, 2)


class RenderStartupCommandTests(SimpleTestCase):
    @patch("staff.management.commands.render_startup.connection")
    @patch("staff.management.commands.render_startup.call_command")
    def test_runs_migrations_and_bootstrap_in_one_command_process(
        self, call_command, connection
    ):
        connection.introspection.table_names.return_value = ["django_cache", "auth_user"]

        RenderStartupCommand().handle(verbosity=1)

        self.assertEqual(
            call_command.call_args_list,
            [
                call("migrate", interactive=False, verbosity=1),
                call("bootstrap_render_admin", verbosity=1),
            ],
        )

    @patch("staff.management.commands.render_startup.connection")
    @patch("staff.management.commands.render_startup.call_command")
    def test_creates_cache_table_only_when_missing(self, call_command, connection):
        connection.introspection.table_names.return_value = ["auth_user"]

        RenderStartupCommand().handle(verbosity=1)

        self.assertEqual(
            call_command.call_args_list,
            [
                call("migrate", interactive=False, verbosity=1),
                call(
                    "createcachetable",
                    "django_cache",
                    database="default",
                    verbosity=1,
                ),
                call("bootstrap_render_admin", verbosity=1),
            ],
        )
