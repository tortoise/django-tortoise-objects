"""
Database configuration translation.

Translates Django ``DATABASES`` settings into the Tortoise ORM configuration
format, mapping database backends and connection parameters.
"""

import logging
from typing import Any

from django.conf import settings

from django_tortoise.conf import get_config
from django_tortoise.exceptions import UnsupportedBackendError

logger = logging.getLogger("django_tortoise")

DEFAULT_ENGINE_MAP: dict[str, str] = {
    "django.db.backends.postgresql": "tortoise.backends.psycopg",
    "django.db.backends.mysql": "tortoise.backends.asyncmy",
    "django.db.backends.sqlite3": "tortoise.backends.sqlite",
}


def build_tortoise_config(tortoise_app_name: str = "django_tortoise") -> dict[str, Any]:
    """
    Build a complete Tortoise ORM config dict from Django settings.

    Reads ``settings.DATABASES`` and the ``TORTOISE_OBJECTS`` configuration
    to produce a dict suitable for passing to ``Tortoise.init(config=...)``.
    """
    config = get_config()
    user_engine_map: dict[str, str] = config.get("DB_ENGINE_MAP", {})
    pool_config: dict[str, dict[str, Any]] = config.get("CONNECTION_POOL", {})
    engine_map = {**DEFAULT_ENGINE_MAP, **user_engine_map}

    django_databases: dict[str, dict[str, Any]] = settings.DATABASES
    tortoise_connections: dict[str, dict[str, Any]] = {}

    for alias, db_conf in django_databases.items():
        engine = db_conf.get("ENGINE", "")
        tortoise_engine = engine_map.get(engine)

        if tortoise_engine is None:
            raise UnsupportedBackendError(
                f"Django database backend '{engine}' (alias '{alias}') "
                f"has no Tortoise ORM equivalent. Supported: {list(engine_map.keys())}"
            )

        credentials = _build_credentials(engine, db_conf)

        # Apply connection pool overrides
        alias_pool = pool_config.get(alias, {})
        if alias_pool:
            credentials.update(alias_pool)

        tortoise_connections[alias] = {
            "engine": tortoise_engine,
            "credentials": credentials,
        }

    tortoise_config: dict[str, Any] = {
        "connections": tortoise_connections,
        "apps": {
            tortoise_app_name: {
                "models": ["django_tortoise._models"],
                "default_connection": "default",
            }
        },
        "use_tz": getattr(settings, "USE_TZ", False),
        "timezone": getattr(settings, "TIME_ZONE", "UTC"),
    }

    return tortoise_config


def _build_credentials(engine: str, db_conf: dict[str, Any]) -> dict[str, Any]:
    """Build Tortoise credentials dict from a Django DB config entry."""
    if "sqlite" in engine:
        return {"file_path": db_conf.get("NAME", ":memory:")}

    # PostgreSQL and MySQL use the same credential keys
    credentials: dict[str, Any] = {
        "host": db_conf.get("HOST", "localhost"),
        "port": int(db_conf.get("PORT", 5432 if "postgresql" in engine else 3306)),
        "user": db_conf.get("USER", ""),
        "password": db_conf.get("PASSWORD", ""),
        "database": db_conf.get("NAME", ""),
    }

    return credentials
