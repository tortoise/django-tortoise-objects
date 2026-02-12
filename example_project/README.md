# django-tortoise-objects Example Project

A standalone Django ASGI project demonstrating `django-tortoise-objects` library features with a comprehensive benchmark suite comparing Tortoise ORM vs native Django async ORM.

## Quick Start

```bash
cd example_project
uv sync
uv run python manage.py migrate
uv run python manage.py seed_data
uv run python -m benchmarks
```

### With PostgreSQL

```bash
# Start PostgreSQL
docker run -d --name bench-postgres \
  -e POSTGRES_DB=bench -e POSTGRES_USER=bench -e POSTGRES_PASSWORD=bench \
  -p 5432:5432 postgres:16-alpine

# Run with PostgreSQL
export DATABASE_URL=postgres://bench:bench@localhost:5432/bench
uv run python manage.py migrate
uv run python manage.py seed_data
uv run python -m benchmarks --db-label postgres
```

## Running the Demo Server

```bash
uv run uvicorn example_project.asgi:application --reload
```

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tags/` | GET | List all tags via `tortoise_objects.all()` |
| `/tags/create/?name=foo` | GET | Create a tag via `tortoise_objects.create()` |
| `/wide/` | GET | List first 10 WideModel records via `tortoise_objects.all().limit(10)` |
| `/employees/` | GET | List employees with team prefetch via Tortoise `prefetch_related` |
| `/benchmark/quick/` | GET | Run an inline timing comparison (Tag.get) |

## Benchmark Suite

### Running Benchmarks

```bash
# Run all tiers with default 50 iterations (SQLite)
uv run python -m benchmarks

# Run against PostgreSQL
DATABASE_URL=postgres://user:pass@localhost:5432/dbname \
  uv run python -m benchmarks --db-label postgres

# Run with custom iteration count
uv run python -m benchmarks --iterations 100

# Run a specific tier only
uv run python -m benchmarks --tier small
uv run python -m benchmarks --tier wide
uv run python -m benchmarks --tier hierarchy

# Output as JSON
uv run python -m benchmarks --json
```

### What Is Measured

The benchmark suite compares two approaches for async database access in Django:

- **tortoise_objects**: The `django-tortoise-objects` library (Tortoise ORM under the hood)
- **django_native**: Django's built-in async ORM methods (`aget`, `acreate`, `acount`, etc.)

### Benchmark Tiers

| Tier | Model | Fields | Purpose |
|------|-------|--------|---------|
| **small** | `Tag` | 1 (name) | Baseline per-operation latency |
| **wide** | `WideModel` | 23 (all supported types) | Serialization overhead for wide rows |
| **hierarchy** | `Employee` -> `Team` -> `Department` | 3-level FK chain | Relation traversal and prefetch performance |

### Operations Benchmarked

| Operation | Description |
|-----------|-------------|
| `get` | Fetch a single record by primary key |
| `filter` / `all` | Fetch all records as a list |
| `count` | Count records |
| `exists` | Check existence |
| `create+delete` | Create then immediately delete (paired) |
| `bulk_create` | Create 20 records in bulk then delete |
| `update` | Update a single record by filter |
| `prefetch_related` | Fetch with related objects (hierarchy tier only) |
| `deep_prefetch` | Fetch with 2-level deep relations (hierarchy tier only) |

### Generating Diagrams

Diagrams are generated automatically after each benchmark run. To skip diagram generation:

```bash
uv run python -m benchmarks --no-diagrams
```

Use `--db-label` to name the output files (defaults to `sqlite`):

```bash
uv run python -m benchmarks --db-label sqlite
DATABASE_URL=postgres://... uv run python -m benchmarks --db-label postgres
```

Generated PNG files are saved to `diagrams/`.

### Results — PostgreSQL

> PostgreSQL 16 via Docker. Both Django and Tortoise use `psycopg` driver.

![Benchmark results — PostgreSQL](diagrams/bench_postgres.png)

#### Speedup Summary

![Performance summary — PostgreSQL](diagrams/bench_postgres_summary.png)

### Key Observations

**PostgreSQL** (both using psycopg driver):
- `tortoise_objects` wins on single-record ops: `get` 1.3-2.0x, `count` 1.3-1.5x, `exists` 1.5x, `filter` 1.5x
- `tortoise_objects` wins on writes: `create+delete` 1.4-2.6x, `WideModel.create+delete` 1.4x
- `tortoise_objects` wins on bulk fetches: `WideModel.all()` 1.2x, `Employee.all()` ~tied
- `Tag.all()` nearly tied: 0.35ms vs 0.39ms
- Relation queries: `prefetch_related` and `select_related` nearly tied for 1-level joins; Django wins on deep joins

### Interpreting Results

- **Min/Mean/Median/P95/Max**: Wall-clock time in milliseconds per operation
- Lower is better
- `tortoise_objects` uses truly async I/O (aiosqlite/psycopg) — no thread pool overhead
- `django_native` uses `sync_to_async` wrappers for SQLite, native async `psycopg3` for PostgreSQL
- Results vary by database backend and dataset size

### Seeding Data

```bash
# Default counts: 100 tags, 100 wide, 5 depts / 4 teams / 10 employees each
uv run python manage.py seed_data

# Custom counts
uv run python manage.py seed_data --tags 500 --wide 500 --departments 10

# Re-seed from scratch
uv run python manage.py seed_data --clear
```

## Project Structure

```
example_project/
    pyproject.toml              # Dependencies with uv sources
    README.md                   # This file
    manage.py                   # Django CLI
    example_project/
        settings.py             # Django + django-tortoise-objects config
        asgi.py                 # ASGI application
        urls.py                 # Root URL configuration
    demo/
        models.py               # Tag, WideModel, Department, Team, Employee
        views.py                # Async demo views
        urls.py                 # Demo URL patterns
        admin.py                # Admin registrations
        management/commands/
            seed_data.py        # Data seeding command
    benchmarks/
        runner.py               # Benchmark framework (timing, stats)
        diagrams.py             # Chart generation (matplotlib)
        bench_small.py          # Tag model benchmarks
        bench_wide.py           # WideModel benchmarks
        bench_hierarchy.py      # Hierarchy model benchmarks
        __main__.py             # CLI entry point
    diagrams/                   # Generated benchmark charts (PNG)
```
