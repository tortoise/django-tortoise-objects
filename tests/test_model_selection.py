"""
Tests for model selection (Phase 4, Step 4.3).

Comprehensive tests for the include/exclude pattern logic and edge cases.
"""

from django_tortoise.apps import _should_include


class TestExcludeDjangoContrib:
    """Tests for excluding Django contrib models."""

    def test_exclude_auth_user(self):
        assert not _should_include("auth.User", None, ["auth.*"])

    def test_exclude_contenttypes(self):
        assert not _should_include("contenttypes.ContentType", None, ["contenttypes.*"])


class TestIncludeSpecificApp:
    """Tests for including a specific app's models only."""

    def test_include_testapp(self):
        assert _should_include("testapp.Article", ["testapp.*"], None)

    def test_exclude_other_app(self):
        assert not _should_include("otherapp.Model", ["testapp.*"], None)


class TestExcludeOverridesInclude:
    """Tests that exclude patterns take precedence over include."""

    def test_exclude_overrides(self):
        assert _should_include("testapp.Article", ["testapp.*"], ["testapp.Secret"])
        assert not _should_include("testapp.Secret", ["testapp.*"], ["testapp.Secret"])


class TestMultiplePatterns:
    """Tests for multiple include/exclude patterns."""

    def test_multiple_include(self):
        patterns = ["app1.*", "app2.*"]
        assert _should_include("app1.Model", patterns, None)
        assert _should_include("app2.Model", patterns, None)
        assert not _should_include("app3.Model", patterns, None)

    def test_multiple_exclude(self):
        patterns = ["app1.*", "app2.*"]
        assert not _should_include("app1.Model", None, patterns)
        assert not _should_include("app2.Model", None, patterns)
        assert _should_include("app3.Model", None, patterns)


class TestExactMatch:
    """Tests for exact (non-glob) pattern matching."""

    def test_exact_include(self):
        assert _should_include("myapp.MyModel", ["myapp.MyModel"], None)
        assert not _should_include("myapp.OtherModel", ["myapp.MyModel"], None)

    def test_exact_exclude(self):
        assert not _should_include("myapp.MyModel", None, ["myapp.MyModel"])
        assert _should_include("myapp.OtherModel", None, ["myapp.MyModel"])


class TestEmptyPatterns:
    """Tests for empty pattern lists vs None."""

    def test_none_include_means_all(self):
        assert _should_include("any.Model", None, None)

    def test_empty_list_include_means_none(self):
        """Empty include list means no models are included."""
        assert not _should_include("any.Model", [], None)

    def test_empty_list_exclude_means_none_excluded(self):
        """Empty exclude list means no models are excluded."""
        assert _should_include("any.Model", None, [])
