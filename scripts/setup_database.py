"""Initialize a fresh local PostgreSQL role/database and write the local .env file."""
from __future__ import annotations

import getpass
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
DB_NAME = "nebula_vault"
DB_USER = "nebula_vault_app"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"


def main() -> int:
    if ENV_FILE.exists():
        values = dotenv_values(ENV_FILE)
        required = ("DJANGO_SECRET_KEY", "DB_NAME", "DB_USER", "DB_PASSWORD")
        if not all(values.get(key) for key in required):
            print("ERROR: .env already exists but is missing required settings.")
            print("It was left untouched. Fix it manually, then run this launcher again.")
            return 1
        try:
            with psycopg.connect(make_conninfo(
                host=values.get("DB_HOST") or DB_HOST,
                port=values.get("DB_PORT") or DB_PORT,
                dbname=values["DB_NAME"],
                user=values["DB_USER"],
                password=values["DB_PASSWORD"],
                connect_timeout=5,
            )):
                print("Existing .env and database connection verified.")
            return 0
        except Exception as exc:
            print(f"ERROR: Could not connect using the existing .env: {exc}")
            print(".env was not changed. Check PostgreSQL and its credentials.")
            return 1

    print("\nNebula Vault Platform — first-time local database setup")
    print("PostgreSQL must already be installed and running on this computer.")
    admin_user = input("PostgreSQL administrator username [postgres]: ").strip() or "postgres"
    admin_password = getpass.getpass("PostgreSQL administrator password (input hidden): ")
    if not admin_password:
        print("ERROR: An administrator password is required.")
        return 1

    app_password = secrets.token_urlsafe(32)
    secret_key = secrets.token_urlsafe(50)

    try:
        admin_conninfo = make_conninfo(
            host=DB_HOST, port=DB_PORT, dbname="postgres",
            user=admin_user, password=admin_password, connect_timeout=5,
        )
        with psycopg.connect(admin_conninfo, autocommit=True) as conn:
            existing_db = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
            ).fetchone()
            existing_role = conn.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,)
            ).fetchone()

            if existing_db:
                print(f"ERROR: Database '{DB_NAME}' already exists, but .env does not.")
                print("To avoid changing or overwriting existing data, setup stopped.")
                print("Restore the matching .env or inspect the database manually.")
                return 1
            if existing_role:
                print(f"ERROR: PostgreSQL role '{DB_USER}' already exists, but .env does not.")
                print("To avoid changing an existing role/password, setup stopped.")
                print("Restore the matching .env or inspect the role manually.")
                return 1

            conn.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(DB_USER), sql.Literal(app_password)
                )
            )
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(DB_NAME), sql.Identifier(DB_USER)
                )
            )

        env_text = (
            f'DJANGO_SECRET_KEY="{secret_key}"\n'
            'DJANGO_DEBUG=True\n'
            'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n'
            f'DB_NAME={DB_NAME}\n'
            f'DB_USER={DB_USER}\n'
            f'DB_PASSWORD={app_password}\n'
            f'DB_HOST={DB_HOST}\n'
            f'DB_PORT={DB_PORT}\n'
        )
        with ENV_FILE.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(env_text)
        print("Created the local database, restricted application role, and .env file.")
        return 0
    except Exception as exc:
        print(f"ERROR: Database setup failed: {exc}")
        print("No existing .env was overwritten. Check PostgreSQL credentials and permissions.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
