"""
Tests for the django_tortoise.generator module.

Validates that ``generate_tortoise_model()`` creates valid Tortoise model
classes from introspected Django model metadata.
"""

from tortoise import models as tortoise_models

from django_tortoise.generator import generate_tortoise_model
from django_tortoise.introspection import ModelInfo, introspect_model


class TestGenerateBasicModel:
    """generate_tortoise_model produces correct Tortoise model classes."""

    def test_returns_model_class(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert tortoise_model is not None

    def test_model_name(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert tortoise_model.__name__ == "CategoryTortoise"

    def test_is_tortoise_model_subclass(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert issubclass(tortoise_model, tortoise_models.Model)

    def test_model_for_tag(self):
        from tests.testapp.models import Tag

        model_info = introspect_model(Tag)
        tortoise_model = generate_tortoise_model(model_info)
        assert tortoise_model is not None
        assert tortoise_model.__name__ == "TagTortoise"

    def test_model_for_article(self):
        from tests.testapp.models import Article

        model_info = introspect_model(Article)
        tortoise_model = generate_tortoise_model(model_info)
        assert tortoise_model is not None
        assert tortoise_model.__name__ == "ArticleTortoise"


class TestGeneratedModelMeta:
    """Generated model Meta class has correct attributes."""

    def test_table_name(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert tortoise_model.Meta.table == "testapp_category"

    def test_app_name(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert tortoise_model.Meta.app == "django_tortoise"

    def test_custom_app_name(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info, tortoise_app_name="custom_app")
        assert tortoise_model.Meta.app == "custom_app"

    def test_tag_table_name(self):
        from tests.testapp.models import Tag

        model_info = introspect_model(Tag)
        tortoise_model = generate_tortoise_model(model_info)
        # Django default table name: "testapp_tag"
        assert tortoise_model.Meta.table == "testapp_tag"


class TestGeneratedModelFields:
    """Generated model has the expected data fields."""

    def test_category_has_name_field(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert "name" in tortoise_model._meta.fields_map

    def test_category_has_slug_field(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert "slug" in tortoise_model._meta.fields_map

    def test_category_has_id_field(self):
        from tests.testapp.models import Category

        model_info = introspect_model(Category)
        tortoise_model = generate_tortoise_model(model_info)
        assert "id" in tortoise_model._meta.fields_map

    def test_tag_has_name_field(self):
        from tests.testapp.models import Tag

        model_info = introspect_model(Tag)
        tortoise_model = generate_tortoise_model(model_info)
        assert "name" in tortoise_model._meta.fields_map

    def test_article_data_fields_present(self):
        """Article has many data fields that should be present."""
        from tests.testapp.models import Article

        model_info = introspect_model(Article)
        tortoise_model = generate_tortoise_model(model_info)
        fields_map = tortoise_model._meta.fields_map
        for field_name in ["id", "title", "body", "views", "published", "uuid", "metadata"]:
            assert field_name in fields_map, f"Expected field '{field_name}' in generated model"

    def test_relational_fields_excluded(self):
        """Relational fields should not be in the generated model (Phase 4)."""
        from tests.testapp.models import Article

        model_info = introspect_model(Article)
        tortoise_model = generate_tortoise_model(model_info)
        fields_map = tortoise_model._meta.fields_map
        # category (FK) and tags (M2M) should be excluded
        assert "category" not in fields_map
        assert "tags" not in fields_map


class TestNoConvertibleFields:
    """Models with no convertible fields return None."""

    def test_empty_model_returns_none(self):
        info = ModelInfo(
            model_class=object,
            app_label="test",
            model_name="Empty",
            db_table="empty",
            fields=[],
            unique_together=[],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        result = generate_tortoise_model(info)
        assert result is None


class TestUniqueTogetherPropagation:
    """unique_together constraints are propagated to the Tortoise model Meta."""

    def test_unique_together_on_article(self):
        """Article has unique_together on ('title', 'category').

        Since 'category' is a relational field and will be skipped in Phase 2,
        the unique_together constraint will reference a missing field.
        The generator should handle this gracefully (omit or warn).
        """
        from tests.testapp.models import Article

        model_info = introspect_model(Article)
        tortoise_model = generate_tortoise_model(model_info)
        # 'category' is relational, so it won't be in converted fields.
        # The constraint should be omitted since it references 'category'.
        meta = tortoise_model.Meta
        # If unique_together was set, it should not include the invalid one
        unique_together = getattr(meta, "unique_together", None)
        if unique_together is not None:
            for constraint in unique_together:
                assert "category" not in constraint

    def test_unique_together_with_all_data_fields(self):
        """When unique_together only references data fields, it's preserved."""
        from django_tortoise.introspection import FieldInfo

        # Create a ModelInfo with unique_together on two data fields
        field_a = FieldInfo(
            name="a",
            internal_type="CharField",
            column="a",
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
        field_b = FieldInfo(
            name="b",
            internal_type="IntegerField",
            column="b",
            primary_key=False,
            null=False,
            unique=False,
            has_default=False,
            default=None,
            max_length=None,
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
        info = ModelInfo(
            model_class=type("FakeModel", (), {}),
            app_label="test",
            model_name="fake",
            db_table="test_fake",
            fields=[field_a, field_b],
            unique_together=[("a", "b")],
            is_abstract=False,
            is_proxy=False,
            is_managed=True,
            pk_name="id",
        )
        tortoise_model = generate_tortoise_model(info)
        assert tortoise_model is not None
        assert hasattr(tortoise_model.Meta, "unique_together")
        assert ("a", "b") in tortoise_model.Meta.unique_together
