.DEFAULT_GOAL := help

.PHONY: help install lint typecheck check test fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install dev dependencies with uv
	uv sync --extra dev

lint: ## Run ruff linter and format check
	uv run ruff check django_tortoise/ tests/
	uv run ruff format --check django_tortoise/ tests/

typecheck: ## Run mypy type checker
	uv run mypy django_tortoise/

check: lint typecheck ## Run all checks (lint + typecheck)

test: ## Run tests with pytest
	uv run pytest tests/ -v

style: ## Auto-fix lint issues and format code
	uv run ruff check --fix django_tortoise/ tests/
	uv run ruff format django_tortoise/ tests/
