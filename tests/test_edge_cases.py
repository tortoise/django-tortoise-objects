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


class TestClassNameMapCleanup:
    """Tests for class_name_map cleanup on generation failure."""

    def test_class_name_map_cleaned_on_generation_failure(self):
        """When a model fails generation, it is removed from class_name_map
        so FK references from other models are gracefully skipped."""
        from django_tortoise.generator import generate_tortoise_model_full

        class _ModelA:
            __name__ = "ModelA"
            __module__ = "tests.testapp.models"

        class _ModelB:
            __name__ = "ModelB"
            __module__ = "tests.testapp.models"

        # ModelA has only an unsupported field (no django_field, so MRO cannot help)
        fi_a = _make_field_info(
            name="weird_pk",
            internal_type="UnsupportedTypeXYZ",
            column="weird_pk",
            primary_key=True,
            django_field=None,
        )
        model_info_a = ModelInfo(
            model_class=_ModelA,
            app_label="test",
            model_name="modela",
            db_table="test_modela",
            fields=[fi_a],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="weird_pk",
        )

        # ModelB has a valid PK + FK to ModelA
        fi_b_pk = _make_field_info(
            name="id",
            internal_type="BigAutoField",
            column="id",
            primary_key=True,
        )
        fi_b_fk = _make_field_info(
            name="ref",
            internal_type="ForeignKey",
            column="ref_id",
            is_relation=True,
            related_model=_ModelA,
            related_model_label="test.ModelA",
            on_delete="CASCADE",
        )
        model_info_b = ModelInfo(
            model_class=_ModelB,
            app_label="test",
            model_name="modelb",
            db_table="test_modelb",
            fields=[fi_b_pk, fi_b_fk],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )

        class_name_map = {
            _ModelA: "ModelATortoise",
            _ModelB: "ModelBTortoise",
        }

        # ModelA generation fails (returns None)
        result_a = generate_tortoise_model_full(model_info_a, class_name_map=class_name_map)
        assert result_a is None

        # Remove ModelA from class_name_map (simulating what apps.py does)
        class_name_map.pop(_ModelA, None)

        # ModelB generation should succeed; FK to ModelA is gracefully skipped
        result_b = generate_tortoise_model_full(model_info_b, class_name_map=class_name_map)
        assert result_b is not None

    def test_class_name_map_cleaned_in_code_generator(self):
        """Same cleanup pattern for the code generator path."""
        from django_tortoise.code_generator import render_model_source

        class _ModelA:
            __name__ = "ModelA"
            __module__ = "tests.testapp.models"

        class _ModelB:
            __name__ = "ModelB"
            __module__ = "tests.testapp.models"

        # ModelA has only an unsupported field
        fi_a = _make_field_info(
            name="weird_pk",
            internal_type="UnsupportedTypeXYZ",
            column="weird_pk",
            primary_key=True,
            django_field=None,
        )
        model_info_a = ModelInfo(
            model_class=_ModelA,
            app_label="test",
            model_name="modela",
            db_table="test_modela",
            fields=[fi_a],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="weird_pk",
        )

        # ModelB has a valid PK + FK to ModelA
        fi_b_pk = _make_field_info(
            name="id",
            internal_type="BigAutoField",
            column="id",
            primary_key=True,
        )
        fi_b_fk = _make_field_info(
            name="ref",
            internal_type="ForeignKey",
            column="ref_id",
            is_relation=True,
            related_model=_ModelA,
            related_model_label="test.ModelA",
            on_delete="CASCADE",
        )
        model_info_b = ModelInfo(
            model_class=_ModelB,
            app_label="test",
            model_name="modelb",
            db_table="test_modelb",
            fields=[fi_b_pk, fi_b_fk],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )

        class_name_map = {
            _ModelA: "ModelATortoise",
            _ModelB: "ModelBTortoise",
        }

        # ModelA render fails (returns None)
        result_a = render_model_source(model_info_a, "django_tortoise", class_name_map)
        assert result_a is None

        # Remove ModelA from class_name_map (simulating what generate_tortoise_models does)
        class_name_map.pop(_ModelA, None)

        # ModelB render should succeed; FK to ModelA is gracefully skipped
        result_b = render_model_source(model_info_b, "django_tortoise", class_name_map)
        assert result_b is not None


