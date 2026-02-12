"""
Async demo views showcasing django-tortoise-objects usage.

Run with: uv run uvicorn example_project.asgi:application --reload
Then visit:
  - /tags/             -- list all tags
  - /tags/create/      -- create a new tag
  - /wide/             -- list wide models (limited)
  - /employees/        -- list employees with team info
  - /benchmark/quick/  -- run a quick inline benchmark
"""

import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from demo.models import Employee, Tag, WideModel


async def tag_list(request):
    """List all tags using tortoise_objects."""
    tags = await Tag.tortoise_objects.all()
    data = [{"id": t.id, "name": t.name} for t in tags]
    return JsonResponse({"count": len(data), "tags": data})


@csrf_exempt
async def tag_create(request):
    """
    Create a tag using tortoise_objects.

    Accepts GET for easy browser testing (demo only — not a production pattern).
    """
    name = request.GET.get("name", f"auto-tag-{int(time.time())}")
    tag = await Tag.tortoise_objects.create(name=name)
    return JsonResponse({"id": tag.id, "name": tag.name}, status=201)


async def wide_model_list(request):
    """List WideModel records (first 10) using tortoise_objects."""
    records = await WideModel.tortoise_objects.all().limit(10)
    data = []
    for r in records:
        data.append({
            "id": r.id,
            "char_field": r.char_field,
            "int_field": r.int_field,
            "bool_field": r.bool_field,
            "uuid_field": str(r.uuid_field),
        })
    return JsonResponse({"count": len(data), "records": data})


async def employee_list(request):
    """
    List employees using tortoise_objects with team prefetch.

    Demonstrates accessing the underlying Tortoise model for prefetch_related.
    """
    emp_model = Employee.tortoise_objects.model
    employees = await emp_model.all().prefetch_related("team").limit(20)
    data = []
    for emp in employees:
        data.append({
            "id": emp.id,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "team": emp.team.name if emp.team else None,
        })
    return JsonResponse({"count": len(data), "employees": data})


async def quick_benchmark(request):
    """
    Run a minimal inline benchmark and return timing results.

    Compares a single Tag.get() via tortoise_objects vs Django native.
    """
    tag = await Tag.tortoise_objects.first()
    if tag is None:
        return JsonResponse({"error": "No tags found. Run seed_data first."}, status=400)

    tag_id = tag.id
    iterations = 20

    # Tortoise
    start = time.perf_counter()
    for _ in range(iterations):
        await Tag.tortoise_objects.get(id=tag_id)
    tortoise_ms = (time.perf_counter() - start) * 1000

    # Django native
    start = time.perf_counter()
    for _ in range(iterations):
        await Tag.objects.aget(id=tag_id)
    django_ms = (time.perf_counter() - start) * 1000

    return JsonResponse({
        "iterations": iterations,
        "tortoise_objects_total_ms": round(tortoise_ms, 2),
        "tortoise_objects_avg_ms": round(tortoise_ms / iterations, 2),
        "django_native_total_ms": round(django_ms, 2),
        "django_native_avg_ms": round(django_ms / iterations, 2),
    })
