"""
Field type mapping registry.

Maps Django field type strings (from ``get_internal_type()``) to Tortoise ORM
field constructors with correct parameter translation.

The registry key is the string returned by Django's ``Field.get_internal_type()``.
A decorator-based registration pattern allows adding new mappings cleanly.
"""

import logging
from collections.abc import Callable
from typing import Any

from tortoise import fields as tortoise_fields

from django_tortoise.introspection import FieldInfo

logger = logging.getLogger("django_tortoise")

# Type alias for the converter function signature
# Converter takes FieldInfo and returns a Tortoise Field instance
FieldConverter = Callable[[FieldInfo], tortoise_fields.Field]

# The main registry: Django internal_type string -> converter function
FIELD_MAP: dict[str, FieldConverter] = {}


def register_field(internal_type: str):
    """Decorator to register a field converter for a Django internal_type string."""

    def decorator(func: FieldConverter) -> FieldConverter:
        FIELD_MAP[internal_type] = func
        return func

    return decorator


def _common_kwargs(field_info: FieldInfo) -> dict[str, Any]:
    """
    Extract common kwargs shared by most Tortoise fields.

    Maps null, primary_key, source_field (when DB column
    differs from field name), and default values.

    Note: ``unique`` and ``db_index`` are intentionally NOT mapped.
    The library relies on the existing Django-managed database schema,
    so Tortoise-level index/unique declarations are unnecessary and can
    cause errors (e.g. ``TextField`` does not support ``unique`` in Tortoise).
    """
    kwargs: dict[str, Any] = {}
    if field_info.null:
        kwargs["null"] = True
    if field_info.primary_key:
        kwargs["primary_key"] = True
    # Map db_column -> source_field
    if field_info.column and field_info.column != field_info.name:
        kwargs["source_field"] = field_info.column
    # Handle defaults
    # Bug fix: when has_default is True, always set the default, even if it's None.
    # A field with has_default=True and default=None is a valid Django pattern
    # (e.g., nullable fields with default=None).
    if field_info.has_default:
        default = field_info.default
        kwargs["default"] = default
    return kwargs


def convert_field(field_info: FieldInfo) -> tortoise_fields.Field | None:
    """
    Convert a FieldInfo to a Tortoise field instance.

    Returns None if no converter is registered for the field's internal_type,
    logging a warning in that case.
    """
    converter = FIELD_MAP.get(field_info.internal_type)
    if converter is None:
        logger.warning(
            "Unsupported Django field type '%s' on field '%s'. Skipping.",
            field_info.internal_type,
            field_info.name,
        )
        return None
    return converter(field_info)


def _try_enum_field(info: FieldInfo) -> tortoise_fields.Field | None:
    """Return an IntEnumField or CharEnumField if the field has an enum_type, else None."""
    if info.enum_type is None:
        return None
    kwargs = _common_kwargs(info)
    if issubclass(info.enum_type, int):
        return tortoise_fields.IntEnumField(info.enum_type, **kwargs)  # type: ignore[type-var,return-value]
    if issubclass(info.enum_type, str):
        kwargs["max_length"] = info.max_length or 255
        return tortoise_fields.CharEnumField(info.enum_type, **kwargs)  # type: ignore[type-var,return-value]
    return None


# ---------------------------------------------------------------------------
# Auto fields (primary key, generated)
# ---------------------------------------------------------------------------


@register_field("AutoField")
def _auto_field(info: FieldInfo):
    return tortoise_fields.IntField(primary_key=True, generated=True)


@register_field("BigAutoField")
def _big_auto_field(info: FieldInfo):
    return tortoise_fields.BigIntField(primary_key=True, generated=True)


@register_field("SmallAutoField")
def _small_auto_field(info: FieldInfo):
    return tortoise_fields.SmallIntField(primary_key=True, generated=True)


# ---------------------------------------------------------------------------
# Integer fields
# ---------------------------------------------------------------------------


