"""
pytest-django configuration for the django-tortoise-objects test suite.

Sets DJANGO_SETTINGS_MODULE and calls django.setup() before tests run.
"""

import os

import django


def pytest_configure(config):
    """Configure Django settings for the test run."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_settings")
    django.setup()
