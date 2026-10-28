"""
WSGI config for config project.

It exposes the Django WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

_django_application = get_wsgi_application()


def application(environ, start_response):
    """Answer Render's health check before Django's host/security middleware runs."""
    if environ.get("PATH_INFO") == "/healthz/":
        body = b"ok"
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]
    return _django_application(environ, start_response)
