# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## 0.1.2

### Fixed

- Custom Django field types (e.g. `CustomIDField(CharField)`) are now resolved
  via MRO fallback when their `get_internal_type()` returns a name not in the
  field map. The library walks the field's ancestor classes to find a supported
  parent type, so models with custom primary key fields no longer lose their
  only data field and fail silently.
- Fixed `KeyError` / `ConnectionError` during Tortoise ORM initialization when
  a model with only unsupported fields was referenced by ForeignKey from another
  model. Failed models are now removed from the internal class name map so
  downstream FK references are gracefully skipped instead of crashing.

## 0.1.1

### Fixed

- Model creation errors now include the Django model name in the message
  (e.g. `Failed to create Tortoise model 'ArticleTortoise' for Django model 'blog.article': …`)
  instead of only showing the raw Tortoise exception.
- Stopped mapping `unique` and `db_index` attributes to generated Tortoise
  fields. The library relies on Django's existing database schema, so
  Tortoise-level index declarations are unnecessary and caused
  `ConfigurationError` for field types that reject them (e.g. `TextField`
  with `unique=True`).
