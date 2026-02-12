"""
Tests for relational field mapping (Phase 4, Step 4.2).

Verifies FK, O2O, M2M introspection and on_delete mapping.
"""

from django_tortoise.fields import _map_on_delete
from django_tortoise.introspection import introspect_model


class TestForeignKeyIntrospection:
    """Tests for ForeignKey field introspection."""

    def test_fk_field_detected(self):
        from tests.testapp.models import Article, Category

        info = introspect_model(Article)
        fk_fields = [f for f in info.fields if f.is_relation and f.internal_type == "ForeignKey"]
        assert len(fk_fields) >= 1
        cat_fk = next(f for f in fk_fields if f.name == "category")
        assert cat_fk.related_model is Category

    def test_fk_on_delete(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        cat_fk = next(f for f in info.fields if f.name == "category")
        assert cat_fk.on_delete == "CASCADE"

    def test_fk_related_name(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        cat_fk = next(f for f in info.fields if f.name == "category")
        assert cat_fk.related_name == "articles"


class TestSelfReferentialFK:
    """Tests for self-referential FK detection."""

    def test_self_referential_detected(self):
        from tests.testapp.models import Comment

        info = introspect_model(Comment)
        parent = next(f for f in info.fields if f.name == "parent")
        assert parent.is_self_referential
        assert parent.null

    def test_non_self_referential(self):
        from tests.testapp.models import Comment

        info = introspect_model(Comment)
        article_fk = next(f for f in info.fields if f.name == "article")
        assert not article_fk.is_self_referential


class TestOneToOneIntrospection:
    """Tests for O2O field introspection."""

    def test_o2o_detected(self):
        from tests.testapp.models import Profile

        info = introspect_model(Profile)
        user_field = next(f for f in info.fields if f.name == "user")
        assert user_field.internal_type == "OneToOneField"
        assert user_field.is_relation


class TestManyToManyIntrospection:
    """Tests for M2M field introspection."""

    def test_m2m_detected(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        tags = next(f for f in info.fields if f.name == "tags")
        assert tags.many_to_many
        assert tags.through_db_table is not None

    def test_m2m_related_name(self):
        from tests.testapp.models import Article

        info = introspect_model(Article)
        tags = next(f for f in info.fields if f.name == "tags")
        assert tags.related_name == "articles"


class TestOnDeleteMapping:
    """Tests for the Django -> Tortoise on_delete mapping."""

    def test_cascade(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete("CASCADE")
        assert result is OnDelete.CASCADE

    def test_set_null(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete("SET_NULL")
        assert result is OnDelete.SET_NULL

    def test_protect_to_restrict(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete("PROTECT")
        assert result is OnDelete.RESTRICT

    def test_restrict(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete("RESTRICT")
        assert result is OnDelete.RESTRICT

    def test_do_nothing_to_no_action(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete("DO_NOTHING")
        assert result is OnDelete.NO_ACTION

    def test_set_default(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete("SET_DEFAULT")
        assert result is OnDelete.SET_DEFAULT

    def test_none_defaults_to_cascade(self):
        from tortoise.fields.relational import OnDelete

        result = _map_on_delete(None)
        assert result is OnDelete.CASCADE


class TestRelationalFieldsRegistered:
    """Tests that relational fields are added to Tortoise models."""

    def test_article_has_category_fk(self):
        """Article's Tortoise model should have a category FK attribute."""
        from tests.testapp.models import Article

        tortoise_model = Article.tortoise_objects.model
        assert hasattr(tortoise_model, "category")

    def test_comment_has_parent_fk(self):
        """Comment's Tortoise model should have a parent FK (self-referential)."""
        from tests.testapp.models import Comment

        tortoise_model = Comment.tortoise_objects.model
        assert hasattr(tortoise_model, "parent")

    def test_comment_has_article_fk(self):
        """Comment's Tortoise model should have an article FK."""
        from tests.testapp.models import Comment

        tortoise_model = Comment.tortoise_objects.model
        assert hasattr(tortoise_model, "article")

    def test_article_has_tags_m2m(self):
        """Article's Tortoise model should have tags M2M."""
        from tests.testapp.models import Article

        tortoise_model = Article.tortoise_objects.model
        assert hasattr(tortoise_model, "tags")

    def test_profile_has_user_o2o(self):
        """Profile's Tortoise model should have a user O2O."""
        from tests.testapp.models import Profile

        tortoise_model = Profile.tortoise_objects.model
        assert hasattr(tortoise_model, "user")
