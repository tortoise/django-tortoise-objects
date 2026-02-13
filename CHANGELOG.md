# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