@register_field("IntegerField")
def _int_field(info: FieldInfo):
    return _try_enum_field(info) or tortoise_fields.IntField(**_common_kwargs(info))


@register_field("BigIntegerField")
def _bigint_field(info: FieldInfo):
    return _try_enum_field(info) or tortoise_fields.BigIntField(**_common_kwargs(info))


@register_field("SmallIntegerField")
def _smallint_field(info: FieldInfo):
    return _try_enum_field(info) or tortoise_fields.SmallIntField(**_common_kwargs(info))


@register_field("PositiveIntegerField")
def _pos_int(info: FieldInfo):
    return _try_enum_field(info) or tortoise_fields.IntField(**_common_kwargs(info))


@register_field("PositiveBigIntegerField")
def _pos_bigint(info: FieldInfo):
    return _try_enum_field(info) or tortoise_fields.BigIntField(**_common_kwargs(info))


@register_field("PositiveSmallIntegerField")
def _pos_smallint(info: FieldInfo):
    return _try_enum_field(info) or tortoise_fields.SmallIntField(**_common_kwargs(info))


# ---------------------------------------------------------------------------
# String fields
# ---------------------------------------------------------------------------


@register_field("CharField")
def _char_field(info: FieldInfo):
    enum_field = _try_enum_field(info)
    if enum_field is not None:
        return enum_field
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 255
    return tortoise_fields.CharField(**kwargs)


@register_field("TextField")
def _text_field(info: FieldInfo):
    return tortoise_fields.TextField(**_common_kwargs(info))


# ---------------------------------------------------------------------------
# Boolean field
# ---------------------------------------------------------------------------


@register_field("BooleanField")
def _bool_field(info: FieldInfo):
    return tortoise_fields.BooleanField(**_common_kwargs(info))


# ---------------------------------------------------------------------------
# Date/Time fields
# ---------------------------------------------------------------------------


@register_field("DateField")
def _date_field(info: FieldInfo):
    return tortoise_fields.DateField(**_common_kwargs(info))


@register_field("DateTimeField")
def _datetime_field(info: FieldInfo):
    return tortoise_fields.DatetimeField(**_common_kwargs(info))


@register_field("TimeField")
def _time_field(info: FieldInfo):
    return tortoise_fields.TimeField(**_common_kwargs(info))


@register_field("DurationField")
def _duration_field(info: FieldInfo):
    return tortoise_fields.TimeDeltaField(**_common_kwargs(info))


# ---------------------------------------------------------------------------
# Numeric fields
# ---------------------------------------------------------------------------


@register_field("DecimalField")
def _decimal_field(info: FieldInfo):
    kwargs = _common_kwargs(info)
    kwargs["max_digits"] = info.max_digits
    kwargs["decimal_places"] = info.decimal_places
    return tortoise_fields.DecimalField(**kwargs)


@register_field("FloatField")
def _float_field(info: FieldInfo):
    return tortoise_fields.FloatField(**_common_kwargs(info))


# ---------------------------------------------------------------------------
# Binary / UUID / JSON fields
# ---------------------------------------------------------------------------


@register_field("BinaryField")
def _binary_field(info: FieldInfo):
    return tortoise_fields.BinaryField(**_common_kwargs(info))


@register_field("UUIDField")
def _uuid_field(info: FieldInfo):
    return tortoise_fields.UUIDField(**_common_kwargs(info))


@register_field("JSONField")
def _json_field(info: FieldInfo):
    return tortoise_fields.JSONField(**_common_kwargs(info))


# ---------------------------------------------------------------------------
# File / path fields (approximate mappings -- store path as CharField)
# ---------------------------------------------------------------------------


@register_field("FileField")
def _file_field(info: FieldInfo):
    logger.info("Mapping FileField '%s' to CharField (stores path).", info.name)
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 100
    return tortoise_fields.CharField(**kwargs)


