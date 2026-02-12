"""
Minimal Django settings for the django-tortoise-objects test suite.

Uses a file-based SQLite database so that both Django and Tortoise ORM
can connect to the same database during integration tests.
"""

import os
import tempfile

SECRET_KEY = "test-secret-key-for-django-tortoise-objects"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_tortoise",
    "tests.testapp",
]

# Use a file-based SQLite database. This is essential for integration tests
# because Tortoise ORM opens its own connection, and :memory: databases
# are per-connection in SQLite.
_DB_PATH = os.path.join(tempfile.gettempdir(), "django_tortoise_test.sqlite3")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _DB_PATH,
        "TEST": {
            "NAME": _DB_PATH,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
