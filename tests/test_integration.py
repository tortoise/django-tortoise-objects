"""
End-to-end integration tests (Phase 5, Step 5.3).

These tests exercise the full pipeline: Django model -> introspect ->
generate -> init Tortoise -> query against a real SQLite database.

The ``tortoise_db`` fixture initializes Tortoise to connect to the same
SQLite file that pytest-django creates and manages.
"""

import pytest

from django_tortoise.initialization import _reset_for_testing, close, init, is_initialized


@pytest.fixture
async def tortoise_db():
    """
    Fixture to init and clean up Tortoise for each test.

    Ensures Tortoise is connected to the same database that Django (via
    pytest-django) manages.
    """
    _reset_for_testing()
    await init()
    yield
    await close()
    _reset_for_testing()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_create_and_query(tortoise_db):
    """Create a record via Tortoise and query it back."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="integration-test")
    tags = await Tag.tortoise_objects.filter(name="integration-test")
    assert len(tags) == 1
    assert tags[0].name == "integration-test"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_all_query(tortoise_db):
    """all() returns all records."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="tag1")
    await Tag.tortoise_objects.create(name="tag2")
    all_tags = await Tag.tortoise_objects.all()
    names = [t.name for t in all_tags]
    assert "tag1" in names
    assert "tag2" in names


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_count(tortoise_db):
    """count() returns correct count after filter."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="count-test")
    count = await Tag.tortoise_objects.filter(name="count-test").count()
    assert count >= 1


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_first(tortoise_db):
    """first() returns the first matching record."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="first-test")
    tag = await Tag.tortoise_objects.filter(name="first-test").first()
    assert tag is not None
    assert tag.name == "first-test"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_get(tortoise_db):
    """get() returns a single record."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="get-test-unique")
    tag = await Tag.tortoise_objects.get(name="get-test-unique")
    assert tag.name == "get-test-unique"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_values(tortoise_db):
    """values() returns dict projections."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="values-test")
    result = await Tag.tortoise_objects.filter(name="values-test").values("name")
    assert len(result) >= 1
    assert result[0]["name"] == "values-test"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_exists(tortoise_db):
    """exists() returns correct boolean."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="exists-test")
    assert await Tag.tortoise_objects.filter(name="exists-test").exists()
    assert not await Tag.tortoise_objects.filter(name="nonexistent-xyz").exists()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_update(tortoise_db):
    """update() modifies records in place."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="update-before")
    await Tag.tortoise_objects.filter(name="update-before").update(name="update-after")
    tag = await Tag.tortoise_objects.get(name="update-after")
    assert tag.name == "update-after"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_delete(tortoise_db):
    """delete() removes records."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="delete-test")
    assert await Tag.tortoise_objects.filter(name="delete-test").exists()
    await Tag.tortoise_objects.filter(name="delete-test").delete()
    assert not await Tag.tortoise_objects.filter(name="delete-test").exists()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_lazy_init(tortoise_db):
    """First query triggers lazy initialization."""
    # tortoise_db already initialized for us; verify the flag
    assert is_initialized()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_lazy_init_via_query():
    """tortoise_objects query auto-initializes Tortoise."""
    _reset_for_testing()
    assert not is_initialized()
    from tests.testapp.models import Tag

    # This should trigger lazy init via _LazyQuerySet.__await__
    await Tag.tortoise_objects.all()
    assert is_initialized()
    await close()
    _reset_for_testing()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_fk_create_and_query(tortoise_db):
    """Test FK relations work end-to-end."""
    from datetime import datetime, timezone

    from tests.testapp.models import Article, Category

    cat_model = Category.tortoise_objects.model
    art_model = Article.tortoise_objects.model
    now = datetime.now(timezone.utc)
    cat = await cat_model.create(name="Tech", slug="tech-int", created_at=now)
    art = await art_model.create(
        title="Test Article",
        body="Content",
        category_id=cat.id,
        published=False,
        views=0,
        created_at=now,
        updated_at=now,
    )
    assert art.category_id == cat.id


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_decimal_field(tortoise_db):
    """Decimal fields preserve precision."""
    from datetime import datetime, timezone
    from decimal import Decimal

    from tests.testapp.models import Article, Category

    cat_model = Category.tortoise_objects.model
    art_model = Article.tortoise_objects.model
    now = datetime.now(timezone.utc)
    cat = await cat_model.create(name="Sci", slug="sci-int", created_at=now)
    art = await art_model.create(
        title="Decimal Test",
        body="Content",
        category_id=cat.id,
        published=True,
        views=100,
        rating=Decimal("4.50"),
        created_at=now,
        updated_at=now,
    )
    retrieved = await art_model.get(id=art.id)
    assert retrieved.rating == Decimal("4.50")


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_boolean_field(tortoise_db):
    """Boolean fields work correctly."""
    from datetime import datetime, timezone

    from tests.testapp.models import Article, Category

    cat_model = Category.tortoise_objects.model
    art_model = Article.tortoise_objects.model
    now = datetime.now(timezone.utc)
    cat = await cat_model.create(name="Bool Cat", slug="bool-cat-int", created_at=now)
    art = await art_model.create(
        title="Bool Test",
        body="Content",
        category_id=cat.id,
        published=True,
        views=0,
        created_at=now,
        updated_at=now,
    )
    retrieved = await art_model.get(id=art.id)
    assert retrieved.published is True


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_filter_chaining(tortoise_db):
    """Chained filter operations work."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="chain-a")
    await Tag.tortoise_objects.create(name="chain-b")
    result = await Tag.tortoise_objects.all().filter(name="chain-a")
    assert len(result) == 1
    assert result[0].name == "chain-a"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_order_by(tortoise_db):
    """order_by works through the chain."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="order-z")
    await Tag.tortoise_objects.create(name="order-a")
    result = await Tag.tortoise_objects.all().filter(name__startswith="order-").order_by("name")
    names = [t.name for t in result]
    assert names == sorted(names)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_limit_offset(tortoise_db):
    """limit and offset work through the chain."""
    from tests.testapp.models import Tag

    for i in range(5):
        await Tag.tortoise_objects.create(name=f"page-{i:02d}")
    result = (
        await Tag.tortoise_objects.all()
        .filter(name__startswith="page-")
        .order_by("name")
        .limit(2)
        .offset(1)
    )
    assert len(result) == 2
    assert result[0].name == "page-01"
    assert result[1].name == "page-02"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_values_list(tortoise_db):
    """values_list returns tuple projections."""
    from tests.testapp.models import Tag

    await Tag.tortoise_objects.create(name="vl-test")
    result = await Tag.tortoise_objects.filter(name="vl-test").values_list("name", flat=True)
    assert "vl-test" in result