# NOTE: ImageField's get_internal_type() returns "CharField", so this converter
# is only reached if a custom subclass overrides get_internal_type() to return
# "ImageField".  Registered for completeness and forward-compatibility.
@register_field("ImageField")
def _image_field(info: FieldInfo):
    logger.info("Mapping ImageField '%s' to CharField (stores path).", info.name)
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 100
    return tortoise_fields.CharField(**kwargs)


@register_field("FilePathField")
def _filepath_field(info: FieldInfo):
    logger.info("Mapping FilePathField '%s' to CharField.", info.name)
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 100
    return tortoise_fields.CharField(**kwargs)


# ---------------------------------------------------------------------------
# Specialised string fields (approximate mappings)
# ---------------------------------------------------------------------------


@register_field("SlugField")
def _slug_field(info: FieldInfo):
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 50
    return tortoise_fields.CharField(**kwargs)


# NOTE: EmailField's get_internal_type() returns "CharField", so this converter
# is only reached if a custom subclass overrides get_internal_type() to return
# "EmailField".  Registered for completeness and forward-compatibility.
@register_field("EmailField")
def _email_field(info: FieldInfo):
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 254
    return tortoise_fields.CharField(**kwargs)


# NOTE: URLField's get_internal_type() returns "CharField", so this converter
# is only reached if a custom subclass overrides get_internal_type() to return
# "URLField".  Registered for completeness and forward-compatibility.
@register_field("URLField")
def _url_field(info: FieldInfo):
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = info.max_length or 200
    return tortoise_fields.CharField(**kwargs)


@register_field("GenericIPAddressField")
def _ip_field(info: FieldInfo):
    kwargs = _common_kwargs(info)
    kwargs["max_length"] = 39
    return tortoise_fields.CharField(**kwargs)


# ---------------------------------------------------------------------------
# Relational field mapping
# ---------------------------------------------------------------------------


# Lazy import to avoid importing tortoise.fields.relational at module level
def _get_on_delete_enum():
    """Lazy import of Tortoise OnDelete enum."""
    from tortoise.fields.relational import OnDelete

    return OnDelete


# Django on_delete name -> Tortoise OnDelete enum member name
ON_DELETE_MAP: dict[str, str] = {
    "CASCADE": "CASCADE",
    "SET_NULL": "SET_NULL",
    "SET_DEFAULT": "SET_DEFAULT",
    "PROTECT": "RESTRICT",  # Tortoise has RESTRICT, not PROTECT
    "RESTRICT": "RESTRICT",
    "DO_NOTHING": "NO_ACTION",  # Tortoise uses NO_ACTION, not DO_NOTHING
}


def _map_on_delete(django_on_delete: str | None):
    """Map a Django on_delete name to the Tortoise OnDelete enum value."""
    OnDelete = _get_on_delete_enum()
    if django_on_delete is None:
        return OnDelete.CASCADE
    mapped_name = ON_DELETE_MAP.get(django_on_delete, "CASCADE")
    return OnDelete[mapped_name]


def convert_relation_field(
    field_info: FieldInfo,
    tortoise_app_name: str = "django_tortoise",
) -> tuple[str, object] | None:
    """
    Convert a relational FieldInfo to a Tortoise relation field.

    Uses the model registry to resolve the target model.  Returns
    ``(field_name, tortoise_field)`` or ``None`` if the relation
    target is unavailable (e.g., excluded model).
    """
    from django_tortoise.registry import model_registry

    target_model = field_info.related_model
    if target_model is None:
        logger.warning(
            "Relation field '%s' has no related model. Skipping.",
            field_info.name,
        )
        return None

    if not model_registry.is_registered(target_model):
        logger.warning(
            "Relation field '%s' points to unregistered/excluded model '%s'. Skipping.",
            field_info.name,
            field_info.related_model_label,
        )
        return None

    target_tortoise = model_registry.get_tortoise_model(target_model)
    if target_tortoise is None:
        return None
    target_ref = f"{tortoise_app_name}.{target_tortoise.__name__}"

    return _convert_relation_to_field(field_info, target_ref)


