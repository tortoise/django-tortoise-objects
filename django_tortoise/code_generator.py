"""
Source code generation for Tortoise ORM models.

Produces Python source code strings from ``FieldInfo`` and ``ModelInfo``
dataclasses.  This module mirrors ``fields.py`` + ``generator.py`` but
outputs source code instead of live objects.

All functions are pure -- no file I/O, no Django app registry access.
"""

from __future__ import annotations

import enum
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from django_tortoise.fields import ON_DELETE_MAP
from django_tortoise.introspection import FieldInfo, ModelInfo

logger = logging.getLogger("django_tortoise")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ModelSourceResult:
    """Result of rendering a single Tortoise model to source code."""

    class_name: str
    source: str
    imports: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Simple literal types whose ``repr()`` is valid Python source.
_SIMPLE_LITERAL_TYPES = (int, float, str, bool, type(None))

# Known safe callables that can be emitted by name.
_SAFE_CALLABLES = {dict, list, set, frozenset, tuple}

# Known safe callables that need a qualified module path (e.g., ``uuid.uuid4``).
_QUALIFIED_CALLABLES: dict[object, tuple[str, str]] = {
    uuid.uuid4: ("uuid", "uuid.uuid4"),
}


def _format_kwargs(kwargs: dict[str, str]) -> str:
    """Join kwarg pairs into a comma-separated source string."""
    return ", ".join(f"{k}={v}" for k, v in kwargs.items())


def _common_kwargs_source(field_info: FieldInfo) -> dict[str, str]:
    """
    Build common kwargs as ``{name: source_repr}`` pairs.

    Mirrors ``fields._common_kwargs()`` but returns source-code strings
    instead of runtime values.
    """
    kwargs: dict[str, str] = {}
    if field_info.null:
        kwargs["null"] = "True"
    if field_info.unique:
        kwargs["unique"] = "True"
    if field_info.db_index:
        kwargs["db_index"] = "True"
    if field_info.primary_key:
        kwargs["primary_key"] = "True"
    # source_field when column differs from name
    if field_info.column and field_info.column != field_info.name:
        kwargs["source_field"] = repr(field_info.column)
    # default handling
    if field_info.has_default:
        default = field_info.default
        # Check enum before simple literals because IntegerChoices members
        # are also int instances.
        if isinstance(default, enum.Enum):
            kwargs["default"] = f"{type(default).__name__}.{default.name}"
        elif isinstance(default, _SIMPLE_LITERAL_TYPES):
            kwargs["default"] = repr(default)
        elif default in _SAFE_CALLABLES:
            kwargs["default"] = default.__name__
        elif default in _QUALIFIED_CALLABLES:
            kwargs["default"] = _QUALIFIED_CALLABLES[default][1]
        elif callable(default):
            # Unserializable callable -- emit None placeholder
            kwargs["default"] = "None"
            kwargs["# TODO"] = ""  # sentinel; handled by caller
        else:
            kwargs["default"] = repr(default)
    return kwargs


def _extract_todo_comment(kwargs: dict[str, str], field_name: str) -> str | None:
    """Pop the TODO sentinel from kwargs and return a comment string, or None."""
    if "# TODO" in kwargs:
        del kwargs["# TODO"]
        return f"  # TODO: set default for '{field_name}'"
    return None


# ---------------------------------------------------------------------------
# SOURCE_FIELD_MAP -- parallel to fields.FIELD_MAP
# ---------------------------------------------------------------------------


def _try_enum_field_source(info: FieldInfo) -> str | None:
    """Return an enum field source string if the field has an enum_type, else None."""
    if info.enum_type is None:
        return None
    kwargs = _common_kwargs_source(info)
    _extract_todo_comment(kwargs, info.name)  # clean sentinel if present
    enum_name = info.enum_type.__name__
    if issubclass(info.enum_type, int):
        extra = _format_kwargs(kwargs)
        parts = [enum_name]
        if extra:
            parts.append(extra)
        return f"fields.IntEnumField({', '.join(parts)})"
    if issubclass(info.enum_type, str):
        kwargs["max_length"] = repr(info.max_length or 255)
        extra = _format_kwargs(kwargs)
        parts = [enum_name]
        if extra:
            parts.append(extra)
        return f"fields.CharEnumField({', '.join(parts)})"
    return None