class TestCustomFieldMROIntegration:
    """End-to-end integration tests with real Django custom field subclasses."""

    def test_convert_field_with_custom_pk(self):
        """convert_field succeeds for a custom CharField PK."""
        from django.db import models as django_models
        from tortoise import fields as tf

        class CustomIDField(django_models.CharField):
            def get_internal_type(self):
                return "CustomIDField"

        django_field = CustomIDField(max_length=36)
        info = _make_field_info(
            name="id",
            internal_type="CustomIDField",
            column="id",
            max_length=36,
            primary_key=True,
            django_field=django_field,
        )
        result = convert_field(info)
        assert result is not None
        assert isinstance(result, tf.CharField)
        assert result.pk is True

    def test_render_field_source_with_custom_pk(self):
        """render_field_source succeeds for a custom CharField PK."""
        from django.db import models as django_models

        from django_tortoise.code_generator import render_field_source

        class CustomIDField(django_models.CharField):
            def get_internal_type(self):
                return "CustomIDField"

        django_field = CustomIDField(max_length=36)
        info = _make_field_info(
            name="id",
            internal_type="CustomIDField",
            column="id",
            max_length=36,
            primary_key=True,
            django_field=django_field,
        )
        result = render_field_source(info)
        assert result is not None
        assert "fields.CharField(" in result

    def test_generate_tortoise_model_full_with_custom_pk(self):
        """generate_tortoise_model_full returns a valid model for custom PK."""
        from django.db import models as django_models

        from django_tortoise.generator import generate_tortoise_model_full

        class CustomIDField(django_models.CharField):
            def get_internal_type(self):
                return "CustomIDField"

        django_field = CustomIDField(max_length=36)
        fi = _make_field_info(
            name="id",
            internal_type="CustomIDField",
            column="id",
            max_length=36,
            primary_key=True,
            django_field=django_field,
        )

        class CustomPKModel:
            __module__ = "tests.testapp.models"

        model_info = ModelInfo(
            model_class=CustomPKModel,
            app_label="test",
            model_name="custompkmodel",
            db_table="test_custompkmodel",
            fields=[fi],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = generate_tortoise_model_full(model_info)
        assert result is not None
        assert result.__name__ == "CustomPKModelTortoise"

    def test_render_model_source_with_custom_pk(self):
        """render_model_source returns a valid ModelSourceResult for custom PK."""
        from django.db import models as django_models

        from django_tortoise.code_generator import ModelSourceResult, render_model_source

        class CustomIDField(django_models.CharField):
            def get_internal_type(self):
                return "CustomIDField"

        django_field = CustomIDField(max_length=36)
        fi = _make_field_info(
            name="id",
            internal_type="CustomIDField",
            column="id",
            max_length=36,
            primary_key=True,
            django_field=django_field,
        )

        class CustomPKModel:
            __module__ = "tests.testapp.models"

        model_info = ModelInfo(
            model_class=CustomPKModel,
            app_label="test",
            model_name="custompkmodel",
            db_table="test_custompkmodel",
            fields=[fi],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = render_model_source(model_info, "django_tortoise", {})
        assert result is not None
        assert isinstance(result, ModelSourceResult)
        assert "fields.CharField(" in result.source

    def test_custom_pk_model_with_fk_from_another_model(self):
        """ModelA with custom PK + ModelB with FK to ModelA both generate correctly."""
        from django.db import models as django_models

        from django_tortoise.generator import generate_tortoise_model_full

        class CustomIDField(django_models.CharField):
            def get_internal_type(self):
                return "CustomIDField"

        class ModelA:
            __module__ = "tests.testapp.models"

        class ModelB:
            __module__ = "tests.testapp.models"

        # ModelA: only field is CustomIDField PK
        django_field_a = CustomIDField(max_length=36)
        fi_a = _make_field_info(
            name="id",
            internal_type="CustomIDField",
            column="id",
            max_length=36,
            primary_key=True,
            django_field=django_field_a,
        )
        model_info_a = ModelInfo(
            model_class=ModelA,
            app_label="test",
            model_name="modela",
            db_table="test_modela",
            fields=[fi_a],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )

        # ModelB: BigAutoField PK + FK to ModelA
        fi_b_pk = _make_field_info(
            name="id",
            internal_type="BigAutoField",
            column="id",
            primary_key=True,
        )
        fi_b_fk = _make_field_info(
            name="ref",
            internal_type="ForeignKey",
            column="ref_id",
            is_relation=True,
            related_model=ModelA,
            related_model_label="test.ModelA",
            on_delete="CASCADE",
        )
        model_info_b = ModelInfo(
            model_class=ModelB,
            app_label="test",
            model_name="modelb",
            db_table="test_modelb",
            fields=[fi_b_pk, fi_b_fk],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )

        class_name_map = {
            ModelA: "ModelATortoise",
            ModelB: "ModelBTortoise",
        }

        # ModelA generates successfully (custom PK resolved via MRO)
        result_a = generate_tortoise_model_full(model_info_a, class_name_map=class_name_map)
        assert result_a is not None
        assert result_a.__name__ == "ModelATortoise"

        # ModelB generates successfully with FK to ModelA
        result_b = generate_tortoise_model_full(model_info_b, class_name_map=class_name_map)
        assert result_b is not None
        assert result_b.__name__ == "ModelBTortoise"
