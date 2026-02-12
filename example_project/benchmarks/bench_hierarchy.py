"""
Benchmarks for hierarchy models (Department -> Team -> Employee).

Focuses on operations that involve related objects:
  - Fetch employee with team + department (join/prefetch)
  - List employees with related data
  - Filter across relations
  - All standard operations on Employee
"""

from asgiref.sync import sync_to_async

from benchmarks.runner import BenchmarkResult, run_benchmark

MODEL_TIER = "hierarchy"


async def run_all(iterations: int = 50) -> list[BenchmarkResult]:
    """Run all hierarchy-model benchmarks."""
    from demo.models import Department, Employee, Team

    results = []

    if not await Employee.objects.aexists():
        raise RuntimeError("No Employee data. Run 'python manage.py seed_data' first.")

    first_emp = await Employee.objects.afirst()
    emp_id = first_emp.pk

    first_team = await Team.objects.afirst()
    team_id = first_team.pk

    first_dept = await Department.objects.afirst()
    dept_id = first_dept.pk

    # --- GET single employee ---
    results.append(await run_benchmark(
        "Employee.get(id=N)", "tortoise_objects", "get", MODEL_TIER,
        lambda: Employee.tortoise_objects.get(id=emp_id),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "Employee.get(id=N)", "django_native", "get", MODEL_TIER,
        lambda: Employee.objects.aget(id=emp_id),
        iterations=iterations,
    ))

    # --- FILTER all employees ---
    results.append(await run_benchmark(
        "Employee.all()", "tortoise_objects", "filter", MODEL_TIER,
        lambda: Employee.tortoise_objects.all(),
        iterations=iterations,
    ))

    async def _django_all():
        return [obj async for obj in Employee.objects.all()]

    results.append(await run_benchmark(
        "Employee.all()", "django_native", "filter", MODEL_TIER,
        _django_all,
        iterations=iterations,
    ))

    # --- COUNT ---
    results.append(await run_benchmark(
        "Employee.count()", "tortoise_objects", "count", MODEL_TIER,
        lambda: Employee.tortoise_objects.all().count(),
        iterations=iterations,
    ))
    results.append(await run_benchmark(
        "Employee.count()", "django_native", "count", MODEL_TIER,
        lambda: Employee.objects.acount(),
        iterations=iterations,
    ))

    # --- FILTER by FK (employees in a team) ---
    results.append(await run_benchmark(
        "Employee.filter(team_id=N)", "tortoise_objects", "filter_fk", MODEL_TIER,
        lambda: Employee.tortoise_objects.filter(team_id=team_id),
        iterations=iterations,
    ))

    async def _django_filter_fk():
        return [obj async for obj in Employee.objects.filter(team_id=team_id)]

    results.append(await run_benchmark(
        "Employee.filter(team_id=N)", "django_native", "filter_fk", MODEL_TIER,
        _django_filter_fk,
        iterations=iterations,
    ))

    # --- PREFETCH / SELECT RELATED ---
    # Tortoise: use prefetch_related on the Tortoise model directly
    # Django: use sync_to_async(list)(...select_related(...))

    async def _tortoise_select_related():
        """Fetch employees with team via Tortoise's prefetch_related."""
        emp_model = Employee.tortoise_objects.model
        from django_tortoise.initialization import ensure_initialized
        await ensure_initialized()
        return await emp_model.filter(team_id=team_id).prefetch_related("team")

    results.append(await run_benchmark(
        "Employee+Team prefetch", "tortoise_objects", "prefetch_related", MODEL_TIER,
        _tortoise_select_related,
        iterations=iterations,
    ))

    async def _django_select_related():
        """Fetch employees with team via Django select_related."""
        return await sync_to_async(list)(
            Employee.objects.filter(team_id=team_id).select_related("team")
        )

    results.append(await run_benchmark(
        "Employee+Team select_related", "django_native", "prefetch_related", MODEL_TIER,
        _django_select_related,
        iterations=iterations,
    ))

    # --- DEEP HIERARCHY: Employee -> Team -> Department ---
    async def _tortoise_deep_prefetch():
        """Fetch employees with team and department via Tortoise prefetch."""
        emp_model = Employee.tortoise_objects.model
        from django_tortoise.initialization import ensure_initialized
        await ensure_initialized()
        return await emp_model.all().prefetch_related("team", "team__department").limit(50)

    results.append(await run_benchmark(
        "Employee+Team+Dept deep prefetch", "tortoise_objects", "deep_prefetch", MODEL_TIER,
        _tortoise_deep_prefetch,
        iterations=iterations,
    ))

    async def _django_deep_select():
        """Fetch employees with team and department via Django select_related."""
        return await sync_to_async(list)(
            Employee.objects.select_related("team", "team__department")[:50]
        )

    results.append(await run_benchmark(
        "Employee+Team+Dept select_related", "django_native", "deep_prefetch", MODEL_TIER,
        _django_deep_select,
        iterations=iterations,
    ))

    return results
