"""Gunicorn configuration for the independent ParsPack deployment.

ParsPack's Django runtime expects the application to listen on port 8000.
Render continues to use its existing $PORT-based command and does not load
this file.
"""

import os

bind = "0.0.0.0:8000"
workers = max(1, int(os.environ.get("WEB_CONCURRENCY", "2")))
timeout = 120
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
capture_output = True