# Mapping: internal_type -> source-rendering function
SOURCE_FIELD_MAP: dict[str, Callable[[FieldInfo], str | None]] = {}


def _register_source(internal_type: str):
    """Decorator to register a source renderer for a Django internal_type."""

    def decorator(func: Callable[[FieldInfo], str | None]) -> Callable[[FieldInfo], str | None]:
        SOURCE_FIELD_MAP[internal_type] = func
        return func

    return decorator


# --- Auto fields ---


@_register_source("AutoField")
def _auto_source(info: FieldInfo) -> str:
    return "fields.IntField(primary_key=True, generated=True)"


@_register_source("BigAutoField")
def _big_auto_source(info: FieldInfo) -> str:
    return "fields.BigIntField(primary_key=True, generated=True)"


@_register_source("SmallAutoField")
def _small_auto_source(info: FieldInfo) -> str:
    return "fields.SmallIntField(primary_key=True, generated=True)"


# --- Integer fields ---


def _int_field_source(tortoise_type: str) -> Callable[[FieldInfo], str | None]:
    """Factory for integer field source renderers."""

    def renderer(info: FieldInfo) -> str | None:
        enum_src = _try_enum_field_source(info)
        if enum_src is not None:
            return enum_src
        kwargs = _common_kwargs_source(info)
        comment = _extract_todo_comment(kwargs, info.name)
        result = f"fields.{tortoise_type}({_format_kwargs(kwargs)})"
        if comment:
            result += comment
        return result

    return renderer


SOURCE_FIELD_MAP["IntegerField"] = _int_field_source("IntField")
SOURCE_FIELD_MAP["BigIntegerField"] = _int_field_source("BigIntField")
SOURCE_FIELD_MAP["SmallIntegerField"] = _int_field_source("SmallIntField")
SOURCE_FIELD_MAP["PositiveIntegerField"] = _int_field_source("IntField")
SOURCE_FIELD_MAP["PositiveBigIntegerField"] = _int_field_source("BigIntField")
SOURCE_FIELD_MAP["PositiveSmallIntegerField"] = _int_field_source("SmallIntField")


# --- String fields ---


@_register_source("CharField")
def _char_source(info: FieldInfo) -> str | None:
    enum_src = _try_enum_field_source(info)
    if enum_src is not None:
        return enum_src
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    kwargs["max_length"] = repr(info.max_length or 255)
    result = f"fields.CharField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("TextField")
def _text_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.TextField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


# --- Boolean ---


@_register_source("BooleanField")
def _bool_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.BooleanField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


# --- Date/Time fields ---


@_register_source("DateField")
def _date_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.DateField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("DateTimeField")
def _datetime_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.DatetimeField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("TimeField")
def _time_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.TimeField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("DurationField")
def _duration_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.TimeDeltaField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


# --- Numeric fields ---


@_register_source("DecimalField")
def _decimal_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    kwargs["max_digits"] = repr(info.max_digits)
    kwargs["decimal_places"] = repr(info.decimal_places)
    result = f"fields.DecimalField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("FloatField")
def _float_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.FloatField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


# --- Binary / UUID / JSON fields ---


@_register_source("BinaryField")
def _binary_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.BinaryField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("UUIDField")
def _uuid_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.UUIDField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


@_register_source("JSONField")
def _json_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    result = f"fields.JSONField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


# --- File / path fields (approximate: stored as CharField) ---


def _file_like_source(default_max: int) -> Callable[[FieldInfo], str | None]:
    """Factory for file-like field source renderers (map to CharField)."""

    def renderer(info: FieldInfo) -> str | None:
        kwargs = _common_kwargs_source(info)
        comment = _extract_todo_comment(kwargs, info.name)
        kwargs["max_length"] = repr(info.max_length or default_max)
        result = f"fields.CharField({_format_kwargs(kwargs)})"
        if comment:
            result += comment
        return result

    return renderer


SOURCE_FIELD_MAP["FileField"] = _file_like_source(100)
SOURCE_FIELD_MAP["ImageField"] = _file_like_source(100)
SOURCE_FIELD_MAP["FilePathField"] = _file_like_source(100)


# --- Specialised string fields ---


