"""
Django AppConfig for django-tortoise-objects.

Registers Tortoise model mirrors during Django's ``ready()`` phase.
Performs a two-pass model generation: first pass creates data-field-only
models, second pass adds relational fields after all targets are registered.
"""

import logging

from django.apps import AppConfig, apps

logger = logging.getLogger("django_tortoise")


class DjangoTortoiseConfig(AppConfig):
    name = "django_tortoise"
    verbose_name = "Django Tortoise Objects"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Synchronous startup: introspect Django models and generate Tortoise
        counterparts. Does NOT establish any database connections.

        Uses a two-pass approach:
          Pass 1 -- Introspect all included Django models, pre-register their
                    Tortoise class names so FK string references resolve.
          Pass 2 -- Generate Tortoise models with ALL fields (data + relational)
                    now that all target class names are known.
        """
        from django_tortoise import _models
        from django_tortoise.conf import get_config, should_include
        from django_tortoise.generator import generate_tortoise_model_full
        from django_tortoise.introspection import ModelInfo, introspect_model, should_skip_model
        from django_tortoise.manager import TortoiseObjects
        from django_tortoise.registry import model_registry

        config = get_config()
        include_patterns = config.get("INCLUDE_MODELS")
        exclude_patterns = config.get("EXCLUDE_MODELS")

        all_models = apps.get_models()
        generated_count = 0
        skipped_count = 0

        # Pass 1: Introspect and pre-register class name mappings
        # This lets FK string references resolve in Pass 2.
        eligible: list[tuple[type, str, ModelInfo]] = []  # (django_model, label, model_info)
        class_name_map: dict[type, str] = {}  # django_model -> tortoise class name

        for django_model in all_models:
            label = f"{django_model._meta.app_label}.{django_model.__name__}"

            if not should_include(label, include_patterns, exclude_patterns):
                logger.debug("Model '%s' excluded by configuration.", label)
                skipped_count += 1
                continue

            model_info = introspect_model(django_model)

            skip, reason = should_skip_model(model_info)
            if skip:
                logger.debug("Skipping model '%s': %s", label, reason)
                skipped_count += 1
                continue

            tortoise_class_name = f"{django_model.__name__}Tortoise"
            class_name_map[django_model] = tortoise_class_name
            eligible.append((django_model, label, model_info))

        # Pass 2: Generate Tortoise models with ALL fields
        for django_model, label, model_info in eligible:
            tortoise_model = generate_tortoise_model_full(model_info, class_name_map=class_name_map)
            if tortoise_model is None:
                class_name_map.pop(django_model, None)
                skipped_count += 1
                continue

            model_registry.register(django_model, tortoise_model, label)
            _models.__models__.append(tortoise_model)
            django_model.tortoise_objects = TortoiseObjects(tortoise_model)  # type: ignore[attr-defined]
            generated_count += 1

        logger.info(
            "django-tortoise-objects: Generated %d Tortoise models, skipped %d.",
            generated_count,
            skipped_count,
        )


# Backward-compatible alias: import from conf.should_include
def _should_include(
    label: str,
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
) -> bool:
    """
    Check if a model label matches include/exclude patterns.

    .. deprecated::
        Use ``django_tortoise.conf.should_include()`` instead.
        This alias is kept for backward compatibility with existing tests.
    """
    from django_tortoise.conf import should_include

    return should_include(label, include_patterns, exclude_patterns)
