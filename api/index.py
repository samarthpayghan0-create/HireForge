"""Vercel serverless entry point: exposes the Django WSGI application.

Vercel serves everything in /public from its CDN and rewrites every other
request (/api/*, /admin/*, /interview/, /static/*) to this function
(see vercel.json).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application  # noqa: E402

app = application  # Vercel looks for a WSGI callable named `app`