def _char_like_source(default_max: int) -> Callable[[FieldInfo], str | None]:
    """Factory for char-like field source renderers."""

    def renderer(info: FieldInfo) -> str | None:
        kwargs = _common_kwargs_source(info)
        comment = _extract_todo_comment(kwargs, info.name)
        kwargs["max_length"] = repr(info.max_length or default_max)
        result = f"fields.CharField({_format_kwargs(kwargs)})"
        if comment:
            result += comment
        return result

    return renderer


SOURCE_FIELD_MAP["SlugField"] = _char_like_source(50)
SOURCE_FIELD_MAP["EmailField"] = _char_like_source(254)
SOURCE_FIELD_MAP["URLField"] = _char_like_source(200)


@_register_source("GenericIPAddressField")
def _ip_source(info: FieldInfo) -> str | None:
    kwargs = _common_kwargs_source(info)
    comment = _extract_todo_comment(kwargs, info.name)
    kwargs["max_length"] = "39"
    result = f"fields.CharField({_format_kwargs(kwargs)})"
    if comment:
        result += comment
    return result


# ---------------------------------------------------------------------------
# Data field source rendering
# ---------------------------------------------------------------------------


def render_field_source(field_info: FieldInfo) -> str | None:
    """
    Render a non-relational field to source code.

    Returns ``None`` if no renderer is registered for the field's internal_type.
    """
    renderer = SOURCE_FIELD_MAP.get(field_info.internal_type)
    if renderer is None:
        logger.warning(
            "Unsupported Django field type '%s' on field '%s'. Skipping.",
            field_info.internal_type,
            field_info.name,
        )
        return None
    return renderer(field_info)


# ---------------------------------------------------------------------------
# Relational field source rendering
# ---------------------------------------------------------------------------


def _render_fk_source(field_info: FieldInfo, target_ref: str) -> str:
    """Render a ForeignKeyField source string. Mirrors ``fields._build_fk``."""
    on_delete_name = ON_DELETE_MAP.get(field_info.on_delete or "", "CASCADE")

    kwargs: dict[str, str] = {}
    if field_info.related_name and field_info.related_name != "+":
        kwargs["related_name"] = repr(field_info.related_name)
    else:
        kwargs["related_name"] = "False"
    kwargs["on_delete"] = f"OnDelete.{on_delete_name}"
    if field_info.column:
        kwargs["source_field"] = repr(field_info.column)
    if field_info.null:
        kwargs["null"] = "True"

    return f'fields.ForeignKeyField("{target_ref}", {_format_kwargs(kwargs)})'


def _render_o2o_source(field_info: FieldInfo, target_ref: str) -> str:
    """Render a OneToOneField source string. Mirrors ``fields._build_o2o``."""
    on_delete_name = ON_DELETE_MAP.get(field_info.on_delete or "", "CASCADE")

    kwargs: dict[str, str] = {}
    if field_info.related_name and field_info.related_name != "+":
        kwargs["related_name"] = repr(field_info.related_name)
    else:
        kwargs["related_name"] = "False"
    kwargs["on_delete"] = f"OnDelete.{on_delete_name}"
    if field_info.column:
        kwargs["source_field"] = repr(field_info.column)
    if field_info.null:
        kwargs["null"] = "True"

    return f'fields.OneToOneField("{target_ref}", {_format_kwargs(kwargs)})'


def _render_m2m_source(field_info: FieldInfo, target_ref: str) -> str:
    """Render a ManyToManyField source string. Mirrors ``fields._build_m2m``."""
    kwargs: dict[str, str] = {}
    if field_info.related_name and field_info.related_name != "+":
        kwargs["related_name"] = repr(field_info.related_name)
    else:
        kwargs["related_name"] = "False"
    if field_info.through_db_table:
        kwargs["through"] = repr(field_info.through_db_table)

    return f'fields.ManyToManyField("{target_ref}", {_format_kwargs(kwargs)})'


def render_relation_field_source(
    field_info: FieldInfo,
    tortoise_app_name: str,
    class_name_map: dict[type, str],
) -> tuple[str, str] | None:
    """
    Render a relational field to source code.

    Returns ``(field_name, source_string)`` or ``None`` if the target model
    is not in *class_name_map*.
    """
    target_model = field_info.related_model
    if target_model is None:
        logger.warning(
            "Relation field '%s' has no related model. Skipping.",
            field_info.name,
        )
        return None

    tortoise_class_name = class_name_map.get(target_model)
    if tortoise_class_name is None:
        logger.warning(
            "Relation field '%s' points to unregistered/excluded model '%s'. Skipping.",
            field_info.name,
            field_info.related_model_label,
        )
        return None

    target_ref = f"{tortoise_app_name}.{tortoise_class_name}"

    internal_type = field_info.internal_type
    if internal_type == "ForeignKey":
        return (field_info.name, _render_fk_source(field_info, target_ref))
    elif internal_type == "OneToOneField":
        return (field_info.name, _render_o2o_source(field_info, target_ref))
    elif field_info.many_to_many:
        return (field_info.name, _render_m2m_source(field_info, target_ref))

    return None


