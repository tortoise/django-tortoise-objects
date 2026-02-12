"""
Settings loading from Django's ``TORTOISE_OBJECTS`` configuration.

Provides ``get_config()`` which merges user-supplied settings with sensible
defaults. The ``TORTOISE_OBJECTS`` dict in Django settings can override any
of the keys defined in ``DEFAULTS``.

Also provides ``should_include()`` for model inclusion/exclusion filtering
based on fnmatch patterns.
"""

import fnmatch
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger("django_tortoise")

# Default configuration values
DEFAULTS: dict[str, Any] = {
    "INCLUDE_MODELS": None,  # None means all models are included
    "EXCLUDE_MODELS": None,  # None means no models are excluded
    "DB_ENGINE_MAP": {},  # Custom DB engine -> Tortoise backend overrides
    "CONNECTION_POOL": {},  # Connection pool configuration overrides
    "LOG_LEVEL": "WARNING",  # Logging level for django_tortoise logger
}


def get_config() -> dict[str, Any]:
    """
    Load TORTOISE_OBJECTS from Django settings, merged with defaults.

    User-supplied keys in ``settings.TORTOISE_OBJECTS`` override the
    corresponding keys in ``DEFAULTS``. Keys not present in the user
    config fall back to their default values.

    Returns:
        A dict containing the merged configuration.
    """
    user_config: dict[str, Any] = getattr(settings, "TORTOISE_OBJECTS", {})
    config = {**DEFAULTS, **user_config}
    return config


def should_include(
    label: str,
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
) -> bool:
    """
    Check if a model label matches include/exclude patterns.

    EXCLUDE takes precedence over INCLUDE.

    Args:
        label: Model label in ``"app_label.ModelName"`` format.
        include_patterns: List of fnmatch patterns for models to include.
            ``None`` means include all.
        exclude_patterns: List of fnmatch patterns for models to exclude.
            ``None`` means exclude none.

    Returns:
        True if the model should be included.
    """
    # If excluded, always skip
    if exclude_patterns is not None:
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(label, pattern):
                return False

    # If include is specified (including empty list), model must match at least one pattern
    if include_patterns is not None:
        return any(fnmatch.fnmatch(label, pattern) for pattern in include_patterns)

    # No include specified (None) = include all
    return True
