"""
Django settings for the example_project.

Supports both SQLite and PostgreSQL backends.
Set DATABASE_URL=postgres://user:pass@host:port/dbname to use PostgreSQL,
or leave unset for the default SQLite backend.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-project-secret-key-not-for-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_tortoise",
    "demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "example_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "example_project.asgi.application"

# --- Database -----------------------------------------------------------------
# Set DATABASE_URL to switch backends:
#   SQLite (default): unset or sqlite:///path/to/db.sqlite3
#   PostgreSQL:       postgres://user:pass@host:port/dbname
_DATABASE_URL = os.environ.get("DATABASE_URL", "")

if _DATABASE_URL.startswith("postgres"):
    # Parse: postgres://user:pass@host:port/dbname
    from urllib.parse import urlparse
    _parsed = urlparse(_DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _parsed.path.lstrip("/"),
            "USER": _parsed.username or "bench",
            "PASSWORD": _parsed.password or "bench",
            "HOST": _parsed.hostname or "localhost",
            "PORT": str(_parsed.port or 5432),
        }
    }
else:
    # File-based SQLite: essential so Tortoise ORM (which opens its own connection)
    # sees the same data as Django's ORM.
    # Use /tmp for SQLite to avoid overlay filesystem SIGBUS issues in Docker.
    _DB_DIR = "/tmp" if os.access("/tmp", os.W_OK) else str(BASE_DIR)
    _DB_PATH = os.path.join(_DB_DIR, "example_project_db.sqlite3")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _DB_PATH,
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

STATIC_URL = "static/"

# --- django-tortoise-objects configuration ------------------------------------
_TORTOISE_PG_ENGINE = os.environ.get("TORTOISE_PG_ENGINE", "tortoise.backends.psycopg")
TORTOISE_OBJECTS = {
    "INCLUDE_MODELS": [
        "demo.*",
    ],
    "DB_ENGINE_MAP": {
        "django.db.backends.postgresql": _TORTOISE_PG_ENGINE,
    },
}
