"""
Custom exceptions for django-tortoise-objects.

All exceptions inherit from ``DjangoTortoiseError`` to allow callers to
catch library-specific errors with a single base class.
"""


class DjangoTortoiseError(Exception):
    """Base exception for django-tortoise-objects."""


class ConnectionError(DjangoTortoiseError):
    """Raised when Tortoise DB connection fails during lazy init."""


class ConfigurationError(DjangoTortoiseError):
    """Raised for invalid configuration in TORTOISE_OBJECTS settings."""


class UnsupportedFieldError(DjangoTortoiseError):
    """Raised/logged when a Django field type has no Tortoise mapping."""


class UnsupportedBackendError(DjangoTortoiseError):
    """Raised when Django DB backend has no Tortoise equivalent."""
