# Deploying HireForge to GitHub + Vercel

Vercel hosts the static pages (`public/`) on its CDN and runs Django as one serverless function
(`api/index.py`). Because serverless functions have no persistent disk, **you need a hosted database**
— SQLite and a local MySQL will not work.

## 1. Create the database (pick one)
**PostgreSQL – simplest (recommended):** in the Vercel dashboard → *Storage* → *Create* → **Neon** (or use
neon.com / Supabase directly). Copy the *pooled* connection string, e.g.
`postgres://USER:PASSWORD@ep-xxxx-pooler.region.aws.neon.tech/neondb?sslmode=require`.

**MySQL (your original plan):** supported (tests and smoke test pass on MariaDB 10.11), but I could not test a
managed MySQL that *requires TLS*. Such providers (PlanetScale, TiDB Cloud, Aiven …) may need extra SSL options in
`DATABASES["default"]["OPTIONS"]`; use PostgreSQL if you want zero friction.

## 2. Push to GitHub
```bash
cd HireForge
git init -b main
git add .
git status        # check: no .env, no db.sqlite3, no .venv  (.gitignore already excludes them)
git commit -m "feat: integrate HireForge members 1-4 into one deployable project"
# create an EMPTY repo named "hireforge" on github.com, then:
git remote add origin https://github.com/<your-username>/hireforge.git
git push -u origin main
```
The included GitHub Action (`.github/workflows/ci.yml`) runs the tests on SQLite and PostgreSQL on every push.

## 3. Import into Vercel
1. vercel.com → **Add New… → Project** → import the `hireforge` repository.
2. **Framework Preset: Other.** Leave *Root Directory* empty (repo root). Leave Build/Output/Install commands at their
   defaults (Vercel installs `requirements.txt` by itself; there is no build step).
3. **Environment Variables** (Production, and Preview if you use previews):

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | long random string: `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `DATABASE_URL` | the connection string from step 1 (auto-added if you used the Vercel Neon integration) |
| `GEMINI_API_KEY` | optional – enables the AI features (get one at aistudio.google.com) |
| `GEMINI_MODEL` | optional, default `gemini-3.5-flash-lite` |
| `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | only if you add a custom domain (`https://your-domain.com`) |

   Never put these in the repository or in front-end code. The app refuses to start in production without
   `DJANGO_SECRET_KEY` and `DATABASE_URL`, so a missing value shows up as an obvious error in the function logs.
4. Click **Deploy**.

## 4. Create the tables (once, and after every change to models)
Migrations do not run automatically on Vercel. Run them from your computer against the production database:
```bash
pip install -r requirements.txt
cd backend
DATABASE_URL="postgres://…your production string…" DJANGO_SECRET_KEY=temporary python manage.py migrate
DATABASE_URL="…" DJANGO_SECRET_KEY=temporary python manage.py createsuperuser   # optional, for /admin/
```
(PowerShell: `$env:DATABASE_URL="…"; $env:DJANGO_SECRET_KEY="temporary"; python manage.py migrate`.)

## 5. Verify the live site
```bash
python scripts/smoke_test.py https://<your-project>.vercel.app
```
It registers a throw-away user and exercises health, pages, login, profile, assessments, resume upload/analysis/match
and interviews with a single token. Expected: `0 failed`. With a `GEMINI_API_KEY` the two AI checks become `PASS`
instead of `SKIP`. Then open the site and click through: sign up → dashboard → each tool card.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `/api/health/` returns 500 or a Vercel error page | Open *Vercel → Deployments → Functions logs*. Usually `DJANGO_SECRET_KEY` / `DATABASE_URL` missing or wrong. |
| health says `"database": "error"` (503) | Wrong `DATABASE_URL`, DB paused, or IP/SSL restrictions. Use the *pooled* string and `?sslmode=require`. |
| `relation … does not exist` / `no such table` | Step 4 (migrate) was not run against *this* database. |
| `DisallowedHost` | Custom domain not in `DJANGO_ALLOWED_HOSTS`. |
| Admin login: "CSRF verification failed" | Add your domain to `CSRF_TRUSTED_ORIGINS` (`*.vercel.app` is already allowed). |
| Upload fails with 413 | File over ~4 MB (Vercel's request-body limit). |
| Interview / AI call times out | The function limit is 60 s (`vercel.json`); Gemini is normally faster. Check `GEMINI_API_KEY` and quota. |
| `/api/...` returns 404 HTML from Vercel | `vercel.json` rewrite missing from the deployed commit – confirm it is at the repository root. |

## Security checklist before sharing the URL
* **Rotate the database passwords that were hard-coded in the original Member 1 and Member 3 `settings.py` files**
  (they were shared in zip files) and make sure they never reach GitHub history.
* Keep `DJANGO_DEBUG` unset/`False` in production (it is `False` automatically on Vercel).
* Add rate limiting before making AI endpoints public (cost control).
