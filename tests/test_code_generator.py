"""
Tests for the django_tortoise.code_generator module.

Validates that the source code rendering functions produce correct Python
source strings from FieldInfo/ModelInfo dataclasses.
"""

import ast
import enum

from django_tortoise.code_generator import (
    SOURCE_FIELD_MAP,
    ModelSourceResult,
    _common_kwargs_source,
    render_app_module,
    render_field_source,
    render_model_source,
    render_relation_field_source,
)
from django_tortoise.fields import FIELD_MAP
from django_tortoise.introspection import FieldInfo, ModelInfo


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


# --- Test enums ---


class _IntStatus(int, enum.Enum):
    DRAFT = 1
    PUBLISHED = 2


class _StrColor(str, enum.Enum):
    RED = "red"
    BLUE = "blue"


# --- Dummy model classes for class_name_map ---


class _DummyCategory:
    __name__ = "Category"
    __module__ = "tests.testapp.models"


class _DummyTag:
    __name__ = "Tag"
    __module__ = "tests.testapp.models"


class _DummyArticle:
    __name__ = "Article"
    __module__ = "tests.testapp.models"


class _DummyComment:
    __name__ = "Comment"
    __module__ = "tests.testapp.models"


# ---------------------------------------------------------------------------
# TC-1.1 through TC-1.4: _common_kwargs_source
# ---------------------------------------------------------------------------


class TestCommonKwargsSource:
    """Tests for _common_kwargs_source."""

    def test_null_kwarg(self):
        """TC-1.1: produces correct kwargs for null."""
        info = _make_field_info(null=True)
        result = _common_kwargs_source(info)
        assert result["null"] == "True"

    def test_unique_not_in_output(self):
        """unique is not included in kwargs source (DB schema handles it)."""
        info = _make_field_info(unique=True)
        result = _common_kwargs_source(info)
        assert "unique" not in result

    def test_primary_key_kwarg(self):
        """TC-1.1: produces correct kwargs for primary_key."""
        info = _make_field_info(primary_key=True)
        result = _common_kwargs_source(info)
        assert result["primary_key"] == "True"

    def test_db_index_not_in_output(self):
        """db_index is not included in kwargs source (DB schema handles it)."""
        info = _make_field_info(db_index=True)
        result = _common_kwargs_source(info)
        assert "db_index" not in result

    def test_simple_literal_default_int(self):
        """TC-1.2: handles int default."""
        info = _make_field_info(has_default=True, default=42)
        result = _common_kwargs_source(info)
        assert result["default"] == "42"

    def test_simple_literal_default_str(self):
        """TC-1.2: handles str default."""
        info = _make_field_info(has_default=True, default="hello")
        result = _common_kwargs_source(info)
        assert result["default"] == "'hello'"

    def test_simple_literal_default_bool(self):
        """TC-1.2: handles bool default."""
        info = _make_field_info(has_default=True, default=False)
        result = _common_kwargs_source(info)
        assert result["default"] == "False"

    def test_simple_literal_default_none(self):
        """TC-1.2: handles None default."""
        info = _make_field_info(has_default=True, default=None)
        result = _common_kwargs_source(info)
        assert result["default"] == "None"

    def test_callable_default_dict(self):
        """TC-1.3: handles dict callable default."""
        info = _make_field_info(has_default=True, default=dict)
        result = _common_kwargs_source(info)
        assert result["default"] == "dict"

    def test_callable_default_list(self):
        """TC-1.3: handles list callable default."""
        info = _make_field_info(has_default=True, default=list)
        result = _common_kwargs_source(info)
        assert result["default"] == "list"

    def test_enum_member_default(self):
        """TC-1.4: handles enum member default."""
        info = _make_field_info(has_default=True, default=_IntStatus.DRAFT)
        result = _common_kwargs_source(info)
        assert result["default"] == "_IntStatus.DRAFT"

    def test_unserializable_callable_emits_none_with_todo(self):
        """Unserializable callable emits None with TODO sentinel."""

        def my_callable():
            return 42

        info = _make_field_info(has_default=True, default=my_callable)
        result = _common_kwargs_source(info)
        assert result["default"] == "None"
        assert "# TODO" in result

    def test_no_default_when_has_default_false(self):
        """No default kwarg when has_default is False."""
        info = _make_field_info(has_default=False)
        result = _common_kwargs_source(info)
        assert "default" not in result

    def test_source_field_when_column_differs(self):
        """source_field emitted when column differs from name."""
        info = _make_field_info(name="title", column="custom_title")
        result = _common_kwargs_source(info)
        assert result["source_field"] == "'custom_title'"

    def test_no_source_field_when_column_matches(self):
        """No source_field when column matches name."""
        info = _make_field_info(name="title", column="title")
        result = _common_kwargs_source(info)
        assert "source_field" not in result


