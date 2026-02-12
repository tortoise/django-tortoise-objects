"""
Tests for the django_tortoise.registry module.

Validates that ``ModelRegistry`` correctly stores and retrieves bidirectional
mappings between Django and Tortoise models, and that the module-level
convenience functions work correctly.
"""

from django_tortoise.registry import (
    ModelRegistry,
    clear_registry,
    get_all_mappings,
    get_tortoise_model,
    model_registry,
    register_model,
)


class TestModelRegistry:
    """ModelRegistry class stores and retrieves model mappings."""

    def test_register_and_retrieve_tortoise(self):
        reg = ModelRegistry()

        class FakeDjango:
            pass

        class FakeTortoise:
            pass

        reg.register(FakeDjango, FakeTortoise, "app.FakeDjango")
        assert reg.get_tortoise_model(FakeDjango) is FakeTortoise

    def test_register_and_retrieve_django(self):
        reg = ModelRegistry()

        class FakeDjango:
            pass

        class FakeTortoise:
            pass

        reg.register(FakeDjango, FakeTortoise, "app.FakeDjango")
        assert reg.get_django_model(FakeTortoise) is FakeDjango

    def test_get_by_label(self):
        reg = ModelRegistry()

        class FakeDjango:
            pass

        class FakeTortoise:
            pass

        reg.register(FakeDjango, FakeTortoise, "app.FakeDjango")
        assert reg.get_by_label("app.FakeDjango") is FakeTortoise

    def test_is_registered_true(self):
        reg = ModelRegistry()

        class FakeDjango:
            pass

        class FakeTortoise:
            pass

        reg.register(FakeDjango, FakeTortoise, "app.FakeDjango")
        assert reg.is_registered(FakeDjango)

    def test_is_registered_false(self):
        reg = ModelRegistry()

        class Unknown:
            pass

        assert not reg.is_registered(Unknown)

    def test_unregistered_tortoise_returns_none(self):
        reg = ModelRegistry()

        class Unknown:
            pass

        assert reg.get_tortoise_model(Unknown) is None

    def test_unregistered_django_returns_none(self):
        reg = ModelRegistry()

        class Unknown:
            pass

        assert reg.get_django_model(Unknown) is None

    def test_unregistered_label_returns_none(self):
        reg = ModelRegistry()
        assert reg.get_by_label("nonexistent.Model") is None

    def test_get_all_tortoise_models(self):
        reg = ModelRegistry()

        class D1:
            pass

        class T1:
            pass

        class D2:
            pass

        class T2:
            pass

        reg.register(D1, T1, "app.D1")
        reg.register(D2, T2, "app.D2")
        all_models = reg.get_all_tortoise_models()
        assert T1 in all_models
        assert T2 in all_models
        assert len(all_models) == 2

    def test_get_all_tortoise_models_returns_copy(self):
        reg = ModelRegistry()

        class D:
            pass

        class T:
            pass

        reg.register(D, T, "app.D")
        models = reg.get_all_tortoise_models()
        models.clear()  # Should not affect internal state
        assert len(reg.get_all_tortoise_models()) == 1

    def test_get_all_mappings(self):
        reg = ModelRegistry()

        class D:
            pass

        class T:
            pass

        reg.register(D, T, "app.D")
        mappings = reg.get_all_mappings()
        assert D in mappings
        assert mappings[D] is T

    def test_clear(self):
        reg = ModelRegistry()

        class FakeDjango:
            pass

        class FakeTortoise:
            pass

        reg.register(FakeDjango, FakeTortoise, "app.FakeDjango")
        reg.clear()
        assert not reg.is_registered(FakeDjango)
        assert reg.get_all_tortoise_models() == []
        assert reg.get_by_label("app.FakeDjango") is None
        assert reg.get_django_model(FakeTortoise) is None


class TestModuleLevelFunctions:
    """Module-level convenience functions delegate to the global singleton."""

    def setup_method(self):
        """Clear global registry before each test."""
        clear_registry()

    def teardown_method(self):
        """Clear global registry after each test."""
        clear_registry()

    def test_register_and_get_tortoise_model(self):
        class FakeDjango:
            pass

        class FakeTortoise:
            pass

        register_model(FakeDjango, FakeTortoise, label="app.FakeDjango")
        assert get_tortoise_model(FakeDjango) is FakeTortoise

    def test_register_model_auto_label(self):
        """register_model derives label from _meta when not provided."""

        class FakeMeta:
            app_label = "myapp"

        class FakeDjango:
            _meta = FakeMeta()
            __name__ = "FakeDjango"

        class FakeTortoise:
            pass

        # Use the class, not an instance
        register_model(FakeDjango, FakeTortoise)
        assert model_registry.get_by_label("myapp.FakeDjango") is FakeTortoise

    def test_get_all_mappings_function(self):
        class D:
            pass

        class T:
            pass

        register_model(D, T, label="app.D")
        mappings = get_all_mappings()
        assert D in mappings

    def test_clear_registry_function(self):
        class D:
            pass

        class T:
            pass

        register_model(D, T, label="app.D")
        clear_registry()
        assert get_tortoise_model(D) is None

    def test_unregistered_returns_none(self):
        class Unknown:
            pass

        assert get_tortoise_model(Unknown) is None


class TestRegistryWithRealModels:
    """Integration tests using actual Django models and generated Tortoise models."""

    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    def test_register_generated_model(self):
        """Register a generated Tortoise model and retrieve it."""
        from django_tortoise.generator import generate_tortoise_model
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Tag

        model_info = introspect_model(Tag)
        tortoise_model = generate_tortoise_model(model_info)
        register_model(Tag, tortoise_model, label="testapp.Tag")

        assert get_tortoise_model(Tag) is tortoise_model
        assert model_registry.get_by_label("testapp.Tag") is tortoise_model
        assert model_registry.get_django_model(tortoise_model) is Tag
        assert model_registry.is_registered(Tag)

    def test_register_multiple_models(self):
        """Register multiple models and verify all are retrievable."""
        from django_tortoise.generator import generate_tortoise_model
        from django_tortoise.introspection import introspect_model
        from tests.testapp.models import Category, Tag

        cat_info = introspect_model(Category)
        cat_tortoise = generate_tortoise_model(cat_info)
        register_model(Category, cat_tortoise, label="testapp.Category")

        tag_info = introspect_model(Tag)
        tag_tortoise = generate_tortoise_model(tag_info)
        register_model(Tag, tag_tortoise, label="testapp.Tag")

        all_models = model_registry.get_all_tortoise_models()
        assert len(all_models) == 2
        assert cat_tortoise in all_models
        assert tag_tortoise in all_models
