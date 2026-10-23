from __future__ import annotations

import os
import secrets
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DB_NAME = "nebula_vault"
DB_USER = "nebula_vault_app"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
SITE_URL = "http://127.0.0.1:8000/"


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env(values: dict[str, str]) -> None:
    content = (
        "# Local development settings for Nebula Vault. Do not commit this file.\n"
        f"DJANGO_SECRET_KEY={values['DJANGO_SECRET_KEY']}\n"
        "DJANGO_DEBUG=True\n"
        "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n"
        f"DB_NAME={values['DB_NAME']}\n"
        f"DB_USER={values['DB_USER']}\n"
        f"DB_PASSWORD={values['DB_PASSWORD']}\n"
        f"DB_HOST={values['DB_HOST']}\n"
        f"DB_PORT={values['DB_PORT']}\n"
        f"POSTGRES_ADMIN_USER={values.get('POSTGRES_ADMIN_USER', 'postgres')}\n"
        f"POSTGRES_ADMIN_PASSWORD={values.get('POSTGRES_ADMIN_PASSWORD', '98741236')}\n"
    )
    ENV_PATH.write_text(content, encoding="utf-8")


def app_database_works(values: dict[str, str]) -> bool:
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=values["DB_NAME"],
            user=values["DB_USER"],
            password=values["DB_PASSWORD"],
            host=values["DB_HOST"],
            port=values["DB_PORT"],
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


def prepare_database(values: dict[str, str]) -> dict[str, str]:
    import psycopg2
    from psycopg2 import sql

    print("\nPostgreSQL database setup")
    print("-------------------------")
    # Credentials are read from the local, git-ignored .env file; no prompts.
    admin_user = values.get("POSTGRES_ADMIN_USER", "postgres").strip() or "postgres"
    admin_password = values.get("POSTGRES_ADMIN_PASSWORD", "98741236").strip() or "98741236"
    if not admin_password:
        raise RuntimeError(
            "PostgreSQL administrator password is missing from .env. Add "
            "POSTGRES_ADMIN_USER=postgres and POSTGRES_ADMIN_PASSWORD=your-password."
        )

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=admin_user,
            password=admin_password,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5,
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not connect to PostgreSQL at 127.0.0.1:5432.\n"
            "Make sure PostgreSQL is installed and its Windows service is running, "
            "then retry. Verify the administrator username/password.\n"
            f"Details: {exc}"
        ) from exc

    existing_password = values.get("DB_PASSWORD", "")
    if existing_password.lower() in {"replace-with-your-local-database-password", "change-me", "your-password"}:
        existing_password = ""
    app_password = existing_password or secrets.token_urlsafe(24)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,))
            if cur.fetchone():
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(DB_USER)),
                    (app_password,),
                )
            else:
                cur.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(DB_USER)),
                    (app_password,),
                )

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            if not cur.fetchone():
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(DB_NAME), sql.Identifier(DB_USER)
                    )
                )
            else:
                cur.execute(
                    sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                        sql.Identifier(DB_NAME), sql.Identifier(DB_USER)
                    )
                )
    finally:
        conn.close()

    values.update({
        "DJANGO_SECRET_KEY": values.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50),
        "DJANGO_DEBUG": "True",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": app_password,
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
    })
    write_env(values)
    return values


def repair_inconsistent_fresh_database(values: dict[str, str]) -> None:
    """Reset an inconsistent local schema when migration records outlive auth_user.

    This is only intended for the project's disposable local development database.
    It preserves nothing in that database, so it runs only when Django's migration
    ledger says auth migrations were applied but the required auth_user table is absent.
    """
    import psycopg2
    from psycopg2 import sql

    conn = psycopg2.connect(
        dbname=values["DB_NAME"],
        user=values["DB_USER"],
        password=values["DB_PASSWORD"],
        host=values["DB_HOST"],
        port=values["DB_PORT"],
        connect_timeout=5,
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.auth_user')")
            if cur.fetchone()[0] is not None:
                return
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'django_migrations')"
            )
            has_migration_ledger = cur.fetchone()[0]
            if not has_migration_ledger:
                return
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM public.django_migrations "
                "WHERE app = 'auth' AND name = '0012_alter_user_first_name_max_length')"
            )
            auth_marked_applied = cur.fetchone()[0]
            if not auth_marked_applied:
                return

            print(
                "\\nWARNING: This local database has an inconsistent migration history "
                "(auth migrations are marked applied, but auth_user is missing)."
            )
            print("Resetting its public schema so migrations can build a consistent fresh database.")
            cur.execute("DROP SCHEMA public CASCADE")
            cur.execute(
                sql.SQL("CREATE SCHEMA public AUTHORIZATION {}").format(
                    sql.Identifier(values["DB_USER"])
                )
            )
    finally:
        conn.close()


def main() -> int:
    os.chdir(BASE_DIR)
    values = read_env(ENV_PATH)

    # Reuse the working app DB first. Only request admin credentials if setup is necessary.
    if not values.get("DJANGO_SECRET_KEY"):
        values["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(50)
    values.setdefault("DB_NAME", DB_NAME)
    values.setdefault("DB_USER", DB_USER)
    values.setdefault("DB_HOST", DB_HOST)
    values.setdefault("DB_PORT", DB_PORT)
    values.setdefault("POSTGRES_ADMIN_USER", "postgres")
    values.setdefault("POSTGRES_ADMIN_PASSWORD", "98741236")

    if not values.get("DB_PASSWORD") or not app_database_works(values):
        # Existing installs may not need administrator credentials if the app role
        # and database are already provisioned. But if app connection fails, admin
        # credentials must be available locally.
        values = prepare_database(values)
    else:
        values.setdefault("DJANGO_DEBUG", "True")
        values.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
        write_env(values)

    repair_inconsistent_fresh_database(values)

    print("\n[4/5] Generating migrations from current model definitions...")
    result = subprocess.run(
        [sys.executable, "manage.py", "makemigrations", "--noinput"],
        cwd=BASE_DIR,
    )
    if result.returncode:
        print("\nMigration generation failed. Fix the error above, then run START_NEBULA_VAULT.bat again.")
        return result.returncode

    print("\n[5/5] Applying all pending migrations...")
    result = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=BASE_DIR)
    if result.returncode:
        print("\nMigration failed. Fix the error above, then run START_NEBULA_VAULT.bat again.")
        return result.returncode

    print("\nEnsuring the local development administrator exists...")
    result = subprocess.run(
        [sys.executable, "manage.py", "bootstrap_local_admin"],
        cwd=BASE_DIR,
        env={**os.environ, "DJANGO_DEBUG": values.get("DJANGO_DEBUG", "True")},
    )
    if result.returncode:
        print("\nAdministrator setup failed.")
        return result.returncode

    print("\nStarting the local Django development server.")
    print(f"Site: {SITE_URL}")
    print("Keep this window open while using the site. Press Ctrl+C to stop it.\n")

    # Open the browser after the server has had a moment to start.
    import threading
    threading.Timer(1.5, lambda: webbrowser.open(SITE_URL)).start()
    return subprocess.call(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000"],
        cwd=BASE_DIR,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nNebula Vault server stopped.")
        raise SystemExit(0)
    except Exception as exc:
        print(f"\nSETUP ERROR: {exc}")
        raise SystemExit(1)
