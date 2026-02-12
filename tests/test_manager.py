"""
Tests for django_tortoise.manager -- TortoiseObjects descriptor and _LazyQuerySet.

Verifies the descriptor protocol, queryset proxy methods, and chaining.
"""

from django_tortoise.manager import TortoiseObjects, _LazyQuerySet


class TestTortoiseObjectsDescriptor:
    """Tests for TortoiseObjects as a descriptor."""

    def test_is_descriptor(self):
        """TortoiseObjects works as a descriptor on a class."""

        class FakeTortoiseModel:
            @classmethod
            def all(cls):
                return "queryset"

        class FakeModel:
            pass

        FakeModel.tortoise_objects = TortoiseObjects(FakeTortoiseModel)
        manager = FakeModel.tortoise_objects
        assert isinstance(manager, TortoiseObjects)
        assert manager.model is FakeTortoiseModel

    def test_instance_access_returns_manager(self):
        """Accessing via instance returns the same manager."""

        class FakeTortoiseModel:
            pass

        class FakeModel:
            pass

        FakeModel.tortoise_objects = TortoiseObjects(FakeTortoiseModel)
        instance = FakeModel()
        assert isinstance(instance.tortoise_objects, TortoiseObjects)

    def test_model_property(self):
        """model property returns the tortoise model class."""

        class FakeTortoiseModel:
            pass

        manager = TortoiseObjects(FakeTortoiseModel)
        assert manager.model is FakeTortoiseModel


class TestTortoiseObjectsMethods:
    """Tests that TortoiseObjects methods return _LazyQuerySet."""

    def setup_method(self):
        class FakeTortoiseModel:
            pass

        self.manager = TortoiseObjects(FakeTortoiseModel)

    def test_all_returns_lazy_queryset(self):
        result = self.manager.all()
        assert isinstance(result, _LazyQuerySet)

    def test_filter_returns_lazy_queryset(self):
        result = self.manager.filter(name="test")
        assert isinstance(result, _LazyQuerySet)

    def test_exclude_returns_lazy_queryset(self):
        result = self.manager.exclude(name="test")
        assert isinstance(result, _LazyQuerySet)

    def test_get_returns_lazy_queryset(self):
        result = self.manager.get(id=1)
        assert isinstance(result, _LazyQuerySet)

    def test_create_returns_lazy_queryset(self):
        result = self.manager.create(name="test")
        assert isinstance(result, _LazyQuerySet)

    def test_first_returns_lazy_queryset(self):
        result = self.manager.first()
        assert isinstance(result, _LazyQuerySet)

    def test_count_returns_lazy_queryset(self):
        result = self.manager.count()
        assert isinstance(result, _LazyQuerySet)

    def test_exists_returns_lazy_queryset(self):
        result = self.manager.exists()
        assert isinstance(result, _LazyQuerySet)

    def test_values_returns_lazy_queryset(self):
        result = self.manager.values("name")
        assert isinstance(result, _LazyQuerySet)

    def test_values_list_returns_lazy_queryset(self):
        result = self.manager.values_list("name")
        assert isinstance(result, _LazyQuerySet)

    def test_delete_returns_lazy_queryset(self):
        result = self.manager.delete()
        assert isinstance(result, _LazyQuerySet)

    def test_update_returns_lazy_queryset(self):
        result = self.manager.update(name="new")
        assert isinstance(result, _LazyQuerySet)


class TestLazyQuerySetChaining:
    """Tests that _LazyQuerySet supports method chaining."""

    def setup_method(self):
        class FakeTortoiseModel:
            pass

        self.manager = TortoiseObjects(FakeTortoiseModel)

    def test_filter_chain(self):
        result = self.manager.all().filter(name="test")
        assert isinstance(result, _LazyQuerySet)
        assert len(result._chain) == 1

    def test_multi_chain(self):
        result = self.manager.all().filter(name="test").order_by("-id").limit(10)
        assert isinstance(result, _LazyQuerySet)
        assert len(result._chain) == 3

    def test_chain_methods(self):
        result = (
            self.manager.all()
            .filter(active=True)
            .exclude(name="bad")
            .order_by("name")
            .limit(5)
            .offset(10)
            .values("name", "id")
        )
        assert isinstance(result, _LazyQuerySet)
        assert len(result._chain) == 6

    def test_count_after_filter(self):
        result = self.manager.filter(active=True).count()
        assert isinstance(result, _LazyQuerySet)
        assert len(result._chain) == 1

    def test_exists_after_filter(self):
        result = self.manager.filter(active=True).exists()
        assert isinstance(result, _LazyQuerySet)
        assert len(result._chain) == 1

    def test_first_after_filter(self):
        result = self.manager.filter(active=True).first()
        assert isinstance(result, _LazyQuerySet)
        assert len(result._chain) == 1


class TestLazyQuerySetHasAwait:
    """Tests that _LazyQuerySet has __await__ and __aiter__."""

    def test_has_await(self):
        class FakeTortoiseModel:
            pass

        lqs = _LazyQuerySet(FakeTortoiseModel, "all")
        assert hasattr(lqs, "__await__")

    def test_has_aiter(self):
        class FakeTortoiseModel:
            pass

        lqs = _LazyQuerySet(FakeTortoiseModel, "all")
        assert hasattr(lqs, "__aiter__")
