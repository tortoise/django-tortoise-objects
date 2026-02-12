"""
Tests for the django_tortoise.fields module.

Validates that the field mapping registry contains converters for all
required Django field types and that converted Tortoise fields have the
correct types and parameters.
"""

import enum

from tortoise import fields as tf
from tortoise.fields.data import CharEnumFieldInstance, IntEnumFieldInstance

from django_tortoise.fields import FIELD_MAP, convert_field
from django_tortoise.introspection import FieldInfo


def _make_field_info(**overrides) -> FieldInfo:
    """Helper to create FieldInfo with sensible defaults."""
    defaults = dict(
        name="test_field",
        internal_type="CharField",
        column="test_field",
        primary_key=False,
        null=False,
        unique=False,
        has_default=False,
        default=None,
        max_length=100,
        max_digits=None,
        decimal_places=None,
        db_index=False,
        choices=None,
        enum_type=None,
        is_relation=False,
        related_model=None,
        related_model_label=None,
        on_delete=None,
        related_name=None,
        is_self_referential=False,
        many_to_many=False,
        through_model=None,
        through_db_table=None,
        is_auto_field=False,
        django_field=None,
    )
    defaults.update(overrides)
    return FieldInfo(**defaults)


class TestFieldMapCoverage:
    """Every field type from the PM spec has a converter registered."""

    def test_all_pm_spec_types_registered(self):
        required = [
            "AutoField",
            "BigAutoField",
            "SmallAutoField",
            "IntegerField",
            "BigIntegerField",
            "SmallIntegerField",
            "PositiveIntegerField",
            "PositiveBigIntegerField",
            "PositiveSmallIntegerField",
            "CharField",
            "TextField",
            "BooleanField",
            "DateField",
            "DateTimeField",
            "TimeField",
            "DurationField",
            "DecimalField",
            "FloatField",
            "BinaryField",
            "UUIDField",
            "JSONField",
            "FileField",
            "ImageField",
            "FilePathField",
            "SlugField",
            "EmailField",
            "URLField",
            "GenericIPAddressField",
        ]
        for ftype in required:
            assert ftype in FIELD_MAP, f"{ftype} not in FIELD_MAP"


class TestAutoFields:
    """Auto fields produce primary_key=True, generated=True."""

    def test_auto_field(self):
        info = _make_field_info(internal_type="AutoField", primary_key=True)
        result = convert_field(info)
        assert isinstance(result, tf.IntField)
        assert result.pk is True

    def test_big_auto_field(self):
        info = _make_field_info(internal_type="BigAutoField", primary_key=True)
        result = convert_field(info)
        assert isinstance(result, tf.BigIntField)
        assert result.pk is True

    def test_small_auto_field(self):
        info = _make_field_info(internal_type="SmallAutoField", primary_key=True)
        result = convert_field(info)
        assert isinstance(result, tf.SmallIntField)
        assert result.pk is True


class TestIntegerFields:
    """Integer field variants map to correct Tortoise field types."""

    def test_integer_field(self):
        info = _make_field_info(internal_type="IntegerField")
        result = convert_field(info)
        assert isinstance(result, tf.IntField)

    def test_big_integer_field(self):
        info = _make_field_info(internal_type="BigIntegerField")
        result = convert_field(info)
        assert isinstance(result, tf.BigIntField)

    def test_small_integer_field(self):
        info = _make_field_info(internal_type="SmallIntegerField")
        result = convert_field(info)
        assert isinstance(result, tf.SmallIntField)

    def test_positive_integer_field(self):
        info = _make_field_info(internal_type="PositiveIntegerField")
        result = convert_field(info)
        assert isinstance(result, tf.IntField)

    def test_positive_big_integer_field(self):
        info = _make_field_info(internal_type="PositiveBigIntegerField")
        result = convert_field(info)
        assert isinstance(result, tf.BigIntField)

    def test_positive_small_integer_field(self):
        info = _make_field_info(internal_type="PositiveSmallIntegerField")
        result = convert_field(info)
        assert isinstance(result, tf.SmallIntField)


class TestStringFields:
    """String fields preserve max_length and map correctly."""

    def test_char_field_max_length(self):
        info = _make_field_info(internal_type="CharField", max_length=200)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 200

    def test_char_field_default_max_length(self):
        info = _make_field_info(internal_type="CharField", max_length=None)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 255

    def test_text_field(self):
        info = _make_field_info(internal_type="TextField")
        result = convert_field(info)
        assert isinstance(result, tf.TextField)

    def test_slug_field(self):
        info = _make_field_info(internal_type="SlugField", max_length=50)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 50

    def test_email_field(self):
        info = _make_field_info(internal_type="EmailField", max_length=254)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 254

    def test_url_field(self):
        info = _make_field_info(internal_type="URLField", max_length=200)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 200

    def test_generic_ip_address_field(self):
        info = _make_field_info(internal_type="GenericIPAddressField")
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 39


class TestDateTimeFields:
    """Date/time fields map to correct Tortoise types."""

    def test_date_field(self):
        info = _make_field_info(internal_type="DateField")
        result = convert_field(info)
        assert isinstance(result, tf.DateField)

    def test_datetime_field(self):
        info = _make_field_info(internal_type="DateTimeField")
        result = convert_field(info)
        assert isinstance(result, tf.DatetimeField)

    def test_time_field(self):
        info = _make_field_info(internal_type="TimeField")
        result = convert_field(info)
        assert isinstance(result, tf.TimeField)

    def test_duration_field(self):
        info = _make_field_info(internal_type="DurationField")
        result = convert_field(info)
        assert isinstance(result, tf.TimeDeltaField)


