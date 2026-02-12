"""
TortoiseObjects descriptor for the ``tortoise_objects`` attribute.

Provides a Django-model-attached descriptor that lazily initializes
Tortoise ORM and returns an async-capable queryset interface.
"""

import logging

logger = logging.getLogger("django_tortoise")


class TortoiseObjects:
    """
    Descriptor/proxy that provides access to Tortoise QuerySet for a Django model.

    Usage: ``MyDjangoModel.tortoise_objects.filter(name="foo")``

    All async QuerySet operations automatically trigger lazy initialization
    of Tortoise ORM connections on first use.
    """

    def __init__(self, tortoise_model_class):
        self._tortoise_model = tortoise_model_class

    def __get__(self, obj, objtype=None):
        """
        When accessed as class attribute, return self (the manager).
        When accessed as instance attribute, also return self.
        """
        return self

    @property
    def model(self):
        """The underlying Tortoise model class."""
        return self._tortoise_model

    def _get_queryset(self):
        """Get a fresh Tortoise QuerySet for the model."""
        return self._tortoise_model.all()

    # --- QuerySet proxy methods ---
    # Each method returns a _LazyQuerySet that ensures init before execution.

    def all(self):
        return _LazyQuerySet(self._tortoise_model, "all")

    def filter(self, *args, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "filter", *args, **kwargs)

    def exclude(self, *args, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "exclude", *args, **kwargs)

    def get(self, *args, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "get", *args, **kwargs)

    def create(self, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "create", **kwargs)

    def first(self):
        return _LazyQuerySet(self._tortoise_model, "first")

    def count(self):
        return _LazyQuerySet(self._tortoise_model, "count")

    def exists(self):
        return _LazyQuerySet(self._tortoise_model, "exists")

    def values(self, *args, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "values", *args, **kwargs)

    def values_list(self, *args, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "values_list", *args, **kwargs)

    def delete(self):
        return _LazyQuerySet(self._tortoise_model, "delete")

    def update(self, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "update", **kwargs)

    def get_or_create(self, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "get_or_create", **kwargs)

    def bulk_create(self, objects, **kwargs):
        return _LazyQuerySet(self._tortoise_model, "bulk_create", objects, **kwargs)


class _LazyQuerySet:
    """
    A lazy wrapper around a Tortoise QuerySet method call.

    Ensures Tortoise is initialized before executing the query.
    Supports both ``__await__`` (for direct ``await``) and chaining.
    """

    def __init__(self, tortoise_model, method_name, *args, **kwargs):
        self._tortoise_model = tortoise_model
        self._method_name = method_name
        self._args = args
        self._kwargs = kwargs
        self._chain = []  # List of (method_name, args, kwargs) for chaining

    def filter(self, *args, **kwargs):
        self._chain.append(("filter", args, kwargs))
        return self

    def exclude(self, *args, **kwargs):
        self._chain.append(("exclude", args, kwargs))
        return self

    def order_by(self, *args):
        self._chain.append(("order_by", args, {}))
        return self

    def limit(self, limit):
        self._chain.append(("limit", (limit,), {}))
        return self

    def offset(self, offset):
        self._chain.append(("offset", (offset,), {}))
        return self

    def values(self, *args, **kwargs):
        self._chain.append(("values", args, kwargs))
        return self

    def values_list(self, *args, **kwargs):
        self._chain.append(("values_list", args, kwargs))
        return self

    def count(self):
        self._chain.append(("count", (), {}))
        return self

    def first(self):
        self._chain.append(("first", (), {}))
        return self

    def exists(self):
        self._chain.append(("exists", (), {}))
        return self

    def delete(self):
        self._chain.append(("delete", (), {}))
        return self

    def update(self, **kwargs):
        self._chain.append(("update", (), kwargs))
        return self

    async def _execute(self):
        """Execute the query chain with lazy initialization."""
        from django_tortoise.initialization import ensure_initialized

        await ensure_initialized()

        # Start with the initial method call
        qs = getattr(self._tortoise_model, self._method_name)(*self._args, **self._kwargs)

        # Apply chain
        for method_name, args, kwargs in self._chain:
            qs = getattr(qs, method_name)(*args, **kwargs)

        # If the result is awaitable (queryset), await it
        if hasattr(qs, "__await__"):
            return await qs
        return qs

    def __await__(self):
        return self._execute().__await__()

    def __aiter__(self):
        return self._async_iter()

    async def _async_iter(self):
        result = await self._execute()
        if hasattr(result, "__aiter__"):
            async for item in result:
                yield item
        elif hasattr(result, "__iter__"):
            for item in result:
                yield item
        else:
            yield result
