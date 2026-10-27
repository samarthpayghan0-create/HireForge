# What was verified (and what was not)

Run on 2026-10-27, Python 3.12, Django 6.1.2.

| Check | Result |
|---|---|
| `manage.py check`, `makemigrations --check` | clean |
| Test suite: Member 2 (15) + Member 3 (17) + Member 4 (33) + integration (11) | **76 / 76 on SQLite** |
| Same suite on **PostgreSQL 16** (27 migrations applied) | **76 / 76** |
| Same suite on **MariaDB 10.11** (MySQL-compatible) | **76 / 76** |
| Production configuration (`VERCEL=1`, DEBUG off) via the real `api/index.py` entry point + CDN-first routing, `scripts/smoke_test.py` on PostgreSQL and on MariaDB | **22 passed, 2 skipped (Gemini), 0 failed** |
| Browser-level journey with jsdom over the real pages: login form, dashboard + new navigation, logout, assessments (auto-connect, start), interview (auto-token, start, role used), resume (upload, analysis), logged-out state, no JS errors | **16 / 16** |
| Missing `DJANGO_SECRET_KEY` / `DATABASE_URL` in production | fails immediately with a clear message |
| Dependency bundle size | 154 MB uncompressed (Vercel limit 250 MB) |

## Not verified — do these yourself
* **The actual Vercel deployment and the GitHub push** (no access from the build environment). `scripts/smoke_test.py`
  is the check to run against the live URL. The one platform behaviour I could only simulate is the catch-all rewrite
  in `vercel.json`; if `/api/health/` fails on Vercel, start with the *Troubleshooting* table.
* **Real Gemini calls** (no API key here): Member 1's readiness assessment, interview answer evaluation, resume AI review.
  They are tested with mocks and fail gracefully, but need a live check with your key.
* **Managed MySQL with TLS**, real MySQL 8 (MariaDB was used), real browsers/visual layout.
