"""
Tests for the django_tortoise.introspection module.

Validates that ``introspect_model()`` and ``introspect_field()`` correctly
extract schema metadata from Django models.
"""

from django_tortoise.introspection import (
    ModelInfo,
    introspect_model,
    should_skip_model,
)


class TestIntrospectBasicModel:
    """introspect_model returns correct ModelInfo for simple models."""

    def test_category_db_table(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        assert info.db_table == "testapp_category"

    def test_category_app_label(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        assert info.app_label == "testapp"

    def test_category_not_abstract(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        assert not info.is_abstract

    def test_category_not_proxy(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        assert not info.is_proxy

    def test_category_is_managed(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        assert info.is_managed

    def test_category_has_expected_fields(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        field_names = [f.name for f in info.fields]
        assert "name" in field_names
        assert "slug" in field_names
        assert "description" in field_names
        assert "created_at" in field_names

    def test_category_pk_name(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        assert info.pk_name == "id"


class TestIntrospectFieldTypes:
    """Fields report correct internal_type strings."""

    def test_char_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["title"].internal_type == "CharField"

    def test_text_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["body"].internal_type == "TextField"

    def test_positive_integer_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["views"].internal_type == "PositiveIntegerField"

    def test_decimal_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["rating"].internal_type == "DecimalField"

    def test_boolean_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["published"].internal_type == "BooleanField"

    def test_uuid_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["uuid"].internal_type == "UUIDField"

    def test_json_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["metadata"].internal_type == "JSONField"

    def test_datetime_field_type(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["created_at"].internal_type == "DateTimeField"

    def test_email_field_type(self):
        """EmailField.get_internal_type() returns 'CharField' in Django."""
        from tests.testapp.models import Comment

        info = introspect_model(Comment)
        fields_by_name = {f.name: f for f in info.fields}
        # Django's EmailField returns "CharField" from get_internal_type()
        assert fields_by_name["email"].internal_type == "CharField"

    def test_generic_ip_address_field_type(self):
        from tests.testapp.models import Comment

        info = introspect_model(Comment)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["ip_address"].internal_type == "GenericIPAddressField"

    def test_slug_field_type(self):
        """SlugField.get_internal_type() returns 'SlugField' in Django."""
        from tests.testapp.models import Category

        info = introspect_model(Category)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["slug"].internal_type == "SlugField"

    def test_url_field_type(self):
        """URLField.get_internal_type() returns 'CharField' in Django."""
        from tests.testapp.models import Profile

        info = introspect_model(Profile)
        fields_by_name = {f.name: f for f in info.fields}
        # Django's URLField returns "CharField" from get_internal_type()
        assert fields_by_name["website"].internal_type == "CharField"

    def test_image_field_type(self):
        """ImageField.get_internal_type() returns 'FileField' in Django."""
        from tests.testapp.models import Profile

        info = introspect_model(Profile)
        fields_by_name = {f.name: f for f in info.fields}
        # Django's ImageField returns "FileField" from get_internal_type()
        assert fields_by_name["avatar"].internal_type == "FileField"


class TestIntrospectForeignKey:
    """FK fields have correct relation metadata."""

    def test_fk_is_relation(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["category"].is_relation

    def test_fk_related_model(self):
        from tests.testapp.models import Article, Category

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["category"].related_model is Category

    def test_fk_on_delete(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["category"].on_delete == "CASCADE"

    def test_fk_related_name(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["category"].related_name == "articles"


class TestIntrospectSelfReferentialFK:
    """Self-referential FK is detected."""

    def test_self_referential_detected(self):
        from tests.testapp.models import Comment

        info = introspect_model(Comment)
        fields_by_name = {f.name: f for f in info.fields}
        parent = fields_by_name["parent"]
        assert parent.is_relation
        assert parent.is_self_referential

    def test_non_self_referential_fk(self):
        from tests.testapp.models import Comment

        info = introspect_model(Comment)
        fields_by_name = {f.name: f for f in info.fields}
        article = fields_by_name["article"]
        assert article.is_relation
        assert not article.is_self_referential


class TestIntrospectM2M:
    """M2M fields are detected with through table info."""

    def test_m2m_detected(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        tags = fields_by_name["tags"]
        assert tags.many_to_many
        assert tags.is_relation

    def test_m2m_has_through_model(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        tags = fields_by_name["tags"]
        assert tags.through_model is not None
        assert tags.through_db_table is not None


class TestIntrospectUniqueTogether:
    """unique_together is extracted from model Meta."""

    def test_unique_together_extracted(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        assert ("title", "category") in info.unique_together


class TestIntrospectDbColumn:
    """Fields report correct DB column names."""

    def test_fk_column_has_id_suffix(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["category"].column == "category_id"

    def test_regular_field_column_matches_name(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["title"].column == "title"


class TestIntrospectFieldAttributes:
    """Various field attributes are correctly extracted."""

    def test_max_length(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["title"].max_length == 200

    def test_null(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["rating"].null is True
        assert fields_by_name["title"].null is False

    def test_unique(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["uuid"].unique is True

    def test_has_default(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["views"].has_default is True
        assert fields_by_name["views"].default == 0

    def test_decimal_params(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["rating"].max_digits == 3
        assert fields_by_name["rating"].decimal_places == 2

    def test_auto_field_detected(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["id"].is_auto_field is True
        assert fields_by_name["id"].primary_key is True

    def test_non_auto_field_not_auto(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["title"].is_auto_field is False


class TestShouldSkipModel:
    """should_skip_model correctly identifies models to skip."""

    def test_skip_abstract_model(self):
        info = ModelInfo(
            model_class=object,
            app_label="test",
            model_name="Abstract",
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
            app_label="test",
            model_name="Proxy",
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
        skip, reason = should_skip_model(info)
        assert skip
        assert "no concrete fields" in reason.lower()

    def test_do_not_skip_normal_model(self):
        from tests.testapp.models import Category

        info = introspect_model(Category)
        skip, reason = should_skip_model(info)
        assert not skip
        assert reason == ""


class TestReverseRelationsFiltered:
    """Reverse relations are filtered out by introspect_field."""

    def test_no_reverse_fk_in_fields(self):
        """Category should not include the reverse 'articles' FK relation."""
        from tests.testapp.models import Category

        info = introspect_model(Category)
        field_names = [f.name for f in info.fields]
        # 'articles' is a reverse relation, should not appear
        assert "articles" not in field_names

    def test_no_reverse_m2m_in_tag(self):
        """Tag should not include the reverse 'articles' M2M relation."""
        from tests.testapp.models import Tag

        info = introspect_model(Tag)
        field_names = [f.name for f in info.fields]
        assert "articles" not in field_names


class TestIntrospectEnumType:
    """enum_type detection for fields with enum-backed choices."""

    def test_integer_choices_enum_detected(self):
        from tests.testapp.models import EnumTestModel, Status

        info = introspect_model(EnumTestModel)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["status"].enum_type is Status

    def test_text_choices_enum_detected(self):
        from tests.testapp.models import Color, EnumTestModel

        info = introspect_model(EnumTestModel)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["color"].enum_type is Color

    def test_plain_tuple_choices_no_enum(self):
        from tests.testapp.models import EnumTestModel

        info = introspect_model(EnumTestModel)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["priority"].enum_type is None

    def test_no_choices_no_enum(self):
        from tests.testapp.models import EnumTestModel

        info = introspect_model(EnumTestModel)
        fields_by_name = {f.name: f for f in info.fields}
        assert fields_by_name["no_choices"].enum_type is None