# ---------------------------------------------------------------------------
# TC-1.5: SOURCE_FIELD_MAP coverage
# ---------------------------------------------------------------------------


class TestSourceFieldMapCoverage:
    """Tests for SOURCE_FIELD_MAP completeness."""

    def test_covers_all_field_map_types(self):
        """TC-1.5: Every key in FIELD_MAP is also in SOURCE_FIELD_MAP."""
        for key in FIELD_MAP:
            assert key in SOURCE_FIELD_MAP, f"{key} not in SOURCE_FIELD_MAP"


# ---------------------------------------------------------------------------
# TC-1.6 through TC-1.9: Individual field source renderers
# ---------------------------------------------------------------------------


class TestAutoFieldSource:
    """Tests for auto field source rendering."""

    def test_auto_field(self):
        info = _make_field_info(internal_type="AutoField", primary_key=True)
        result = SOURCE_FIELD_MAP["AutoField"](info)
        assert result == "fields.IntField(primary_key=True, generated=True)"

    def test_big_auto_field(self):
        """TC-1.6: BigAutoField renders correctly."""
        info = _make_field_info(internal_type="BigAutoField", primary_key=True)
        result = SOURCE_FIELD_MAP["BigAutoField"](info)
        assert result == "fields.BigIntField(primary_key=True, generated=True)"

    def test_small_auto_field(self):
        info = _make_field_info(internal_type="SmallAutoField", primary_key=True)
        result = SOURCE_FIELD_MAP["SmallAutoField"](info)
        assert result == "fields.SmallIntField(primary_key=True, generated=True)"


class TestCharFieldSource:
    """Tests for CharField source rendering."""

    def test_char_field_with_max_length(self):
        """TC-1.7: CharField renders with max_length."""
        info = _make_field_info(internal_type="CharField", max_length=200)
        result = SOURCE_FIELD_MAP["CharField"](info)
        assert "fields.CharField(" in result
        assert "max_length=200" in result

    def test_char_field_default_max_length(self):
        info = _make_field_info(internal_type="CharField", max_length=None)
        result = SOURCE_FIELD_MAP["CharField"](info)
        assert "max_length=255" in result


class TestIntEnumFieldSource:
    """Tests for enum-backed field source rendering."""

    def test_int_enum_field(self):
        """TC-1.8: IntegerField with enum_type renders IntEnumField."""
        info = _make_field_info(internal_type="IntegerField", enum_type=_IntStatus)
        result = SOURCE_FIELD_MAP["IntegerField"](info)
        assert "fields.IntEnumField(_IntStatus" in result

    def test_char_enum_field(self):
        info = _make_field_info(internal_type="CharField", enum_type=_StrColor, max_length=10)
        result = SOURCE_FIELD_MAP["CharField"](info)
        assert "fields.CharEnumField(_StrColor" in result
        assert "max_length=10" in result


class TestDecimalFieldSource:
    """Tests for DecimalField source rendering."""

    def test_decimal_field(self):
        """TC-1.9: DecimalField renders max_digits and decimal_places."""
        info = _make_field_info(internal_type="DecimalField", max_digits=10, decimal_places=2)
        result = SOURCE_FIELD_MAP["DecimalField"](info)
        assert "max_digits=10" in result
        assert "decimal_places=2" in result


# ---------------------------------------------------------------------------
# TC-1.10 through TC-1.12: Relational field source rendering
# ---------------------------------------------------------------------------


