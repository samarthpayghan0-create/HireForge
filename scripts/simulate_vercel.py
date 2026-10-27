#!/usr/bin/env python3
"""Run HireForge the way Vercel does, on your own machine.

Static files from /public are served first (like Vercel's CDN); every other request
is rewritten to the Django WSGI app exposed by api/index.py.

    DATABASE_URL=... DJANGO_SECRET_KEY=... VERCEL=1 python scripts/simulate_vercel.py 8001
    python scripts/smoke_test.py http://127.0.0.1:8001
"""

import mimetypes
import os
import sys
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
sys.path.insert(0, str(ROOT / "api"))
from index import app as django_app  # noqa: E402  (the real Vercel entry point)


def resolve_static(path):
    candidate = (PUBLIC / path.lstrip("/")).resolve()
    if PUBLIC.resolve() not in candidate.parents and candidate != PUBLIC.resolve():
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate if candidate.is_file() else None


def application(environ, start_response):
    if environ["REQUEST_METHOD"] in ("GET", "HEAD"):
        file = resolve_static(environ.get("PATH_INFO", "/"))
        if file:
            body = file.read_bytes()
            ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            start_response("200 OK", [("Content-Type", ctype), ("Content-Length", str(len(body)))])
            return [body]
    return django_app(environ, start_response)  # rewrite -> /api/index


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"Simulated Vercel on http://127.0.0.1:{port}  (VERCEL={os.getenv('VERCEL')!r})")
    make_server("127.0.0.1", port, application, handler_class=Quiet).serve_forever()
