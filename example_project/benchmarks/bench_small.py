"""
Benchmarks for the small model (Tag).

Compares tortoise_objects vs Django native async for:
  - get (single record fetch)
  - filter (list fetch)
  - create + delete (paired)
  - bulk_create
  - count
  - exists
  - update
"""

import time

from asgiref.sync import sync_to_async

from benchmarks.runner import BenchmarkResult, run_benchmark

MODEL_TIER = "small"


async def run_all(iterations: int = 50) -> list[BenchmarkResult]:
    """Run all small-model benchmarks and return results."""
    from demo.models import Tag

    results = []

    # Ensure baseline data exists
    if not await Tag.objects.aexists():
        raise RuntimeError("No Tag data found. Run 'python manage.py seed_data' first.")

    # Get first tag ID for single-record benchmarks
    first_tag = await Tag.objects.afirst()
    tag_id = first_tag.pk

    # Unique prefix for this run to avoid collisions from previous crashes
    run_id = str(int(time.time() * 1000))

    # --- GET ---
    results.append(await run_benchmark(
        "Tag.get(id=N)", "tortoise_objects", "get", MODEL_TIER,
        lambda: Tag.tortoise_objects.get(id=tag_id),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "Tag.get(id=N)", "django_native", "get", MODEL_TIER,
        lambda: Tag.objects.aget(id=tag_id),
        iterations=iterations,
    ))

    # --- FILTER (all) ---
    results.append(await run_benchmark(
        "Tag.all()", "tortoise_objects", "filter", MODEL_TIER,
        lambda: Tag.tortoise_objects.all(),
        iterations=iterations,
    ))

    async def _django_all():
        return [obj async for obj in Tag.objects.all()]

    results.append(await run_benchmark(
        "Tag.all()", "django_native", "filter", MODEL_TIER,
        _django_all,
        iterations=iterations,
    ))

    # --- COUNT ---
    results.append(await run_benchmark(
        "Tag.count()", "tortoise_objects", "count", MODEL_TIER,
        lambda: Tag.tortoise_objects.all().count(),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "Tag.count()", "django_native", "count", MODEL_TIER,
        lambda: Tag.objects.acount(),
        iterations=iterations,
    ))

    # --- EXISTS ---
    results.append(await run_benchmark(
        "Tag.exists()", "tortoise_objects", "exists", MODEL_TIER,
        lambda: Tag.tortoise_objects.filter(name="tag-0001").exists(),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "Tag.exists()", "django_native", "exists", MODEL_TIER,
        lambda: Tag.objects.filter(name="tag-0001").aexists(),
        iterations=iterations,
    ))

    # --- CREATE + DELETE (paired to avoid accumulation) ---
    _create_counter = [0]

    async def _tortoise_create_delete():
        _create_counter[0] += 1
        name = f"bench-t-{run_id}-{_create_counter[0]}"
        await Tag.tortoise_objects.create(name=name)
        await Tag.tortoise_objects.filter(name=name).delete()

    results.append(await run_benchmark(
        "Tag.create+delete", "tortoise_objects", "create", MODEL_TIER,
        _tortoise_create_delete,
        iterations=iterations,
    ))

    _create_counter_d = [0]

    async def _django_create_delete():
        _create_counter_d[0] += 1
        name = f"bench-d-{run_id}-{_create_counter_d[0]}"
        await Tag.objects.acreate(name=name)
        await Tag.objects.filter(name=name).adelete()

    results.append(await run_benchmark(
        "Tag.create+delete", "django_native", "create", MODEL_TIER,
        _django_create_delete,
        iterations=iterations,
    ))

    # --- BULK CREATE ---
    _bulk_counter = [0]

    async def _tortoise_bulk_create():
        _bulk_counter[0] += 1
        prefix = f"bulk-t-{run_id}-{_bulk_counter[0]}"
        tortoise_model = Tag.tortoise_objects.model
        objs = [tortoise_model(name=f"{prefix}-{i}") for i in range(20)]
        await Tag.tortoise_objects.bulk_create(objs)
        await Tag.tortoise_objects.filter(name__startswith=prefix).delete()

    results.append(await run_benchmark(
        "Tag.bulk_create(20)", "tortoise_objects", "bulk_create", MODEL_TIER,
        _tortoise_bulk_create,
        iterations=iterations,
    ))

    _bulk_counter_d = [0]

    async def _django_bulk_create():
        _bulk_counter_d[0] += 1
        prefix = f"bulk-d-{run_id}-{_bulk_counter_d[0]}"
        objs = [Tag(name=f"{prefix}-{i}") for i in range(20)]
        await sync_to_async(Tag.objects.bulk_create)(objs)
        await Tag.objects.filter(name__startswith=prefix).adelete()

    results.append(await run_benchmark(
        "Tag.bulk_create(20)", "django_native", "bulk_create", MODEL_TIER,
        _django_bulk_create,
        iterations=iterations,
    ))

    # --- UPDATE ---
    results.append(await run_benchmark(
        "Tag.filter().update()", "tortoise_objects", "update", MODEL_TIER,
        lambda: Tag.tortoise_objects.filter(id=tag_id).update(name="tag-updated"),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "Tag.filter().update()", "django_native", "update", MODEL_TIER,
        lambda: Tag.objects.filter(id=tag_id).aupdate(name="tag-updated"),
        iterations=iterations,
    ))

    return results
