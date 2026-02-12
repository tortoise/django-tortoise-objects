"""
Placeholder tests to verify the test infrastructure is working correctly.

These tests validate that Django is properly configured and that the
django_tortoise package is importable with the expected public API.
"""


def test_django_setup():
    """Verify that Django settings are loaded and django_tortoise is installed."""
    from django.conf import settings

    assert "django_tortoise" in settings.INSTALLED_APPS


def test_import():
    """Verify that django_tortoise exposes the expected public API."""
    import django_tortoise

    assert hasattr(django_tortoise, "init")
    assert hasattr(django_tortoise, "close")
    assert hasattr(django_tortoise, "get_tortoise_model")
