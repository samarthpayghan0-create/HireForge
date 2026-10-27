"""
Django settings for the unified HireForge project
(Member 1 dashboard + Member 2 assessments + Member 3 mock interviews + Member 4 resume).

Everything environment-specific comes from environment variables (see
`.env.example`). Locally a `.env` file in the repository root is loaded
automatically. On Vercel, set the same variables in Project Settings.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent          # .../backend
REPO_ROOT = BASE_DIR.parent
PUBLIC_DIR = REPO_ROOT / "public"                          # static frontend pages

if load_dotenv:
    # Does not override variables that are already set (e.g. by Vercel / CI).
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name):
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


ON_VERCEL = bool(os.getenv("VERCEL"))

# --- Core / security ----------------------------------------------------

DEBUG = env_bool("DJANGO_DEBUG", default=not ON_VERCEL)

_DEV_SECRET_KEY = "django-insecure-dev-only-change-me"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = _DEV_SECRET_KEY
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is not set. Generate one with: "
            "python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\""
        )

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver", ".vercel.app"] + env_list("DJANGO_ALLOWED_HOSTS")
for _name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
    if os.getenv(_name):
        ALLOWED_HOSTS.append(os.environ[_name])

CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"] + env_list("CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- Applications -------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "dashboard",          # Member 1: auth, profile, AI readiness
    "assessments",        # Member 2: question bank
    "assessments_api",    # Member 2: assessment API
    "mock_interviews",    # Member 3: AI mock interviews
    "resume_career",      # Member 4: resume analysis & career development
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database -----------------------------------------------------------
# 1) DATABASE_URL (recommended; Vercel + hosted DB):
#      postgres://user:pass@host/db?sslmode=require     mysql://user:pass@host:3306/db
# 2) Otherwise, locally: SQLite (zero setup).
# SQLite cannot be used on Vercel (read-only, non-persistent file system).

DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=0)}
    _engine = DATABASES["default"]["ENGINE"]
    if "postgresql" in _engine:
        # Needed for pooled connections (Neon/Supabase pgbouncer, transaction mode).
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    if "mysql" in _engine:
        DATABASES["default"].setdefault("OPTIONS", {}).setdefault("charset", "utf8mb4")
elif ON_VERCEL:
    raise ImproperlyConfigured(
        "DATABASE_URL is not set. Vercel needs a hosted database "
        "(for example Neon PostgreSQL or a MySQL provider). See DEPLOY.md."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Static files (Django admin / DRF browsable API) ---------------------
# WhiteNoise serves them straight from the installed apps, so no
# `collectstatic` build step is needed on Vercel.

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True

# --- REST framework / CORS ----------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# On Vercel the pages and the API share one origin, so CORS is only needed
# when the frontend is opened from another origin (e.g. VS Code Live Server).
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
] + env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "x-requested-with",
    "x-member1-token",
]

# Serve the static frontend (public/) from Django when running locally.
SERVE_FRONTEND = env_bool("SERVE_FRONTEND", default=DEBUG)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- Gemini (optional; AI features degrade gracefully without a key) ------
# Member 1 reads GEMINI_API_KEY from the environment directly; Members 3 and 4
# use the settings below.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# --- Logging (Vercel captures stdout/stderr) -----------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
