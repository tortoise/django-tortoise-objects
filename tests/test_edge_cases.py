"""
Tests for edge cases and error handling (Phase 5, Step 5.1).

Covers callable defaults, None defaults, abstract models, proxy models,
unmanaged models, unsupported fields, and other boundary conditions.
"""

import uuid

from django_tortoise.fields import _common_kwargs, convert_field
from django_tortoise.introspection import FieldInfo, ModelInfo, should_skip_model


def _make_field_info(**overrides) -> FieldInfo:
    """Helper to create FieldInfo with sensible defaults."""
    defaults = dict(
        name="test",
        internal_type="CharField",
        column="test",
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


class TestCallableDefaults:
    """Tests for callable default handling."""

    def test_callable_default_passed_through(self):
        """Callable defaults (like uuid.uuid4) should be passed through."""
        info = _make_field_info(internal_type="UUIDField", has_default=True, default=uuid.uuid4)
        result = convert_field(info)
        assert result.default is uuid.uuid4

    def test_dict_callable_default(self):
        """dict as default (callable) should be passed through."""
        info = _make_field_info(internal_type="JSONField", has_default=True, default=dict)
        result = convert_field(info)
        assert result.default is dict

    def test_list_callable_default(self):
        """list as default (callable) should be passed through."""
        info = _make_field_info(internal_type="JSONField", has_default=True, default=list)
        result = convert_field(info)
        assert result.default is list


class TestNoneDefault:
    """Tests for None default value handling."""

    def test_none_default_when_has_default_true(self):
        """When has_default=True and default=None, default should be set to None."""
        info = _make_field_info(
            internal_type="IntegerField", has_default=True, default=None, null=True
        )
        kwargs = _common_kwargs(info)
        assert "default" in kwargs
        assert kwargs["default"] is None

    def test_no_default_when_has_default_false(self):
        """If has_default is False, no default kwarg should be set."""
        info = _make_field_info(internal_type="IntegerField", has_default=False)
        kwargs = _common_kwargs(info)
        assert "default" not in kwargs

    def test_string_default_empty(self):
        """Empty string default should be passed through."""
        info = _make_field_info(internal_type="CharField", has_default=True, default="")
        kwargs = _common_kwargs(info)
        assert "default" in kwargs
        assert kwargs["default"] == ""

    def test_zero_default(self):
        """Zero default should be passed through."""
        info = _make_field_info(internal_type="IntegerField", has_default=True, default=0)
        kwargs = _common_kwargs(info)
        assert "default" in kwargs
        assert kwargs["default"] == 0

    def test_false_default(self):
        """False default should be passed through."""
        info = _make_field_info(internal_type="BooleanField", has_default=True, default=False)
        kwargs = _common_kwargs(info)
        assert "default" in kwargs
        assert kwargs["default"] is False


class TestShouldSkipModel:
    """Tests for model skip conditions."""

    def test_skip_abstract_model(self):
        info = ModelInfo(
            model_class=object,
            app_label="t",
            model_name="A",
            db_table="",
            fields=[],
            unique_together=[],
            is_abstract=True,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        skip, reason = should_skip_model(info)
        assert skip
        assert "abstract" in reason.lower()

    def test_skip_proxy_model(self):
        info = ModelInfo(
            model_class=object,
            app_label="t",
            model_name="P",
            db_table="",
            fields=[],
            unique_together=[],
            is_abstract=False,
            is_proxy=True,
            is_managed=True,
            pk_name="id",
        )
        skip, reason = should_skip_model(info)
        assert skip
        assert "proxy" in reason.lower()

    def test_skip_no_fields(self):
        info = ModelInfo(
            model_class=object,
            app_label="t",
            model_name="E",
            db_table="",
            fields=[],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        skip, reason = should_skip_model(info)
        assert skip
        assert "no concrete fields" in reason.lower()

    def test_unmanaged_model_not_skipped(self):
        """Unmanaged models (managed=False) should NOT be skipped."""
        info = ModelInfo(
            model_class=object,
            app_label="t",
            model_name="U",
            db_table="some_table",
            fields=[_make_field_info(internal_type="IntegerField")],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=False,
            pk_name="id",
        )
        skip, _ = should_skip_model(info)
        assert not skip


class TestUnsupportedField:
    """Tests for unsupported field handling."""

    def test_unsupported_field_returns_none(self, caplog):
        """Unknown field types produce a warning and return None."""
        info = _make_field_info(internal_type="CompositePKField")
        result = convert_field(info)
        assert result is None

    def test_unsupported_field_logs_warning(self, caplog):
        """Unknown field types log a warning."""
        import logging

        with caplog.at_level(logging.WARNING, logger="django_tortoise"):
            info = _make_field_info(internal_type="UnknownFieldXYZ")
            convert_field(info)
        assert "Unsupported" in caplog.text
        assert "UnknownFieldXYZ" in caplog.text


class TestSourceFieldMapping:
    """Tests for source_field (column name) mapping."""

    def test_source_field_when_column_differs(self):
        info = _make_field_info(internal_type="CharField", name="title", column="custom_title")
        kwargs = _common_kwargs(info)
        assert kwargs["source_field"] == "custom_title"

    def test_no_source_field_when_column_matches(self):
        info = _make_field_info(internal_type="CharField", name="title", column="title")
        kwargs = _common_kwargs(info)
        assert "source_field" not in kwargs
