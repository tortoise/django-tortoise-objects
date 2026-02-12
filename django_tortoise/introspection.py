"""
Django model introspection logic.

Extracts schema metadata from Django models using the ``_meta`` API,
producing ``ModelInfo`` and ``FieldInfo`` dataclasses consumed by the
Tortoise model generator.
"""

import enum
import logging
from dataclasses import dataclass
from typing import Any

from django.db import models

logger = logging.getLogger("django_tortoise")


@dataclass
class FieldInfo:
    """Extracted metadata for a single Django model field."""

    name: str
    internal_type: str  # from get_internal_type()
    column: str  # actual DB column name
    primary_key: bool
    null: bool
    unique: bool
    has_default: bool
    default: Any
    max_length: int | None
    max_digits: int | None
    decimal_places: int | None
    db_index: bool
    choices: list | None
    enum_type: type | None  # Python Enum class backing choices, if any
    # Relational field info
    is_relation: bool
    related_model: type | None  # Django model class
    related_model_label: str | None  # "app_label.ModelName"
    on_delete: str | None  # e.g. "CASCADE"
    related_name: str | None
    is_self_referential: bool
    # M2M specific
    many_to_many: bool
    through_model: type | None
    through_db_table: str | None
    # Auto field detection
    is_auto_field: bool
    # Original Django field reference
    django_field: models.Field | None


@dataclass
class ModelInfo:
    """Extracted metadata for a single Django model."""

    model_class: type
    app_label: str
    model_name: str
    db_table: str
    fields: list[FieldInfo]
    unique_together: list[tuple[str, ...]]
    is_abstract: bool
    is_proxy: bool
    is_managed: bool
    pk_name: str


def _detect_enum_type(django_field) -> type | None:
    """Detect a Python Enum class backing a Django field's choices.

    Django 6.0+ normalizes enum choices to plain ``(value, label)`` tuples
    via ``normalize_choices``, so the enum class cannot be recovered from
    ``field.choices`` alone.  Instead we check the field's default value:
    when an ``IntegerChoices`` / ``TextChoices`` default is set, Django
    preserves the enum member as the default.

    Returns the Enum subclass when found, otherwise None.
    """
    if not getattr(django_field, "choices", None):
        return None

    # The default value is an enum member when choices=SomeEnum was used
    if django_field.has_default():
        default = django_field.default
        if isinstance(default, enum.Enum):
            return type(default)

    return None


