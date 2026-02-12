"""
Tests for django_tortoise.db_config -- Database configuration translation.

Verifies that Django ``DATABASES`` settings are correctly translated into
Tortoise ORM configuration format for all supported backends.
"""

from unittest.mock import patch

import pytest

from django_tortoise.db_config import _build_credentials, build_tortoise_config
from django_tortoise.exceptions import UnsupportedBackendError


class TestSqliteConfig:
    """Tests for SQLite backend configuration."""

    def test_sqlite_config(self):
        """SQLite Django config translates correctly."""
        config = build_tortoise_config()
        conn = config["connections"]["default"]
        assert conn["engine"] == "tortoise.backends.sqlite"
        assert "file_path" in conn["credentials"]

    def test_sqlite_memory(self):
        """SQLite :memory: is passed through as file_path."""
        creds = _build_credentials("django.db.backends.sqlite3", {"NAME": ":memory:"})
        assert creds["file_path"] == ":memory:"

    def test_sqlite_file_path(self):
        """SQLite file path is passed through."""
        creds = _build_credentials("django.db.backends.sqlite3", {"NAME": "/tmp/test.db"})
        assert creds["file_path"] == "/tmp/test.db"


class TestPostgresqlConfig:
    """Tests for PostgreSQL backend configuration."""

    def test_postgresql_credentials(self):
        creds = _build_credentials(
            "django.db.backends.postgresql",
            {
                "HOST": "db.example.com",
                "PORT": "5433",
                "USER": "myuser",
                "PASSWORD": "mypass",
                "NAME": "mydb",
            },
        )
        assert creds["host"] == "db.example.com"
        assert creds["port"] == 5433
        assert creds["user"] == "myuser"
        assert creds["password"] == "mypass"
        assert creds["database"] == "mydb"

    def test_postgresql_default_port(self):
        """PostgreSQL defaults to port 5432 when not specified."""
        creds = _build_credentials("django.db.backends.postgresql", {"NAME": "mydb"})
        assert creds["port"] == 5432

    def test_postgresql_default_host(self):
        """PostgreSQL defaults to localhost when HOST not specified."""
        creds = _build_credentials("django.db.backends.postgresql", {"NAME": "mydb"})
        assert creds["host"] == "localhost"


class TestMysqlConfig:
    """Tests for MySQL backend configuration."""

    def test_mysql_credentials(self):
        creds = _build_credentials(
            "django.db.backends.mysql",
            {
                "HOST": "mysql.example.com",
                "PORT": "3307",
                "USER": "root",
                "PASSWORD": "secret",
                "NAME": "app_db",
            },
        )
        assert creds["host"] == "mysql.example.com"
        assert creds["port"] == 3307
        assert creds["user"] == "root"
        assert creds["password"] == "secret"
        assert creds["database"] == "app_db"

    def test_mysql_default_port(self):
        """MySQL defaults to port 3306 when not specified."""
        creds = _build_credentials("django.db.backends.mysql", {"NAME": "mydb"})
        assert creds["port"] == 3306


class TestUnsupportedBackend:
    """Tests for unsupported database backends."""

    def test_unsupported_backend_raises(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {"ENGINE": "django.db.backends.oracle", "NAME": "orcl"}
            }
            mock_settings.USE_TZ = False
            mock_settings.TIME_ZONE = "UTC"
            with (
                patch(
                    "django_tortoise.db_config.get_config",
                    return_value={"DB_ENGINE_MAP": {}, "CONNECTION_POOL": {}},
                ),
                pytest.raises(UnsupportedBackendError, match="oracle"),
            ):
                build_tortoise_config()


class TestMultiDatabase:
    """Tests for multi-database configurations."""

    def test_multi_database(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
                "secondary": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/tmp/secondary.db"},
            }
            mock_settings.USE_TZ = True
            mock_settings.TIME_ZONE = "UTC"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={"DB_ENGINE_MAP": {}, "CONNECTION_POOL": {}},
            ):
                config = build_tortoise_config()
                assert "default" in config["connections"]
                assert "secondary" in config["connections"]
                assert (
                    config["connections"]["secondary"]["credentials"]["file_path"]
                    == "/tmp/secondary.db"
                )


class TestConnectionPoolOverrides:
    """Tests for connection pool configuration overrides."""

    def test_connection_pool_overrides(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            }
            mock_settings.USE_TZ = False
            mock_settings.TIME_ZONE = "UTC"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={
                    "DB_ENGINE_MAP": {},
                    "CONNECTION_POOL": {"default": {"minsize": 5, "maxsize": 20}},
                },
            ):
                config = build_tortoise_config()
                creds = config["connections"]["default"]["credentials"]
                assert creds["minsize"] == 5
                assert creds["maxsize"] == 20


class TestEngineMapOverride:
    """Tests for custom engine map overrides."""

    def test_engine_map_override(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {
                    "ENGINE": "custom.pg.backend",
                    "NAME": "mydb",
                    "HOST": "localhost",
                    "PORT": "5432",
                    "USER": "u",
                    "PASSWORD": "p",
                },
            }
            mock_settings.USE_TZ = False
            mock_settings.TIME_ZONE = "UTC"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={
                    "DB_ENGINE_MAP": {"custom.pg.backend": "tortoise.backends.psycopg"},
                    "CONNECTION_POOL": {},
                },
            ):
                config = build_tortoise_config()
                assert config["connections"]["default"]["engine"] == "tortoise.backends.psycopg"


class TestConfigStructure:
    """Tests for the overall config structure."""

    def test_config_includes_app(self):
        config = build_tortoise_config()
        assert "django_tortoise" in config["apps"]
        assert config["apps"]["django_tortoise"]["models"] == ["django_tortoise._models"]

    def test_config_includes_use_tz(self):
        config = build_tortoise_config()
        assert config["use_tz"] is True  # Our test settings have USE_TZ = True

    def test_config_includes_timezone(self):
        config = build_tortoise_config()
        assert "timezone" in config

    def test_config_default_connection(self):
        config = build_tortoise_config()
        assert config["apps"]["django_tortoise"]["default_connection"] == "default"
