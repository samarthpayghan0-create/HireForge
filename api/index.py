
import os
import sys
from urllib.parse import parse_qsl, urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")

if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application


def app(environ, start_response):
    query = parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    original_path = None
    remaining_query = []

    for key, value in query:
        if key == "original_path" and original_path is None:
            original_path = value
        else:
            remaining_query.append((key, value))

    if original_path and original_path.startswith("/"):
        environ["PATH_INFO"] = original_path
        environ["QUERY_STRING"] = urlencode(remaining_query)

    return application(environ, start_response)
