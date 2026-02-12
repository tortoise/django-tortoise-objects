"""
django-tortoise-objects: Bridge Django ORM models to Tortoise ORM for truly async database access.

This package provides automatic generation of Tortoise ORM model mirrors from
Django models, enabling async database access via the ``tortoise_objects``
descriptor on Django model classes.

Public API
----------
- ``init()``  -- Explicitly initialize Tortoise ORM connections.
- ``close()`` -- Shut down Tortoise ORM connections.
- ``get_tortoise_model()`` -- Retrieve the generated Tortoise model for a Django model.
"""

from django_tortoise.initialization import close, init
from django_tortoise.registry import get_tortoise_model

__all__ = ["close", "get_tortoise_model", "init"]
