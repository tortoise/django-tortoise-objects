"""
ASGI config for example_project.

Includes Tortoise ORM lifecycle management via lifespan events.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

application = get_asgi_application()
