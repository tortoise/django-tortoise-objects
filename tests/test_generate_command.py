"""
Tests for the generate_tortoise_models management command.

Validates command output, file generation, filtering, and the
_should_include refactor to conf.py.
"""

import ast
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temporary directory for generated files."""
    return tmp_path


class TestCommandGeneratesFiles:
    """Tests for basic command file generation."""

    def test_generates_output_file_for_testapp(self, output_dir):
        """TC-2.1: Command generates output files for test app."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        output_file = output_dir / "tortoise_models_testapp.py"
        assert output_file.exists()
        # File is valid Python
        source = output_file.read_text()
        ast.parse(source)

    def test_generated_file_contains_expected_models(self, output_dir):
        """TC-2.2: Generated file contains expected model classes."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        source = (output_dir / "tortoise_models_testapp.py").read_text()
        assert "class CategoryTortoise(Model):" in source
        assert "class TagTortoise(Model):" in source
        assert "class ArticleTortoise(Model):" in source

    def test_generated_file_has_header(self, output_dir):
        """TC-2.3: Generated file has auto-generated header comment."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        source = (output_dir / "tortoise_models_testapp.py").read_text()
        assert source.startswith("# Auto-generated")


class TestAppLabelFiltering:
    """Tests for --app-label filtering."""

    def test_app_label_filters_to_specific_app(self, output_dir):
        """TC-2.4: --app-label filters to specific app."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        assert (output_dir / "tortoise_models_testapp.py").exists()
        assert not (output_dir / "tortoise_models_auth.py").exists()


class TestOutputDir:
    """Tests for --output-dir."""

    def test_output_dir_controls_placement(self, output_dir):
        """TC-2.5: --output-dir controls file placement."""
        subdir = output_dir / "subdir"
        subdir.mkdir()
        call_command(
            "generate_tortoise_models",
            output_dir=str(subdir),
            app_label=["testapp"],
        )
        assert (subdir / "tortoise_models_testapp.py").exists()

    def test_creates_nonexistent_output_dir(self, output_dir):
        """TC-2.9: Command handles output directory that does not exist."""
        new_dir = output_dir / "new_dir"
        call_command(
            "generate_tortoise_models",
            output_dir=str(new_dir),
            app_label=["testapp"],
        )
        assert new_dir.exists()
        assert (new_dir / "tortoise_models_testapp.py").exists()


class TestModelFiltering:
    """Tests for INCLUDE_MODELS and EXCLUDE_MODELS filtering."""

    def test_exclude_models_respected(self, output_dir):
        """TC-2.6: EXCLUDE_MODELS setting is respected."""
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = {"EXCLUDE_MODELS": ["testapp.Tag"]}
            call_command(
                "generate_tortoise_models",
                output_dir=str(output_dir),
                app_label=["testapp"],
            )
        filepath = output_dir / "tortoise_models_testapp.py"
        if filepath.exists():
            source = filepath.read_text()
            assert "class TagTortoise" not in source

    def test_include_models_respected(self, output_dir):
        """TC-2.7: INCLUDE_MODELS setting is respected."""
        with patch("django_tortoise.conf.settings") as mock_settings:
            mock_settings.TORTOISE_OBJECTS = {"INCLUDE_MODELS": ["testapp.Category"]}
            call_command(
                "generate_tortoise_models",
                output_dir=str(output_dir),
                app_label=["testapp"],
            )
        filepath = output_dir / "tortoise_models_testapp.py"
        source = filepath.read_text()
        assert "class CategoryTortoise" in source
        assert "class ArticleTortoise" not in source
        assert "class TagTortoise" not in source


class TestCommandOutput:
    """Tests for command stdout output."""

    def test_prints_summary(self, output_dir):
        """TC-2.8: Command prints summary to stdout."""
        out = StringIO()
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
            stdout=out,
        )
        output = out.getvalue()
        assert "Generated" in output
        assert "model" in output.lower()
        assert "file" in output.lower()


class TestGeneratedFileContent:
    """Tests for generated file content."""

    def test_contains_proper_imports(self, output_dir):
        """TC-2.10: Generated file contains proper imports."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        source = (output_dir / "tortoise_models_testapp.py").read_text()
        assert "from tortoise.models import Model" in source
        assert "from tortoise import fields" in source

    def test_generated_source_is_parseable(self, output_dir):
        """TC-2.11: Generated source can be parsed by Python."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        source = (output_dir / "tortoise_models_testapp.py").read_text()
        # Should not raise SyntaxError
        compile(source, "tortoise_models_testapp.py", "exec")


class TestShouldIncludeMovedToConf:
    """Tests that _should_include was moved to conf.py and apps.py still works."""

    def test_conf_should_include_exists(self):
        """TC-2.12: should_include is available from conf."""
        from django_tortoise.conf import should_include

        assert callable(should_include)

    def test_conf_should_include_works(self):
        """TC-2.12: conf.should_include works correctly."""
        from django_tortoise.conf import should_include

        assert should_include("myapp.MyModel", None, None)
        assert not should_include("myapp.MyModel", None, ["myapp.*"])
        assert should_include("myapp.MyModel", ["myapp.*"], None)

    def test_apps_should_include_still_works(self):
        """TC-2.12: apps._should_include still works (backward compat)."""
        from django_tortoise.apps import _should_include

        assert _should_include("myapp.MyModel", None, None)
        assert not _should_include("myapp.MyModel", None, ["myapp.*"])

    def test_existing_apps_tests_still_pass(self):
        """TC-2.12: Existing tests in test_apps.py still pass."""
        from django_tortoise.registry import model_registry
        from tests.testapp.models import Category, Tag

        # Registry should still be populated after ready()
        assert model_registry.is_registered(Category)
        assert model_registry.is_registered(Tag)


# ---------------------------------------------------------------------------
# TC-3.6: Full pipeline round-trip tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Full round-trip tests for the management command."""

    def test_full_pipeline_for_testapp(self, output_dir):
        """TC-3.6: Full pipeline round-trip for testapp."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        filepath = output_dir / "tortoise_models_testapp.py"
        source = filepath.read_text()

        # All expected model classes are present
        expected_models = [
            "CategoryTortoise",
            "TagTortoise",
            "ArticleTortoise",
            "ProfileTortoise",
            "EnumTestModelTortoise",
            "CommentTortoise",
        ]
        for model_name in expected_models:
            assert f"class {model_name}(Model):" in source, (
                f"{model_name} not found in generated source"
            )

        # ast.parse succeeds
        tree = ast.parse(source)

        # Verify Meta.table values match Django _meta.db_table
        from tests.testapp.models import (
            Article,
            Category,
            Comment,
            EnumTestModel,
            Profile,
            Tag,
        )

        model_map = {
            "CategoryTortoise": Category,
            "TagTortoise": Tag,
            "ArticleTortoise": Article,
            "ProfileTortoise": Profile,
            "EnumTestModelTortoise": EnumTestModel,
            "CommentTortoise": Comment,
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in model_map:
                django_model = model_map[node.name]
                expected_table = django_model._meta.db_table
                # Find Meta inner class and table assignment
                for item in node.body:
                    if isinstance(item, ast.ClassDef) and item.name == "Meta":
                        for meta_item in item.body:
                            if (
                                isinstance(meta_item, ast.Assign)
                                and len(meta_item.targets) == 1
                                and isinstance(meta_item.targets[0], ast.Name)
                                and meta_item.targets[0].id == "table"
                            ):
                                table_value = meta_item.value
                                if isinstance(table_value, ast.Constant):
                                    assert table_value.value == expected_table, (
                                        f"Table mismatch for {node.name}: "
                                        f"expected {expected_table}, "
                                        f"got {table_value.value}"
                                    )

    def test_generated_file_contains_on_delete_import(self, output_dir):
        """Generated file with relational models includes OnDelete import."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        source = (output_dir / "tortoise_models_testapp.py").read_text()
        assert "from tortoise.fields.relational import OnDelete" in source

    def test_generated_file_contains_enum_import(self, output_dir):
        """Generated file with enum fields includes enum import."""
        call_command(
            "generate_tortoise_models",
            output_dir=str(output_dir),
            app_label=["testapp"],
        )
        source = (output_dir / "tortoise_models_testapp.py").read_text()
        # Should import Status or Color enum from the testapp models
        assert "import Status" in source or "import Color" in source
