"""Gunicorn configuration for production (WSGI).

Run from the project directory:
    gunicorn -c gunicorn.conf.py
"""

import multiprocessing

wsgi_app = "config.wsgi:application"

# Bind to the port expected by nginx / reverse proxy. Override with
# `gunicorn -b 127.0.0.1:8001 -c gunicorn.conf.py` if you proxy from elsewhere.
bind = "0.0.0.0:8000"

# Classic nginx-style worker count heuristic for CPU-bound Django.
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

timeout = 120
graceful_timeout = 30
keepalive = 5

# Log to stdout/stderr so Docker/systemd/journald can collect the logs.
accesslog = "-"
errorlog = "-"
capture_output = True