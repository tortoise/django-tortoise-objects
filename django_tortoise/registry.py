"""
Central registry of Django-to-Tortoise model mappings.

Maintains a bidirectional mapping between Django model classes and their
dynamically generated Tortoise ORM counterparts.  Provides lookup by
Django model class, Tortoise model class, or ``"app_label.ModelName"``
label string.

A module-level ``model_registry`` singleton is the single source of truth.
The public ``get_tortoise_model()`` function is a convenience wrapper
re-exported by ``django_tortoise.__init__``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tortoise.models import Model as TortoiseModel

logger = logging.getLogger("django_tortoise")


class ModelRegistry:
    """Central registry mapping Django models to Tortoise models."""

    def __init__(self) -> None:
        self._django_to_tortoise: dict[type, type[TortoiseModel]] = {}
        self._tortoise_to_django: dict[type[TortoiseModel], type] = {}
        self._by_label: dict[str, type[TortoiseModel]] = {}  # "app_label.ModelName" -> Tortoise
        self._tortoise_models: list[type[TortoiseModel]] = []

    def register(
        self,
        django_model: type,
        tortoise_model: type[TortoiseModel],
        label: str,
    ) -> None:
        """Register a Django <-> Tortoise model pair."""
        self._django_to_tortoise[django_model] = tortoise_model
        self._tortoise_to_django[tortoise_model] = django_model
        self._by_label[label] = tortoise_model
        self._tortoise_models.append(tortoise_model)
        logger.debug("Registered: %s -> %s", label, tortoise_model.__name__)

    def get_tortoise_model(self, django_model: type) -> type[TortoiseModel] | None:
        """Get the Tortoise model for a Django model."""
        return self._django_to_tortoise.get(django_model)

    def get_django_model(self, tortoise_model: type[TortoiseModel]) -> type | None:
        """Get the Django model for a Tortoise model."""
        return self._tortoise_to_django.get(tortoise_model)

    def get_by_label(self, label: str) -> type[TortoiseModel] | None:
        """Get Tortoise model by ``'app_label.ModelName'`` string."""
        return self._by_label.get(label)

    def get_all_tortoise_models(self) -> list[type[TortoiseModel]]:
        """Get all registered Tortoise models."""
        return list(self._tortoise_models)

    def get_all_mappings(self) -> dict[type, type[TortoiseModel]]:
        """Return a copy of the full Django -> Tortoise model registry."""
        return dict(self._django_to_tortoise)

    def is_registered(self, django_model: type) -> bool:
        """Check if a Django model has a Tortoise counterpart."""
        return django_model in self._django_to_tortoise

    def clear(self) -> None:
        """Clear all registrations. Primarily used in testing."""
        self._django_to_tortoise.clear()
        self._tortoise_to_django.clear()
        self._by_label.clear()
        self._tortoise_models.clear()


# Global singleton instance
model_registry = ModelRegistry()


# ---------------------------------------------------------------------------
# Public convenience functions (re-exported by django_tortoise.__init__)
# ---------------------------------------------------------------------------


def register_model(
    django_model: type,
    tortoise_model: type[TortoiseModel],
    label: str | None = None,
) -> None:
    """
    Register a Django -> Tortoise model mapping.

    If *label* is not provided, it is derived from the Django model's
    ``_meta.app_label`` and class name.
    """
    if label is None:
        try:
            label = f"{django_model._meta.app_label}.{django_model.__name__}"  # type: ignore[attr-defined]
        except AttributeError:
            label = django_model.__name__
    model_registry.register(django_model, tortoise_model, label)


def get_tortoise_model(django_model: type) -> type[TortoiseModel] | None:
    """
    Retrieve the Tortoise ORM model class generated for the given Django model.

    Returns ``None`` if no mapping has been registered for this model.
    """
    return model_registry.get_tortoise_model(django_model)


def get_all_mappings() -> dict[type, type[TortoiseModel]]:
    """Return a copy of the full Django -> Tortoise model registry."""
    return model_registry.get_all_mappings()


def clear_registry() -> None:
    """Clear all registered mappings. Primarily used in testing."""
    model_registry.clear()
