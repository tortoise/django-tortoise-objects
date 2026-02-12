"""
Tests for django_tortoise.apps -- AppConfig and model inclusion/exclusion.

Verifies that ``DjangoTortoiseConfig.ready()`` correctly populates the
registry and that ``_should_include()`` handles all pattern combinations.
"""

from django_tortoise.apps import _should_include


class TestShouldInclude:
    """Tests for the _should_include filter function."""

    def test_include_all_by_default(self):
        assert _should_include("myapp.MyModel", None, None)

    def test_include_specific(self):
        assert _should_include("myapp.MyModel", ["myapp.MyModel"], None)
        assert not _should_include("myapp.Other", ["myapp.MyModel"], None)

    def test_include_glob(self):
        assert _should_include("myapp.MyModel", ["myapp.*"], None)
        assert not _should_include("otherapp.Model", ["myapp.*"], None)

    def test_exclude(self):
        assert not _should_include("django.contrib.auth.User", None, ["django.contrib.*"])
        assert _should_include("myapp.MyModel", None, ["django.contrib.*"])

    def test_exclude_takes_precedence(self):
        assert not _should_include("myapp.Secret", ["myapp.*"], ["myapp.Secret"])

    def test_multiple_include_patterns(self):
        assert _should_include("app1.Model", ["app1.*", "app2.*"], None)
        assert _should_include("app2.Model", ["app1.*", "app2.*"], None)
        assert not _should_include("app3.Model", ["app1.*", "app2.*"], None)

    def test_multiple_exclude_patterns(self):
        assert not _should_include("app1.Model", None, ["app1.*", "app2.*"])
        assert _should_include("app3.Model", None, ["app1.*", "app2.*"])


class TestReadyPopulatesRegistry:
    """Tests that AppConfig.ready() correctly populates the registry."""

    def test_ready_populates_registry(self):
        """After Django setup, the registry should have models from testapp."""
        from django_tortoise.registry import model_registry
        from tests.testapp.models import Category, Tag

        assert model_registry.is_registered(Category)
        assert model_registry.is_registered(Tag)

    def test_ready_populates_article(self):
        from django_tortoise.registry import model_registry
        from tests.testapp.models import Article

        assert model_registry.is_registered(Article)

    def test_ready_populates_comment(self):
        from django_tortoise.registry import model_registry
        from tests.testapp.models import Comment

        assert model_registry.is_registered(Comment)

    def test_ready_populates_profile(self):
        from django_tortoise.registry import model_registry
        from tests.testapp.models import Profile

        assert model_registry.is_registered(Profile)


class TestReadySetsTortoiseObjects:
    """Tests that AppConfig.ready() sets tortoise_objects on models."""

    def test_category_has_tortoise_objects(self):
        from tests.testapp.models import Category

        assert hasattr(Category, "tortoise_objects")

    def test_tag_has_tortoise_objects(self):
        from tests.testapp.models import Tag

        assert hasattr(Tag, "tortoise_objects")

    def test_article_has_tortoise_objects(self):
        from tests.testapp.models import Article

        assert hasattr(Article, "tortoise_objects")


class TestReadyPopulatesModels:
    """Tests that __models__ list is populated."""

    def test_models_list_not_empty(self):
        from django_tortoise import _models

        assert len(_models.__models__) > 0

    def test_models_list_contains_tortoise_models(self):
        from tortoise import models as tortoise_models

        from django_tortoise import _models

        for model in _models.__models__:
            assert issubclass(model, tortoise_models.Model)