# ---------------------------------------------------------------------------
# Model source rendering
# ---------------------------------------------------------------------------


def render_model_source(
    model_info: ModelInfo,
    tortoise_app_name: str,
    class_name_map: dict[type, str],
) -> ModelSourceResult | None:
    """
    Render a full Tortoise model class definition as source code.

    Returns ``None`` if the model has no convertible data fields.
    """
    imports: set[str] = set()
    imports.add("from tortoise import fields")
    imports.add("from tortoise.models import Model")

    class_name = f"{model_info.model_class.__name__}Tortoise"
    field_lines: list[str] = []
    converted_names: set[str] = set()
    skipped_fields: list[str] = []
    has_relations = False

    # Data fields
    for fi in model_info.fields:
        if fi.is_relation:
            continue
        source = render_field_source(fi)
        if source is None:
            skipped_fields.append(fi.name)
            continue
        field_lines.append(f"    {fi.name} = {source}")
        converted_names.add(fi.name)

        # Track enum imports
        if fi.enum_type is not None:
            model_module = model_info.model_class.__module__
            enum_class_name = fi.enum_type.__name__
            imports.add(f"from {model_module} import {enum_class_name}")

        # Track qualified callable imports (e.g., uuid.uuid4)
        if fi.has_default and fi.default in _QUALIFIED_CALLABLES:
            module_name = _QUALIFIED_CALLABLES[fi.default][0]
            imports.add(f"import {module_name}")

    if not converted_names:
        logger.warning(
            "Model '%s.%s' has no convertible fields. Skipping.",
            model_info.app_label,
            model_info.model_name,
        )
        return None

    if skipped_fields:
        for name in skipped_fields:
            field_lines.append(f"    # Skipped unsupported field: {name}")

    # Relational fields
    for fi in model_info.fields:
        if not fi.is_relation:
            continue
        result = render_relation_field_source(fi, tortoise_app_name, class_name_map)
        if result is None:
            continue
        field_name, source = result
        field_lines.append(f"    {field_name} = {source}")
        converted_names.add(field_name)
        has_relations = True

    if has_relations:
        imports.add("from tortoise.fields.relational import OnDelete")

    # Meta class
    meta_lines: list[str] = []
    meta_lines.append(f'        table = "{model_info.db_table}"')
    meta_lines.append(f'        app = "{tortoise_app_name}"')

    if model_info.unique_together:
        valid_constraints: list[tuple[str, ...]] = []
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
            meta_lines.append(f"        unique_together = {valid_constraints!r}")

    # Assemble class source
    lines: list[str] = []
    lines.append(f"class {class_name}(Model):")
    lines.extend(field_lines)
    lines.append("")
    lines.append("    class Meta:")
    lines.extend(meta_lines)

    source = "\n".join(lines)
    return ModelSourceResult(class_name=class_name, source=source, imports=imports)


# ---------------------------------------------------------------------------
# App module rendering
# ---------------------------------------------------------------------------


def render_app_module(models: list[ModelSourceResult], app_label: str) -> str:
    """
    Combine multiple ``ModelSourceResult`` objects into a complete Python module.

    Produces a self-contained ``.py`` file with a header comment, merged
    imports, and all model class definitions separated by blank lines.
    """
    # Header
    header = "# Auto-generated by django-tortoise-objects. Do not edit manually."

    # Merge and sort imports
    all_imports: set[str] = set()
    for model in models:
        all_imports.update(model.imports)
    sorted_imports = sorted(all_imports)

    # Combine model sources
    model_sources = [m.source for m in models]

    parts: list[str] = [header, ""]
    parts.extend(sorted_imports)
    parts.append("")
    parts.append("")
    parts.append("\n\n\n".join(model_sources))
    parts.append("")

    return "\n".join(parts)
