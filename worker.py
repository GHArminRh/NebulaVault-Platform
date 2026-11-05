"""Low-memory entry point for the Enzonic-hosted Celery worker.

The broker URL must be supplied as an environment variable. This process
intentionally uses Celery's solo pool because the free Enzonic instance has
one CPU core and limited memory.
"""

import os


def main() -> None:
    broker_url = os.environ.get("CELERY_BROKER_URL", "").strip()
    if not broker_url:
        raise SystemExit(
            "CELERY_BROKER_URL is missing. Add the CloudAMQP AMQPS URL "
            "to the server private environment variables."
        )
    if not broker_url.startswith("amqps://"):
        raise SystemExit(
            "CELERY_BROKER_URL must use amqps:// so the broker connection is encrypted."
        )

    from config.celery import app

    app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
            "--pool=solo",
            "--concurrency=1",
            "--hostname=nebula-vault@%h",
            "--without-gossip",
            "--without-mingle",
        ]
    )


if __name__ == "__main__":
    main()
