"""
Benchmarks for the wide model (WideModel -- 20+ fields).

Same operation matrix as bench_small, but measures overhead of
serializing/deserializing wide rows with many field types.
"""

import time
import uuid
from datetime import datetime, timezone

from asgiref.sync import sync_to_async

from benchmarks.runner import BenchmarkResult, run_benchmark

MODEL_TIER = "wide"


async def run_all(iterations: int = 50) -> list[BenchmarkResult]:
    """Run all wide-model benchmarks."""
    from demo.models import WideModel

    results = []

    if not await WideModel.objects.aexists():
        raise RuntimeError("No WideModel data. Run 'python manage.py seed_data' first.")

    first = await WideModel.objects.afirst()
    obj_id = first.pk

    run_id = str(int(time.time() * 1000))

    # --- GET ---
    results.append(await run_benchmark(
        "WideModel.get(id=N)", "tortoise_objects", "get", MODEL_TIER,
        lambda: WideModel.tortoise_objects.get(id=obj_id),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "WideModel.get(id=N)", "django_native", "get", MODEL_TIER,
        lambda: WideModel.objects.aget(id=obj_id),
        iterations=iterations,
    ))

    # --- FILTER (all) ---
    results.append(await run_benchmark(
        "WideModel.all()", "tortoise_objects", "filter", MODEL_TIER,
        lambda: WideModel.tortoise_objects.all(),
        iterations=iterations,
    ))

    async def _django_all():
        return [obj async for obj in WideModel.objects.all()]

    results.append(await run_benchmark(
        "WideModel.all()", "django_native", "filter", MODEL_TIER,
        _django_all,
        iterations=iterations,
    ))

    # --- COUNT ---
    results.append(await run_benchmark(
        "WideModel.count()", "tortoise_objects", "count", MODEL_TIER,
        lambda: WideModel.tortoise_objects.all().count(),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "WideModel.count()", "django_native", "count", MODEL_TIER,
        lambda: WideModel.objects.acount(),
        iterations=iterations,
    ))

    # --- EXISTS ---
    results.append(await run_benchmark(
        "WideModel.exists()", "tortoise_objects", "exists", MODEL_TIER,
        lambda: WideModel.tortoise_objects.filter(id=obj_id).exists(),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "WideModel.exists()", "django_native", "exists", MODEL_TIER,
        lambda: WideModel.objects.filter(id=obj_id).aexists(),
        iterations=iterations,
    ))

    # --- CREATE + DELETE ---
    _counter = [0]

    async def _tortoise_create_delete():
        _counter[0] += 1
        now = datetime.now(timezone.utc)
        obj = await WideModel.tortoise_objects.create(
            char_field=f"bench-t-{run_id}-{_counter[0]}",
            int_field=_counter[0],
            bool_field=True,
            decimal_field=0,
            uuid_field=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
        )
        await WideModel.tortoise_objects.filter(id=obj.id).delete()

    results.append(await run_benchmark(
        "WideModel.create+delete", "tortoise_objects", "create", MODEL_TIER,
        _tortoise_create_delete,
        iterations=iterations,
    ))

    _counter_d = [0]

    async def _django_create_delete():
        _counter_d[0] += 1
        obj = await WideModel.objects.acreate(
            char_field=f"bench-d-{run_id}-{_counter_d[0]}",
            int_field=_counter_d[0],
            bool_field=True,
            decimal_field=0,
            uuid_field=uuid.uuid4(),
        )
        await WideModel.objects.filter(id=obj.pk).adelete()

    results.append(await run_benchmark(
        "WideModel.create+delete", "django_native", "create", MODEL_TIER,
        _django_create_delete,
        iterations=iterations,
    ))

    # --- UPDATE ---
    results.append(await run_benchmark(
        "WideModel.filter().update()", "tortoise_objects", "update", MODEL_TIER,
        lambda: WideModel.tortoise_objects.filter(id=obj_id).update(int_field=999),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "WideModel.filter().update()", "django_native", "update", MODEL_TIER,
        lambda: WideModel.objects.filter(id=obj_id).aupdate(int_field=999),
        iterations=iterations,
    ))

    return results