def convert_relation_field_by_name(
    field_info: FieldInfo,
    tortoise_app_name: str = "django_tortoise",
    class_name_map: dict[type, str] | None = None,
) -> tuple[str, object] | None:
    """
    Convert a relational FieldInfo using a pre-computed class name map.

    This variant does not require the target Tortoise model to exist yet.
    It uses *class_name_map* (Django model class -> Tortoise class name)
    to build the string reference.  Returns ``(field_name, tortoise_field)``
    or ``None`` if the target is not in the map.
    """
    target_model = field_info.related_model
    if target_model is None:
        logger.warning(
            "Relation field '%s' has no related model. Skipping.",
            field_info.name,
        )
        return None

    if class_name_map is None:
        class_name_map = {}

    tortoise_class_name = class_name_map.get(target_model)
    if tortoise_class_name is None:
        logger.warning(
            "Relation field '%s' points to unregistered/excluded model '%s'. Skipping.",
            field_info.name,
            field_info.related_model_label,
        )
        return None

    target_ref = f"{tortoise_app_name}.{tortoise_class_name}"
    return _convert_relation_to_field(field_info, target_ref)


def _convert_relation_to_field(field_info: FieldInfo, target_ref: str) -> tuple[str, object] | None:
    """Dispatch to the appropriate relational field builder."""
    internal_type = field_info.internal_type

    if internal_type == "ForeignKey":
        return _build_fk(field_info, target_ref)
    elif internal_type == "OneToOneField":
        return _build_o2o(field_info, target_ref)
    elif field_info.many_to_many:
        return _build_m2m(field_info, target_ref)

    return None


def _build_fk(info: FieldInfo, target_ref: str) -> tuple[str, object]:
    """Build a Tortoise ForeignKeyField from introspected field info."""
    on_delete = _map_on_delete(info.on_delete)
    related_name: str | bool | None = None
    if info.related_name and info.related_name != "+":
        related_name = info.related_name
    else:
        # Tortoise requires a related_name or False to disable.
        # Use False to avoid auto-generated reverse accessors clashing.
        related_name = False

    kwargs: dict[str, Any] = {}
    if info.column:
        kwargs["source_field"] = info.column
    if info.null:
        kwargs["null"] = True
    return (
        info.name,
        tortoise_fields.ForeignKeyField(
            target_ref,
            related_name=related_name,  # type: ignore[arg-type]
            on_delete=on_delete,
            **kwargs,
        ),
    )


def _build_o2o(info: FieldInfo, target_ref: str) -> tuple[str, object]:
    """Build a Tortoise OneToOneField from introspected field info."""
    on_delete = _map_on_delete(info.on_delete)
    related_name: str | bool | None = None
    if info.related_name and info.related_name != "+":
        related_name = info.related_name
    else:
        related_name = False

    kwargs: dict[str, Any] = {}
    if info.column:
        kwargs["source_field"] = info.column
    if info.null:
        kwargs["null"] = True
    return (
        info.name,
        tortoise_fields.OneToOneField(
            target_ref,
            related_name=related_name,  # type: ignore[arg-type]
            on_delete=on_delete,
            **kwargs,
        ),
    )


def _build_m2m(info: FieldInfo, target_ref: str) -> tuple[str, object]:
    """Build a Tortoise ManyToManyField from introspected field info."""
    related_name: str | bool | None = None
    if info.related_name and info.related_name != "+":
        related_name = info.related_name
    else:
        related_name = False

    kwargs: dict[str, Any] = {}
    if info.through_db_table:
        kwargs["through"] = info.through_db_table
    return (
        info.name,
        tortoise_fields.ManyToManyField(target_ref, related_name=related_name, **kwargs),  # type: ignore[arg-type]
    )
