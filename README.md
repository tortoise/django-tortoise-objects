# django-tortoise-objects

Bridge Django ORM models to [Tortoise ORM](https://github.com/tortoise/tortoise-orm) for truly async database access. Define your models once in Django, query them asynchronously via Tortoise — no duplicate schema, no manual sync.

## Why?

Django's async ORM wraps synchronous calls in `sync_to_async` threads. Tortoise ORM is natively async but requires its own model definitions. This library eliminates that trade-off:

- **Single source of truth** — Django models define the schema, migrations, and admin
- **Truly async queries** — Tortoise ORM handles the actual database I/O with native async drivers
- **Zero boilerplate** — Add to `INSTALLED_APPS`, and every model gets a `tortoise_objects` manager

## Installation

```bash
pip install django-tortoise-objects
```

With database drivers:

```bash
# PostgreSQL
pip install django-tortoise-objects[pg]

# SQLite
pip install django-tortoise-objects[sqlite]

# MySQL
pip install django-tortoise-objects[mysql]

# All drivers
pip install django-tortoise-objects[all]
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ...
    "django_tortoise",
    # ... your apps
]
```

### 2. Query your existing Django models asynchronously

```python
from myapp.models import Article

# All standard query operations — fully async, no sync_to_async wrapper
articles = await Article.tortoise_objects.filter(published=True)
article = await Article.tortoise_objects.get(id=42)
count = await Article.tortoise_objects.count()
exists = await Article.tortoise_objects.filter(title="foo").exists()

# Create, update, delete
article = await Article.tortoise_objects.create(title="Hello", body="World")
await Article.tortoise_objects.filter(published=False).update(draft=True)
await Article.tortoise_objects.filter(id=42).delete()

# Chaining
recent = await Article.tortoise_objects.filter(published=True).order_by("-created_at").limit(10)

# Prefetch relations (via underlying Tortoise model)
employees = await Employee.tortoise_objects.model.all().prefetch_related("team")
```

### 3. Use in async Django views

```python
from django.http import JsonResponse
from myapp.models import Tag

async def tag_list(request):
    tags = await Tag.tortoise_objects.all()
    return JsonResponse({"tags": [{"id": t.id, "name": t.name} for t in tags]})
```

That's it. No Tortoise model definitions, no configuration files, no manual initialization.

## Configuration

Optional settings via `TORTOISE_OBJECTS` in your Django settings:

```python
TORTOISE_OBJECTS = {
    # Include only specific app models (fnmatch patterns)
    "INCLUDE_MODELS": ["myapp.*", "blog.*"],

    # Exclude specific models
    "EXCLUDE_MODELS": ["auth.*", "admin.*"],

    # Override database backend mapping
    "DB_ENGINE_MAP": {
        "django.db.backends.postgresql": "tortoise.backends.psycopg",
    },

    # Connection pool settings per database alias
    "CONNECTION_POOL": {
        "default": {"minsize": 5, "maxsize": 20},
    },

    # Logging level
    "LOG_LEVEL": "WARNING",
}
```

All settings are optional. With no configuration, all models are included and database backends are auto-detected from Django's `DATABASES` setting.

## Supported Field Types

| Django Field | Tortoise Field |
|---|---|
| CharField, SlugField, EmailField, URLField | CharField |
| TextField | TextField |
| IntegerField, BigIntegerField, SmallIntegerField | IntField, BigIntField, SmallIntField |
| BooleanField | BooleanField |
| FloatField | FloatField |
| DecimalField | DecimalField |
| DateField, DateTimeField, TimeField | DateField, DatetimeField, TimeField |
| DurationField | TimeDeltaField |
| UUIDField | UUIDField |
| JSONField | JSONField |
| BinaryField | BinaryField |
| FileField, ImageField | CharField (stores path) |
| ForeignKey | ForeignKeyField |
| OneToOneField | OneToOneField |
| ManyToManyField | ManyToManyField |
| AutoField, BigAutoField, SmallAutoField | IntField/BigIntField/SmallIntField (pk=True) |

## ASGI Lifespan

For production ASGI deployments, explicitly manage Tortoise connections:

```python
# asgi.py
from django_tortoise import init, close

async def lifespan(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await init()
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await close()
                await send({"type": "lifespan.shutdown.complete"})
                return
```

If you don't set up lifespan, connections are initialized lazily on first query.

## Generating Static Tortoise Models

By default, Tortoise models are generated dynamically at runtime. If you want static files you can inspect, customize, or version-control, use the management command:

```bash
# Generate for all apps
python manage.py generate_tortoise_models --output-dir ./tortoise_models

# Generate for a specific app
python manage.py generate_tortoise_models --app-label demo --output-dir .

# Custom Tortoise app name
python manage.py generate_tortoise_models --tortoise-app-name myapp
```

This produces one file per Django app (e.g., `tortoise_models_demo.py`):

```python
# Auto-generated by django-tortoise-objects. Do not edit manually.

import uuid

from tortoise import fields
from tortoise.fields.relational import OnDelete
from tortoise.models import Model


class DepartmentTortoise(Model):
    id = fields.BigIntField(primary_key=True, generated=True)
    name = fields.CharField(max_length=200)
    code = fields.CharField(unique=True, max_length=20)
    budget = fields.DecimalField(default=0, max_digits=14, decimal_places=2)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "demo_department"
        app = "django_tortoise"


class TeamTortoise(Model):
    id = fields.BigIntField(primary_key=True, generated=True)
    name = fields.CharField(max_length=200)
    department = fields.ForeignKeyField(
        "django_tortoise.DepartmentTortoise",
        related_name='teams',
        on_delete=OnDelete.CASCADE,
        source_field='department_id',
    )

    class Meta:
        table = "demo_team"
        app = "django_tortoise"
```

The command respects `INCLUDE_MODELS` and `EXCLUDE_MODELS` from your `TORTOISE_OBJECTS` settings.

## Limitations & Non-Goals

**Query results are Tortoise model instances, not Django models.** Methods like `tortoise_objects.get()` and `tortoise_objects.filter()` return Tortoise ORM objects. They cannot be passed directly to Django forms, serializers, admin, or template tags that expect Django model instances. Use `tortoise_objects` for async read/write paths (APIs, WebSockets, background tasks) and the regular Django ORM for everything else.

This library is **not** intended to:

- **Replace Django ORM** — it is a complementary tool for async-critical paths, not a full substitute. Django ORM remains the right choice for admin, forms, management commands, and sync views.
- **Manage schema or migrations** — all schema management is delegated to Django. Tortoise never writes to your database schema.
- **Support cross-ORM transactions** — you cannot mix Django and Tortoise queries in a single database transaction.
- **Provide Django admin integration** — Tortoise query results don't work with Django's admin site. Use Django's ORM for admin.
- **Expose Tortoise-specific features** — Tortoise signals, custom managers, and validators are not bridged.
- **Generate Django models from Tortoise** — the bridge is one-way only (Django → Tortoise).

**Other things to keep in mind:**

- Tortoise maintains its own connection pool, separate from Django's. Configure pool sizes via the `CONNECTION_POOL` setting to avoid excess connections.
- Unsupported or custom Django field types are silently skipped during model generation. Check logs at `DEBUG` level if a field is missing.
- ManyToManyField relations require that the related model is also included in the Tortoise bridge (not excluded via `EXCLUDE_MODELS`).

## Performance

Benchmarks comparing `tortoise_objects` vs Django's native async ORM (`aget`, `acreate`, etc.) on the same models and data. Measured on PostgreSQL (both using psycopg).

### PostgreSQL

![Benchmark results — PostgreSQL](example_project/diagrams/bench_postgres_summary.png)

- `tortoise_objects` wins on single-record ops: `get` 1.3-2.0x, `count` 1.3-1.5x, `exists` 1.5x
- `tortoise_objects` wins on writes: `create+delete` 1.4-2.6x
- Bulk fetches nearly tied

See [`example_project/README.md`](example_project/README.md) for full benchmark details, methodology, and raw data.

## Requirements

- Python >= 3.10
- Django >= 4.2
- Tortoise ORM >= 1.1.2

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