class TestRelationFieldSource:
    """Tests for relational field source rendering."""

    def test_fk_source(self):
        """TC-1.10: FK renders correctly."""
        info = _make_field_info(
            name="category",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
            related_name="articles",
            column="category_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        field_name, source = result
        assert field_name == "category"
        assert 'ForeignKeyField("django_tortoise.CategoryTortoise"' in source
        assert "related_name='articles'" in source
        assert "OnDelete.CASCADE" in source

    def test_m2m_with_through_table(self):
        """TC-1.11: M2M with through table renders correctly."""
        info = _make_field_info(
            name="tags",
            internal_type="ManyToManyField",
            is_relation=True,
            related_model=_DummyTag,
            related_model_label="testapp.Tag",
            related_name="articles",
            many_to_many=True,
            through_db_table="testapp_article_tags",
        )
        class_name_map = {_DummyTag: "TagTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        field_name, source = result
        assert field_name == "tags"
        assert 'ManyToManyField("django_tortoise.TagTortoise"' in source
        assert "through='testapp_article_tags'" in source

    def test_returns_none_for_unknown_target(self):
        """TC-1.12: Returns None when target not in class_name_map."""
        info = _make_field_info(
            name="category",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
        )
        result = render_relation_field_source(info, "django_tortoise", {})
        assert result is None

    def test_o2o_source(self):
        info = _make_field_info(
            name="user",
            internal_type="OneToOneField",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
            related_name="profile",
            column="user_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        field_name, source = result
        assert field_name == "user"
        assert 'OneToOneField("django_tortoise.CategoryTortoise"' in source
        assert "OnDelete.CASCADE" in source

    def test_related_name_none_renders_false(self):
        """When related_name is None, renders related_name=False."""
        info = _make_field_info(
            name="category",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
            related_name=None,
            column="category_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        _, source = result
        assert "related_name=False" in source

    def test_related_name_plus_renders_false(self):
        """When related_name is '+', renders related_name=False."""
        info = _make_field_info(
            name="category",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
            related_name="+",
            column="category_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        _, source = result
        assert "related_name=False" in source


# ---------------------------------------------------------------------------
# TC-1.13 through TC-1.15: render_model_source
# ---------------------------------------------------------------------------


class TestRenderModelSource:
    """Tests for render_model_source using real introspected models."""

    def test_category_model(self):
        """TC-1.13: render_model_source for Category."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        class_name_map = {Category: "CategoryTortoise"}
        result = render_model_source(model_info, "django_tortoise", class_name_map)
        assert result is not None
        assert result.class_name == "CategoryTortoise"
        assert "class CategoryTortoise(Model):" in result.source
        assert 'table = "testapp_category"' in result.source
        assert 'app = "django_tortoise"' in result.source

    def test_article_with_relations(self):
        """TC-1.14: render_model_source includes relational fields."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Article, Category, Tag

        model_info = introspect_model(Article)
        class_name_map = {
            Article: "ArticleTortoise",
            Category: "CategoryTortoise",
            Tag: "TagTortoise",
        }
        result = render_model_source(model_info, "django_tortoise", class_name_map)
        assert result is not None
        assert "category = fields.ForeignKeyField(" in result.source
        assert "tags = fields.ManyToManyField(" in result.source

    def test_unique_together_with_unconverted_fields_skipped(self):
        """TC-1.15: unique_together referencing unconverted fields is omitted."""
        # Create a ModelInfo with unique_together referencing a non-existent field
        fi = _make_field_info(name="id", internal_type="BigAutoField", primary_key=True)

        class _DummyModel:
            __name__ = "Dummy"
            __module__ = "tests.testapp.models"

        model_info = ModelInfo(
            model_class=_DummyModel,
            app_label="test",
            model_name="dummy",
            db_table="test_dummy",
            fields=[fi],
            unique_together=[("id", "nonexistent_field")],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = render_model_source(model_info, "django_tortoise", {})
        assert result is not None
        assert "unique_together" not in result.source

    def test_valid_unique_together_included(self):
        """unique_together with all converted fields is included."""
        fi_id = _make_field_info(
            name="id", internal_type="BigAutoField", primary_key=True, column="id"
        )
        fi_name = _make_field_info(
            name="name", internal_type="CharField", max_length=100, column="name"
        )

        class _DummyModel:
            __name__ = "Dummy"
            __module__ = "tests.testapp.models"

        model_info = ModelInfo(
            model_class=_DummyModel,
            app_label="test",
            model_name="dummy",
            db_table="test_dummy",
            fields=[fi_id, fi_name],
            unique_together=[("id", "name")],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = render_model_source(model_info, "django_tortoise", {})
        assert result is not None
        assert "unique_together" in result.source

    def test_no_convertible_fields_returns_none(self):
        """Model with no convertible fields returns None."""
        fi = _make_field_info(name="weird", internal_type="UnknownXYZ")

        class _DummyModel:
            __name__ = "Empty"
            __module__ = "tests.testapp.models"

        model_info = ModelInfo(
            model_class=_DummyModel,
            app_label="test",
            model_name="empty",
            db_table="test_empty",
            fields=[fi],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = render_model_source(model_info, "django_tortoise", {})
        assert result is None

    def test_source_is_valid_python(self):
        """Generated source for Category is syntactically valid Python."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        class_name_map = {Category: "CategoryTortoise"}
        result = render_model_source(model_info, "django_tortoise", class_name_map)
        assert result is not None
        # Should parse without raising
        ast.parse(result.source)


# ---------------------------------------------------------------------------
# TC-1.16: render_app_module
# ---------------------------------------------------------------------------


class TestRenderAppModule:
    """Tests for render_app_module."""

    def test_produces_complete_module(self):
        """TC-1.16: Produces complete Python module."""
        result1 = ModelSourceResult(
            class_name="CategoryTortoise",
            source='class CategoryTortoise(Model):\n    name = fields.CharField(max_length=100)\n\n    class Meta:\n        table = "testapp_category"\n        app = "django_tortoise"',
            imports={"from tortoise import fields", "from tortoise.models import Model"},
        )
        result2 = ModelSourceResult(
            class_name="TagTortoise",
            source='class TagTortoise(Model):\n    name = fields.CharField(max_length=50)\n\n    class Meta:\n        table = "testapp_tag"\n        app = "django_tortoise"',
            imports={"from tortoise import fields", "from tortoise.models import Model"},
        )
        output = render_app_module([result1, result2], "testapp")
        assert output.startswith("# Auto-generated")
        assert "from tortoise import fields" in output
        assert "from tortoise.models import Model" in output
        assert "class CategoryTortoise(Model):" in output
        assert "class TagTortoise(Model):" in output
        assert output.endswith("\n")
        # Should be valid Python
        ast.parse(output)

    def test_imports_are_sorted(self):
        """Imports are sorted in the output."""
        result = ModelSourceResult(
            class_name="Test",
            source='class Test(Model):\n    pass\n\n    class Meta:\n        table = "t"\n        app = "a"',
            imports={
                "from tortoise.models import Model",
                "from tortoise import fields",
                "from app.models import Status",
            },
        )
        output = render_app_module([result], "test")
        lines = output.split("\n")
        import_lines = [line for line in lines if line.startswith("from ")]
        assert import_lines == sorted(import_lines)

    def test_two_classes_separated_by_blank_lines(self):
        """Model classes are separated by blank lines."""
        result1 = ModelSourceResult(
            class_name="A",
            source='class A(Model):\n    pass\n\n    class Meta:\n        table = "a"\n        app = "t"',
            imports=set(),
        )
        result2 = ModelSourceResult(
            class_name="B",
            source='class B(Model):\n    pass\n\n    class Meta:\n        table = "b"\n        app = "t"',
            imports=set(),
        )
        output = render_app_module([result1, result2], "test")
        # Classes should be separated by blank lines
        assert "class A(Model):" in output
        assert "class B(Model):" in output


# ---------------------------------------------------------------------------
# TC-1.17: source_field emitted when column differs
# ---------------------------------------------------------------------------


class TestSourceFieldEmission:
    """Tests for source_field emission."""

    def test_source_field_emitted(self):
        """TC-1.17: source_field emitted when column differs from name."""
        info = _make_field_info(
            name="title",
            column="custom_title",
            internal_type="CharField",
            max_length=200,
        )
        result = SOURCE_FIELD_MAP["CharField"](info)
        assert "source_field='custom_title'" in result


# ---------------------------------------------------------------------------
# TC-1.18: enum field includes import
# ---------------------------------------------------------------------------


class TestEnumImport:
    """Tests for enum import in render_model_source."""

    def test_enum_field_includes_import(self):
        """TC-1.18: render_model_source for model with enum field includes enum import."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import EnumTestModel

        model_info = introspect_model(EnumTestModel)
        class_name_map = {EnumTestModel: "EnumTestModelTortoise"}
        result = render_model_source(model_info, "django_tortoise", class_name_map)
        assert result is not None
        # Should include import for the Status enum class
        has_status_import = any("Status" in imp for imp in result.imports)
        assert has_status_import, f"Expected Status import in {result.imports}"


# ---------------------------------------------------------------------------
# TC-3.1, TC-3.2: Semantic correctness -- field names match runtime generator
# ---------------------------------------------------------------------------


def _extract_field_names_from_source(source: str) -> set[str]:
    """Parse class source and extract field assignment names (top-level only, not Meta)."""
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name != "Meta":
            for item in node.body:
                # Only top-level assignments, skip inner classes like Meta
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
    return names


class TestSemanticCorrectness:
    """Compare generated source against runtime generator output."""

    def _get_runtime_field_names(self, model_info, class_name_map):
        """Get field names from the runtime generator."""
        from django_tortoise.generator import generate_tortoise_model_full

        tortoise_model = generate_tortoise_model_full(model_info, class_name_map=class_name_map)
        if tortoise_model is None:
            return set()
        # Get field names from _meta.fields_map, excluding internal descriptors
        # Tortoise adds *_id fields for FK descriptors
        field_names = set()
        for name in tortoise_model._meta.fields_map:
            # Skip the Tortoise-internal reverse and _id descriptor fields
            if name.endswith("_id") and name[:-3] in tortoise_model._meta.fields_map:
                continue
            field_names.add(name)
        return field_names

    def _get_source_field_names(self, model_info, class_name_map):
        """Get field names from the source code generator."""
        result = render_model_source(model_info, "django_tortoise", class_name_map)
        if result is None:
            return set()
        return _extract_field_names_from_source(result.source)

    def _build_full_class_name_map(self):
        """Build class_name_map for all testapp models."""
        from django.contrib.auth.models import User

        from tests.testapp.models import (
            Article,
            Category,
            Comment,
            EnumTestModel,
            Profile,
            Tag,
        )

        return {
            Category: "CategoryTortoise",
            Tag: "TagTortoise",
            Article: "ArticleTortoise",
            Comment: "CommentTortoise",
            EnumTestModel: "EnumTestModelTortoise",
            Profile: "ProfileTortoise",
            User: "UserTortoise",
        }

    def test_category_field_names_match(self):
        """TC-3.1: Category field names match between source and runtime."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Category

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(Category)
        source_names = self._get_source_field_names(model_info, class_name_map)
        runtime_names = self._get_runtime_field_names(model_info, class_name_map)
        assert source_names == runtime_names

    def test_article_field_names_match(self):
        """TC-3.2: Article field names (with relations) match."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Article

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(Article)
        source_names = self._get_source_field_names(model_info, class_name_map)
        runtime_names = self._get_runtime_field_names(model_info, class_name_map)
        # Both should include category (FK) and tags (M2M)
        assert "category" in source_names
        assert "tags" in source_names
        assert source_names == runtime_names

    def test_tag_field_names_match(self):
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Tag

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(Tag)
        source_names = self._get_source_field_names(model_info, class_name_map)
        runtime_names = self._get_runtime_field_names(model_info, class_name_map)
        assert source_names == runtime_names

    def test_comment_field_names_match(self):
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Comment

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(Comment)
        source_names = self._get_source_field_names(model_info, class_name_map)
        runtime_names = self._get_runtime_field_names(model_info, class_name_map)
        assert source_names == runtime_names

    def test_enum_test_model_field_names_match(self):
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import EnumTestModel

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(EnumTestModel)
        source_names = self._get_source_field_names(model_info, class_name_map)
        runtime_names = self._get_runtime_field_names(model_info, class_name_map)
        assert source_names == runtime_names

    def test_profile_field_names_match(self):
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Profile

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(Profile)
        source_names = self._get_source_field_names(model_info, class_name_map)
        runtime_names = self._get_runtime_field_names(model_info, class_name_map)
        assert source_names == runtime_names

    def test_meta_table_matches_runtime(self):
        """Verify Meta.table in source matches runtime model's Meta.table."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Category

        class_name_map = self._build_full_class_name_map()
        model_info = introspect_model(Category)
        result = render_model_source(model_info, "django_tortoise", class_name_map)
        assert result is not None
        assert f'table = "{model_info.db_table}"' in result.source

    def test_all_model_sources_are_valid_python(self):
        """Generated source for all test models is syntactically valid."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import (
            Article,
            Category,
            Comment,
            EnumTestModel,
            Profile,
            Tag,
        )

        class_name_map = self._build_full_class_name_map()
        for model_cls in [Category, Tag, Article, Comment, EnumTestModel, Profile]:
            model_info = introspect_model(model_cls)
            result = render_model_source(model_info, "django_tortoise", class_name_map)
            assert result is not None, f"render_model_source returned None for {model_cls.__name__}"
            ast.parse(result.source)


# ---------------------------------------------------------------------------
# TC-3.3 through TC-3.5: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for the code generator."""

    def test_self_referential_fk(self):
        """TC-3.3: Self-referential FK uses correct target ref."""
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Comment

        model_info = introspect_model(Comment)
        class_name_map = {Comment: "CommentTortoise"}
        # Also need Article in map for the article FK
        from tests.testapp.models import Article

        class_name_map[Article] = "ArticleTortoise"

        result = render_model_source(model_info, "django_tortoise", class_name_map)
        assert result is not None
        # The parent FK should reference CommentTortoise
        assert '"django_tortoise.CommentTortoise"' in result.source

    def test_disabled_reverse_relation(self):
        """TC-3.4: related_name='+' renders as related_name=False."""
        info = _make_field_info(
            name="thing",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
            related_name="+",
            column="thing_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        _, source = result
        assert "related_name=False" in source

    def test_fk_to_excluded_model_returns_none(self):
        """FK to model not in class_name_map returns None (graceful skip)."""

        class _ExcludedModel:
            __name__ = "Excluded"
            __module__ = "tests.testapp.models"

        info = _make_field_info(
            name="ref",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_ExcludedModel,
            related_model_label="testapp.Excluded",
            on_delete="CASCADE",
            column="ref_id",
        )
        result = render_relation_field_source(info, "django_tortoise", {})
        assert result is None

    def test_fk_source_field_column(self):
        """FK field with column different from name emits source_field."""
        info = _make_field_info(
            name="category",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="CASCADE",
            related_name="articles",
            column="category_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        _, source = result
        assert "source_field='category_id'" in source

    def test_unsupported_field_skipped_with_comment(self):
        """TC-3.5: Unsupported field type is skipped with a comment."""
        fi_id = _make_field_info(
            name="id", internal_type="BigAutoField", primary_key=True, column="id"
        )
        fi_unknown = _make_field_info(name="weird", internal_type="UnknownXYZ", column="weird")

        class _DummyModel:
            __name__ = "WithUnknown"
            __module__ = "tests.testapp.models"

        model_info = ModelInfo(
            model_class=_DummyModel,
            app_label="test",
            model_name="withunknown",
            db_table="test_withunknown",
            fields=[fi_id, fi_unknown],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = render_model_source(model_info, "django_tortoise", {})
        assert result is not None
        # The unknown field should have a skip comment
        assert "# Skipped unsupported field: weird" in result.source
        # But the model should still have the id field
        assert "id = fields.BigIntField(" in result.source

    def test_unsupported_field_render_returns_none(self):
        """render_field_source returns None for unsupported types."""
        info = _make_field_info(internal_type="UnknownXYZ")
        result = render_field_source(info)
        assert result is None

    def test_on_delete_protect_maps_to_restrict(self):
        """Django PROTECT maps to Tortoise RESTRICT in source."""
        info = _make_field_info(
            name="ref",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="PROTECT",
            related_name="refs",
            column="ref_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        _, source = result
        assert "OnDelete.RESTRICT" in source

    def test_on_delete_do_nothing_maps_to_no_action(self):
        """Django DO_NOTHING maps to Tortoise NO_ACTION in source."""
        info = _make_field_info(
            name="ref",
            internal_type="ForeignKey",
            is_relation=True,
            related_model=_DummyCategory,
            related_model_label="testapp.Category",
            on_delete="DO_NOTHING",
            related_name="refs",
            column="ref_id",
        )
        class_name_map = {_DummyCategory: "CategoryTortoise"}
        result = render_relation_field_source(info, "django_tortoise", class_name_map)
        assert result is not None
        _, source = result
        assert "OnDelete.NO_ACTION" in source
