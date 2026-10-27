# HireForge

AI-assisted career preparation for students: profile + AI readiness assessment, skill assessments,
AI mock interviews and resume analysis — one Django backend and one static frontend, deployable to Vercel.

| Module | Owner | Frontend | API |
|---|---|---|---|
| Accounts, profile, AI readiness | Member 1 | `public/*.html`, `public/script.js` | `/api/register/ login/ profile/ assessment/` |
| Skill assessments (800 questions) | Member 2 | `public/assessments/` | `/api/assessments/…` |
| AI mock interview | Member 3 | `backend/mock_interviews/templates/` → `/interview/` | `/api/interviews/…` |
| Resume analysis & careers | Member 4 | `public/resume/` | `/api/resume/…` |
| Health check | – | – | `/api/health/` |

One login (Member 1) gives one token that works for every module (`localStorage["hireforgeToken"]`).

```
HireForge/
├── api/index.py            Vercel serverless entry point (exposes Django WSGI)
├── backend/                Django project: config/, dashboard/, assessments*/, mock_interviews/, resume_career/
│   └── integration_tests/  cross-module tests
├── public/                 static frontend (served by Vercel's CDN, or by Django locally)
├── scripts/                smoke_test.py (post-deploy check), simulate_vercel.py (local production run)
├── vercel.json  requirements.txt  .python-version  .env.example
└── DEPLOY.md               GitHub + Vercel + database step by step
```

## Run locally (2 minutes, no database setup)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # optional: add GEMINI_API_KEY
cd backend
python manage.py migrate
python manage.py runserver                             # http://127.0.0.1:8000  (pages + API on one origin)
```
Open http://127.0.0.1:8000, sign up, then use the dashboard cards. To use MySQL/PostgreSQL locally, set
`DATABASE_URL` in `.env` (see `.env.example`). Without `GEMINI_API_KEY` everything works except the AI-only
parts (readiness assessment, interview answer evaluation, optional resume AI review); interview questions fall back
to built-in ones and resume analysis stays rule-based.

## Test
```bash
cd backend
python manage.py check && python manage.py makemigrations --check --dry-run
python manage.py test                                   # 76 tests (also run against PostgreSQL in CI)
```
Test a *production-like* run (DEBUG off, Vercel entry point, CDN-first routing) and the smoke test:
```bash
VERCEL=1 DJANGO_SECRET_KEY=any-long-random DATABASE_URL=postgres://... python scripts/simulate_vercel.py 8001
python scripts/smoke_test.py http://127.0.0.1:8001
```

## Deploy
See **[DEPLOY.md](DEPLOY.md)**. Short version: push to GitHub → import in Vercel → set `DJANGO_SECRET_KEY` and
`DATABASE_URL` → run `migrate` once against that database → `python scripts/smoke_test.py https://<your-app>.vercel.app`.

## Known limitations
* "Forgot password" is a UI placeholder (Member 1; no email service is configured).
* No rate limiting yet: add it before opening the AI endpoints to the public (Gemini usage is billed to your key).
* Uploaded resumes are limited to 4 MB (Vercel rejects request bodies over 4.5 MB). Scanned PDFs are rejected (no OCR).
* Auth tokens live in `localStorage` and do not expire (Member 1's design).
