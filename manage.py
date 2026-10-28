#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _reset_test_database_once():
    """One-time, explicitly gated reset for the disposable Render test database.

    The marker schema is intentionally outside public, so the reset cannot repeat
    on later restarts while the temporary environment flag remains configured.
    """
    if os.environ.get("RESET_TEST_DATABASE_ONCE") != "nebula-vault-db":
        return
    if sys.argv[1:2] != ["migrate"]:
        return

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name = %s)",
            ["_nebula_reset_marker"],
        )
        already_reset = cursor.fetchone()[0]
        if already_reset:
            return

        # This is destructive by design and is only enabled by the exact
        # one-time token above for the disposable test database.
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE")
        cursor.execute("CREATE SCHEMA public AUTHORIZATION CURRENT_USER")
        cursor.execute("CREATE SCHEMA _nebula_reset_marker")
        connection.commit()


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    _reset_test_database_once()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate your virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
