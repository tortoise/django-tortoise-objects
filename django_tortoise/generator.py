"""
Dynamic Tortoise model class generation.

Creates Tortoise ORM model classes at runtime from ``ModelInfo`` objects
produced by the introspection module, using ``type()`` with Tortoise's
``Model`` as the base class.  The ``ModelMeta`` metaclass (inherited from
``tortoise.models.Model``) handles field registration automatically.

Two functions are provided:
  - ``generate_tortoise_model()`` -- creates data-field-only models (Phase 2).
  - ``generate_tortoise_model_full()`` -- creates models with data + relational
    fields, used by ``AppConfig.ready()`` after pre-registration.
"""

import logging
from typing import Any

from tortoise import models as tortoise_models

from django_tortoise.fields import convert_field, convert_relation_field_by_name
from django_tortoise.introspection import ModelInfo

logger = logging.getLogger("django_tortoise")


def generate_tortoise_model(
    model_info: ModelInfo,
    tortoise_app_name: str = "django_tortoise",
) -> type | None:
    """
    Generate a Tortoise ORM model class from Django model metadata.

    Iterates over the non-relational fields in *model_info*, converts each
    to a Tortoise field via ``convert_field()``, and constructs a new
    ``tortoise.models.Model`` subclass with ``type()``.

    Returns ``None`` if the model has no convertible data fields.
    """
    tortoise_fields, skipped_fields = _build_data_fields(model_info)

    if not tortoise_fields:
        logger.warning(
            "Model '%s.%s' has no convertible fields. Skipping.",
            model_info.app_label,
            model_info.model_name,
        )
        return None

    if skipped_fields:
        logger.info(
            "Skipped fields %s on model '%s.%s' (unsupported types).",
            skipped_fields,
            model_info.app_label,
            model_info.model_name,
        )

    meta_class = _build_meta_class(model_info, tortoise_fields, tortoise_app_name)
    class_name = f"{model_info.model_class.__name__}Tortoise"

    try:
        tortoise_model = type(
            class_name,
            (tortoise_models.Model,),
            {
                "Meta": meta_class,
                **tortoise_fields,
            },
        )
    except Exception as exc:
        raise type(exc)(
            f"Failed to create Tortoise model '{class_name}' for Django model "
            f"'{model_info.app_label}.{model_info.model_name}': {exc}"
        ) from exc

    logger.debug(
        "Generated Tortoise model '%s' for Django model '%s.%s' (table: %s, fields: %d)",
        class_name,
        model_info.app_label,
        model_info.model_name,
        model_info.db_table,
        len(tortoise_fields),
    )

    return tortoise_model


def generate_tortoise_model_full(
    model_info: ModelInfo,
    tortoise_app_name: str = "django_tortoise",
    class_name_map: dict[type, str] | None = None,
) -> type | None:
    """
    Generate a Tortoise ORM model class with ALL fields (data + relational).

    Uses *class_name_map* to resolve FK/O2O/M2M string references without
    requiring the target Tortoise models to exist yet.  The map is keyed
    by Django model class and valued by the planned Tortoise class name.

    Returns ``None`` if the model has no convertible data fields.
    """
    tortoise_fields, skipped_fields = _build_data_fields(model_info)

    if not tortoise_fields:
        logger.warning(
            "Model '%s.%s' has no convertible fields. Skipping.",
            model_info.app_label,
            model_info.model_name,
        )
        return None

    if skipped_fields:
        logger.info(
            "Skipped fields %s on model '%s.%s' (unsupported types).",
            skipped_fields,
            model_info.app_label,
            model_info.model_name,
        )

    # Add relational fields
    for field_info in model_info.fields:
        if not field_info.is_relation:
            continue
        result = convert_relation_field_by_name(
            field_info,
            tortoise_app_name=tortoise_app_name,
            class_name_map=class_name_map,
        )
        if result is None:
            continue
        field_name, tortoise_field = result
        tortoise_fields[field_name] = tortoise_field

    meta_class = _build_meta_class(model_info, tortoise_fields, tortoise_app_name)
    class_name = f"{model_info.model_class.__name__}Tortoise"

    try:
        tortoise_model = type(
            class_name,
            (tortoise_models.Model,),
            {
                "Meta": meta_class,
                **tortoise_fields,
            },
        )
    except Exception as exc:
        raise type(exc)(
            f"Failed to create Tortoise model '{class_name}' for Django model "
            f"'{model_info.app_label}.{model_info.model_name}': {exc}"
        ) from exc

    logger.debug(
        "Generated Tortoise model '%s' for Django model '%s.%s' "
        "(table: %s, data fields: %d, total fields: %d)",
        class_name,
        model_info.app_label,
        model_info.model_name,
        model_info.db_table,
        len([f for f in tortoise_fields.values() if not hasattr(f, "related_model")]),
        len(tortoise_fields),
    )

    return tortoise_model


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_data_fields(model_info: ModelInfo) -> tuple[dict[str, object], list[str]]:
    """Convert non-relational fields to Tortoise fields."""
    tortoise_fields: dict[str, object] = {}
    skipped_fields: list[str] = []

    for field_info in model_info.fields:
        if field_info.is_relation:
            continue

        tortoise_field = convert_field(field_info)
        if tortoise_field is None:
            skipped_fields.append(field_info.name)
            continue
        tortoise_fields[field_info.name] = tortoise_field

    return tortoise_fields, skipped_fields


def _build_meta_class(
    model_info: ModelInfo,
    tortoise_fields: dict[str, object],
    tortoise_app_name: str,
) -> type:
    """Build the inner Meta class for a Tortoise model."""
    meta_attrs: dict[str, Any] = {
        "table": model_info.db_table,
        "app": tortoise_app_name,
    }

    if model_info.unique_together:
        valid_constraints: list[tuple[str, ...]] = []
        converted_names = set(tortoise_fields.keys())
        for constraint in model_info.unique_together:
            missing = [f for f in constraint if f not in converted_names]
            if missing:
                logger.warning(
                    "unique_together constraint %s on '%s.%s' references "
                    "unconverted fields %s; omitting constraint.",
                    constraint,
                    model_info.app_label,
                    model_info.model_name,
                    missing,
                )
            else:
                valid_constraints.append(tuple(constraint))
        if valid_constraints:
            meta_attrs["unique_together"] = tuple(valid_constraints)

    return type("Meta", (), meta_attrs)