def introspect_field(django_field) -> FieldInfo | None:
    """
    Extract metadata from a single Django field.

    Returns None for reverse relations (fields where ``field.concrete`` is
    False and the field is not a forward ManyToManyField).
    """
    # Skip reverse relations: they are not concrete and not forward M2M
    is_m2m = getattr(django_field, "many_to_many", False)
    is_concrete = getattr(django_field, "concrete", False)

    if not is_concrete and not is_m2m:
        return None

    # For M2M fields, only include forward relations (not reverse).
    # Reverse M2M (ManyToManyRel) has a 'field' attribute pointing back.
    if is_m2m and not is_concrete and hasattr(django_field, "field"):
        return None

    name = django_field.name
    internal_type = django_field.get_internal_type()

    # Get DB column name. M2M fields don't have a column attribute.
    try:
        column = django_field.column or name
    except AttributeError:
        column = name

    primary_key = getattr(django_field, "primary_key", False)
    null = getattr(django_field, "null", False)
    unique = getattr(django_field, "unique", False)
    db_index = getattr(django_field, "db_index", False)

    # Default handling
    has_default = django_field.has_default()
    default = None
    if has_default:
        default = django_field.default

    max_length = getattr(django_field, "max_length", None)
    max_digits = getattr(django_field, "max_digits", None)
    decimal_places = getattr(django_field, "decimal_places", None)

    choices = list(django_field.choices) if django_field.choices else None
    enum_type = _detect_enum_type(django_field)

    # Relational field info
    is_relation = getattr(django_field, "is_relation", False)
    related_model = None
    related_model_label = None
    on_delete = None
    related_name = None
    is_self_referential = False
    many_to_many = is_m2m
    through_model = None
    through_db_table = None

    if is_relation:
        related_model = getattr(django_field, "related_model", None)

        if related_model is not None:
            try:
                related_model_label = f"{related_model._meta.app_label}.{related_model.__name__}"
            except AttributeError:
                related_model_label = None

        # on_delete from remote_field
        remote_field = getattr(django_field, "remote_field", None)
        if remote_field is not None:
            on_delete_func = getattr(remote_field, "on_delete", None)
            if on_delete_func is not None:
                # Extract the name from the on_delete callable
                # Django's on_delete functions have __name__ like 'CASCADE', 'SET_NULL', etc.
                on_delete = getattr(on_delete_func, "__name__", None)

        # related_name
        related_name_val = getattr(django_field, "related_query_name", None)
        if related_name_val and callable(related_name_val):
            # related_query_name() returns the related name
            pass
        # Use remote_field.related_name for the actual related_name
        if remote_field is not None:
            related_name = getattr(remote_field, "related_name", None)

        # Self-referential detection
        if related_model is not None:
            # Get the model that owns this field
            owner_model = getattr(django_field, "model", None)
            if owner_model is not None and related_model is owner_model:
                is_self_referential = True

        # M2M specific
        if many_to_many and remote_field is not None:
            through_model = getattr(remote_field, "through", None)
            if through_model is not None:
                try:
                    through_db_table = through_model._meta.db_table
                except AttributeError:
                    through_db_table = None

    # Auto field detection
    is_auto_field = isinstance(
        django_field,
        (models.AutoField, models.BigAutoField, models.SmallAutoField),
    )

    return FieldInfo(
        name=name,
        internal_type=internal_type,
        column=column,
        primary_key=primary_key,
        null=null,
        unique=unique,
        has_default=has_default,
        default=default,
        max_length=max_length,
        max_digits=max_digits,
        decimal_places=decimal_places,
        db_index=db_index,
        choices=choices,
        enum_type=enum_type,
        is_relation=is_relation,
        related_model=related_model,
        related_model_label=related_model_label,
        on_delete=on_delete,
        related_name=related_name,
        is_self_referential=is_self_referential,
        many_to_many=many_to_many,
        through_model=through_model,
        through_db_table=through_db_table,
        is_auto_field=is_auto_field,
        django_field=django_field,
    )


def introspect_model(django_model: type) -> ModelInfo:
    """
    Extract all schema metadata from a Django model.

    Iterates over all fields returned by ``_meta.get_fields()`` and produces
    a ``ModelInfo`` containing ``FieldInfo`` for each concrete or forward-M2M
    field.
    """
    meta = django_model._meta  # type: ignore[attr-defined]

    fields: list[FieldInfo] = []
    for django_field in meta.get_fields():
        field_info = introspect_field(django_field)
        if field_info is not None:
            fields.append(field_info)

    # Extract unique_together as a list of tuples
    unique_together = [tuple(ut) for ut in meta.unique_together]

    # Primary key name
    pk_name = meta.pk.name if meta.pk is not None else "id"

    return ModelInfo(
        model_class=django_model,
        app_label=meta.app_label,
        model_name=meta.model_name,
        db_table=meta.db_table,
        fields=fields,
        unique_together=unique_together,
        is_abstract=meta.abstract,
        is_proxy=meta.proxy,
        is_managed=meta.managed,
        pk_name=pk_name,
    )


def should_skip_model(model_info: ModelInfo) -> tuple[bool, str]:
    """
    Check if a model should be skipped during Tortoise model generation.

    Returns a ``(skip, reason)`` tuple. If ``skip`` is True, ``reason``
    contains a human-readable explanation.
    """
    if model_info.is_abstract:
        return True, f"Model '{model_info.model_name}' is abstract."

    if model_info.is_proxy:
        return True, f"Model '{model_info.model_name}' is a proxy model."

    if not model_info.fields:
        return True, f"Model '{model_info.model_name}' has no concrete fields."

    return False, ""
