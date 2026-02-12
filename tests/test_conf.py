"""
Tests for the django_tortoise.conf module.

Validates that ``get_config()`` returns correct defaults and properly merges
user-supplied settings from ``settings.TORTOISE_OBJECTS``.
"""

from unittest.mock import patch

from django_tortoise.conf import DEFAULTS, get_config


class TestDefaultConfig:
    """get_config() returns defaults when TORTOISE_OBJECTS is not set."""

    def test_returns_all_default_keys(self) -> None:
        config = get_config()
        for key in DEFAULTS:
            assert key in config

    def test_include_models_default_is_none(self) -> None:
        config = get_config()
        assert config["INCLUDE_MODELS"] is None

    def test_exclude_models_default_is_none(self) -> None:
        config = get_config()
        assert config["EXCLUDE_MODELS"] is None

    def test_db_engine_map_default_is_empty_dict(self) -> None:
        config = get_config()
        assert config["DB_ENGINE_MAP"] == {}

    def test_connection_pool_default_is_empty_dict(self) -> None:
        config = get_config()
        assert config["CONNECTION_POOL"] == {}

    def test_log_level_default_is_warning(self) -> None:
        config = get_config()
        assert config["LOG_LEVEL"] == "WARNING"


class TestCustomConfig:
    """get_config() merges user settings with defaults."""

    def test_user_override_replaces_default(self) -> None:
        user_settings = {"TORTOISE_OBJECTS": {"LOG_LEVEL": "DEBUG"}}
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = user_settings["TORTOISE_OBJECTS"]
            config = get_config()
        assert config["LOG_LEVEL"] == "DEBUG"

    def test_user_override_preserves_other_defaults(self) -> None:
        user_settings = {"TORTOISE_OBJECTS": {"LOG_LEVEL": "DEBUG"}}
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = user_settings["TORTOISE_OBJECTS"]
            config = get_config()
        # Other defaults should still be present
        assert config["INCLUDE_MODELS"] is None
        assert config["EXCLUDE_MODELS"] is None
        assert config["DB_ENGINE_MAP"] == {}
        assert config["CONNECTION_POOL"] == {}

    def test_include_models_override(self) -> None:
        user_settings = {
            "TORTOISE_OBJECTS": {
                "INCLUDE_MODELS": ["myapp.MyModel"],
            }
        }
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = user_settings["TORTOISE_OBJECTS"]
            config = get_config()
        assert config["INCLUDE_MODELS"] == ["myapp.MyModel"]

    def test_exclude_models_override(self) -> None:
        user_settings = {
            "TORTOISE_OBJECTS": {
                "EXCLUDE_MODELS": ["myapp.SkipMe"],
            }
        }
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = user_settings["TORTOISE_OBJECTS"]
            config = get_config()
        assert config["EXCLUDE_MODELS"] == ["myapp.SkipMe"]

    def test_no_tortoise_objects_setting(self) -> None:
        """When TORTOISE_OBJECTS is absent, defaults are returned."""
        with patch("django_tortoise.conf.settings", spec=[]):
            # spec=[] means the mock has no attributes at all,
            # so getattr(settings, "TORTOISE_OBJECTS", {}) returns {}
            config = get_config()
        assert config == DEFAULTS

    def test_extra_keys_are_preserved(self) -> None:
        """User-supplied keys not in DEFAULTS are preserved in the output."""
        user_settings = {
            "TORTOISE_OBJECTS": {
                "CUSTOM_SETTING": "custom_value",
            }
        }
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = user_settings["TORTOISE_OBJECTS"]
            config = get_config()
        assert config["CUSTOM_SETTING"] == "custom_value"
