"""
Tests for the django_tortoise.exceptions module.

Validates that all custom exceptions are defined, importable, and form the
correct inheritance hierarchy under ``DjangoTortoiseError``.
"""

from django_tortoise.exceptions import (
    ConfigurationError,
    ConnectionError,
    DjangoTortoiseError,
    UnsupportedBackendError,
    UnsupportedFieldError,
)


class TestExceptionHierarchy:
    """All custom exceptions inherit from DjangoTortoiseError."""

    def test_connection_error_is_subclass(self) -> None:
        assert issubclass(ConnectionError, DjangoTortoiseError)

    def test_configuration_error_is_subclass(self) -> None:
        assert issubclass(ConfigurationError, DjangoTortoiseError)

    def test_unsupported_field_error_is_subclass(self) -> None:
        assert issubclass(UnsupportedFieldError, DjangoTortoiseError)

    def test_unsupported_backend_error_is_subclass(self) -> None:
        assert issubclass(UnsupportedBackendError, DjangoTortoiseError)

    def test_base_is_exception(self) -> None:
        assert issubclass(DjangoTortoiseError, Exception)


class TestExceptionsRaisable:
    """Custom exceptions can be raised and caught."""

    def test_raise_connection_error(self) -> None:
        try:
            raise ConnectionError("connection failed")
        except DjangoTortoiseError as exc:
            assert str(exc) == "connection failed"

    def test_raise_configuration_error(self) -> None:
        try:
            raise ConfigurationError("bad config")
        except DjangoTortoiseError as exc:
            assert str(exc) == "bad config"

    def test_raise_unsupported_field_error(self) -> None:
        try:
            raise UnsupportedFieldError("unknown field")
        except DjangoTortoiseError as exc:
            assert str(exc) == "unknown field"

    def test_raise_unsupported_backend_error(self) -> None:
        try:
            raise UnsupportedBackendError("unknown backend")
        except DjangoTortoiseError as exc:
            assert str(exc) == "unknown backend"
