"""
Tests for multi-database support (Phase 5, Step 5.2).

Verifies that multiple database aliases and mixed backends produce
correct Tortoise configuration.
"""

from unittest.mock import patch

from django_tortoise.db_config import build_tortoise_config


class TestMultiDbConfig:
    """Tests for multi-database configuration translation."""

    def test_two_sqlite_databases(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                },
                "analytics": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "/tmp/analytics.db",
                },
            }
            mock_settings.USE_TZ = True
            mock_settings.TIME_ZONE = "UTC"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={"DB_ENGINE_MAP": {}, "CONNECTION_POOL": {}},
            ):
                config = build_tortoise_config()
                assert "default" in config["connections"]
                assert "analytics" in config["connections"]
                assert (
                    config["connections"]["analytics"]["credentials"]["file_path"]
                    == "/tmp/analytics.db"
                )

    def test_mixed_backends(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": "mydb",
                    "HOST": "localhost",
                    "PORT": "5432",
                    "USER": "user",
                    "PASSWORD": "pass",
                },
                "cache_db": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "/tmp/cache.db",
                },
            }
            mock_settings.USE_TZ = False
            mock_settings.TIME_ZONE = "UTC"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={"DB_ENGINE_MAP": {}, "CONNECTION_POOL": {}},
            ):
                config = build_tortoise_config()
                assert config["connections"]["default"]["engine"] == "tortoise.backends.psycopg"
                assert config["connections"]["cache_db"]["engine"] == "tortoise.backends.sqlite"

    def test_three_databases(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                },
                "read_replica": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "/tmp/replica.db",
                },
                "warehouse": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "/tmp/warehouse.db",
                },
            }
            mock_settings.USE_TZ = True
            mock_settings.TIME_ZONE = "America/New_York"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={"DB_ENGINE_MAP": {}, "CONNECTION_POOL": {}},
            ):
                config = build_tortoise_config()
                assert len(config["connections"]) == 3
                assert config["timezone"] == "America/New_York"
                assert config["use_tz"] is True

    def test_per_alias_pool_config(self):
        with patch("django_tortoise.db_config.settings") as mock_settings:
            mock_settings.DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                },
                "secondary": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "/tmp/secondary.db",
                },
            }
            mock_settings.USE_TZ = False
            mock_settings.TIME_ZONE = "UTC"
            with patch(
                "django_tortoise.db_config.get_config",
                return_value={
                    "DB_ENGINE_MAP": {},
                    "CONNECTION_POOL": {
                        "default": {"minsize": 2, "maxsize": 10},
                        "secondary": {"minsize": 1, "maxsize": 5},
                    },
                },
            ):
                config = build_tortoise_config()
                default_creds = config["connections"]["default"]["credentials"]
                secondary_creds = config["connections"]["secondary"]["credentials"]
                assert default_creds["minsize"] == 2
                assert default_creds["maxsize"] == 10
                assert secondary_creds["minsize"] == 1
                assert secondary_creds["maxsize"] == 5