class TestNumericFields:
    """Numeric fields preserve digits/precision params."""

    def test_decimal_field_params(self):
        info = _make_field_info(internal_type="DecimalField", max_digits=10, decimal_places=2)
        result = convert_field(info)
        assert isinstance(result, tf.DecimalField)
        assert result.max_digits == 10
        assert result.decimal_places == 2

    def test_float_field(self):
        info = _make_field_info(internal_type="FloatField")
        result = convert_field(info)
        assert isinstance(result, tf.FloatField)


class TestOtherFields:
    """Binary, UUID, JSON, and file fields."""

    def test_binary_field(self):
        info = _make_field_info(internal_type="BinaryField")
        result = convert_field(info)
        assert isinstance(result, tf.BinaryField)

    def test_uuid_field(self):
        info = _make_field_info(internal_type="UUIDField")
        result = convert_field(info)
        assert isinstance(result, tf.UUIDField)

    def test_json_field(self):
        info = _make_field_info(internal_type="JSONField")
        result = convert_field(info)
        assert isinstance(result, tf.JSONField)

    def test_boolean_field(self):
        info = _make_field_info(internal_type="BooleanField")
        result = convert_field(info)
        assert isinstance(result, tf.BooleanField)

    def test_file_field(self):
        info = _make_field_info(internal_type="FileField", max_length=None)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 100

    def test_image_field(self):
        info = _make_field_info(internal_type="ImageField", max_length=None)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 100

    def test_file_path_field(self):
        info = _make_field_info(internal_type="FilePathField", max_length=None)
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert result.max_length == 100


class TestCommonKwargs:
    """Common field kwargs are correctly forwarded."""

    def test_null_field(self):
        info = _make_field_info(internal_type="IntegerField", null=True)
        result = convert_field(info)
        assert result.null is True

    def test_unique_field(self):
        info = _make_field_info(internal_type="IntegerField", unique=True)
        result = convert_field(info)
        assert result.unique is True

    def test_db_index_field(self):
        info = _make_field_info(internal_type="IntegerField", db_index=True)
        result = convert_field(info)
        # Tortoise stores db_index as 'index' on the field instance
        assert result.index is True

    def test_source_field_mapping(self):
        info = _make_field_info(
            internal_type="CharField",
            name="title",
            column="custom_title",
            max_length=100,
        )
        result = convert_field(info)
        assert result.source_field == "custom_title"

    def test_no_source_field_when_column_matches_name(self):
        info = _make_field_info(
            internal_type="CharField",
            name="title",
            column="title",
            max_length=100,
        )
        result = convert_field(info)
        assert result.source_field is None or result.source_field == "title"

    def test_default_value(self):
        info = _make_field_info(internal_type="IntegerField", has_default=True, default=42)
        result = convert_field(info)
        assert result.default == 42

    def test_callable_default(self):
        def my_default():
            return []

        info = _make_field_info(internal_type="JSONField", has_default=True, default=my_default)
        result = convert_field(info)
        assert result.default is my_default


class _IntStatus(int, enum.Enum):
    ACTIVE = 1
    INACTIVE = 2


class _StrColor(str, enum.Enum):
    RED = "red"
    BLUE = "blue"


class TestEnumFields:
    """Enum-backed choices produce IntEnumField / CharEnumField."""

    def test_int_field_with_int_enum(self):
        info = _make_field_info(internal_type="IntegerField", enum_type=_IntStatus)
        result = convert_field(info)
        assert isinstance(result, IntEnumFieldInstance)
        assert result.enum_type is _IntStatus

    def test_char_field_with_str_enum(self):
        info = _make_field_info(internal_type="CharField", enum_type=_StrColor, max_length=10)
        result = convert_field(info)
        assert isinstance(result, CharEnumFieldInstance)
        assert result.enum_type is _StrColor

    def test_int_field_plain_choices_no_enum(self):
        info = _make_field_info(
            internal_type="IntegerField",
            choices=[(1, "Low"), (2, "High")],
            enum_type=None,
        )
        result = convert_field(info)
        assert isinstance(result, tf.IntField)
        assert not isinstance(result, IntEnumFieldInstance)

    def test_char_field_plain_choices_no_enum(self):
        info = _make_field_info(
            internal_type="CharField",
            choices=[("a", "A"), ("b", "B")],
            enum_type=None,
            max_length=10,
        )
        result = convert_field(info)
        assert isinstance(result, tf.CharField)
        assert not isinstance(result, CharEnumFieldInstance)

    def test_enum_field_preserves_null_and_default(self):
        info = _make_field_info(
            internal_type="IntegerField",
            enum_type=_IntStatus,
            null=True,
            has_default=True,
            default=_IntStatus.ACTIVE,
        )
        result = convert_field(info)
        assert isinstance(result, IntEnumFieldInstance)
        assert result.null is True
        assert result.default is _IntStatus.ACTIVE

    def test_positive_int_field_with_enum(self):
        info = _make_field_info(internal_type="PositiveIntegerField", enum_type=_IntStatus)
        result = convert_field(info)
        assert isinstance(result, IntEnumFieldInstance)

    def test_small_int_field_with_enum(self):
        info = _make_field_info(internal_type="SmallIntegerField", enum_type=_IntStatus)
        result = convert_field(info)
        assert isinstance(result, IntEnumFieldInstance)

    def test_big_int_field_with_enum(self):
        info = _make_field_info(internal_type="BigIntegerField", enum_type=_IntStatus)
        result = convert_field(info)
        assert isinstance(result, IntEnumFieldInstance)


class TestUnsupportedField:
    """Unsupported fields return None with a warning log."""

    def test_unsupported_field_returns_none(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="django_tortoise"):
            info = _make_field_info(internal_type="UnknownFieldXYZ")
            result = convert_field(info)
        assert result is None
        assert "Unsupported" in caplog.text
