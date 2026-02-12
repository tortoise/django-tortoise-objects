"""
Management command to generate static Tortoise ORM model source files.

Usage::

    python manage.py generate_tortoise_models [--output-dir DIR] [--app-label APP ...]
                                               [--tortoise-app-name NAME]

Produces one Python file per Django app containing Tortoise ORM model classes
that mirror the Django models.  The generated files can be inspected,
customized, and version-controlled.
"""

import os
from collections import defaultdict

from django.apps import apps
from django.core.management.base import BaseCommand

from django_tortoise.code_generator import render_app_module, render_model_source
from django_tortoise.conf import get_config, should_include
from django_tortoise.introspection import introspect_model, should_skip_model


class Command(BaseCommand):
    help = "Generate static Tortoise ORM model source files from Django models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=".",
            help='Directory where generated files are written (default: ".").',
        )
        parser.add_argument(
            "--app-label",
            nargs="*",
            default=None,
            help="Restrict generation to specific Django app(s).",
        )
        parser.add_argument(
            "--tortoise-app-name",
            default="django_tortoise",
            help='Tortoise app name used in Meta.app and FK references (default: "django_tortoise").',
        )

    def handle(self, *args, **options):
        output_dir = options["output_dir"]
        app_labels = options["app_label"]
        tortoise_app_name = options["tortoise_app_name"]

        config = get_config()
        include_patterns = config.get("INCLUDE_MODELS")
        exclude_patterns = config.get("EXCLUDE_MODELS")

        all_models = apps.get_models()

        # Filter by --app-label if specified
        if app_labels:
            all_models = [m for m in all_models if m._meta.app_label in app_labels]

        # Two-pass approach mirroring apps.py
        # Pass 1: Introspect and build class_name_map
        eligible = []  # list of (django_model, label, model_info)
        class_name_map = {}  # django_model -> tortoise class name

        for django_model in all_models:
            label = f"{django_model._meta.app_label}.{django_model.__name__}"

            if not should_include(label, include_patterns, exclude_patterns):
                continue

            model_info = introspect_model(django_model)

            skip, _reason = should_skip_model(model_info)
            if skip:
                continue

            tortoise_class_name = f"{django_model.__name__}Tortoise"
            class_name_map[django_model] = tortoise_class_name
            eligible.append((django_model, label, model_info))

        # Pass 2: Render source code grouped by app_label
        models_by_app = defaultdict(list)
        for _django_model, _label, model_info in eligible:
            result = render_model_source(model_info, tortoise_app_name, class_name_map)
            if result is not None:
                models_by_app[model_info.app_label].append(result)

        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)

        # Write files
        files_written = []
        total_models = 0
        for app_label, model_results in sorted(models_by_app.items()):
            filename = f"tortoise_models_{app_label}.py"
            filepath = os.path.join(output_dir, filename)
            source = render_app_module(model_results, app_label)

            with open(filepath, "w") as f:
                f.write(source)

            files_written.append(filename)
            total_models += len(model_results)

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {total_models} Tortoise model(s) in {len(files_written)} file(s)."
            )
        )
        for filename in files_written:
            self.stdout.write(f"  {filename}")
