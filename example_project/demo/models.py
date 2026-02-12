"""
Demo models for django-tortoise-objects example project.

Three tiers:
  - Tag: simple model (benchmark baseline)
  - WideModel: 20+ fields of varied types (wide-row benchmark)
  - Department / Team / Employee: 3-level hierarchy (relation benchmark)
"""

import uuid

from django.db import models


# ---------------------------------------------------------------------------
# Tier 1: Small model
# ---------------------------------------------------------------------------

class Tag(models.Model):
    """Minimal model for baseline benchmarks."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "demo_tag"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Tier 2: Wide model (20+ fields)
# ---------------------------------------------------------------------------

class WideModel(models.Model):
    """
    Model with 20+ fields exercising every supported field type.
    Used to benchmark serialization/deserialization overhead for wide rows.
    """
    # String fields
    char_field = models.CharField(max_length=200)
    text_field = models.TextField(default="")
    slug_field = models.SlugField(max_length=100, default="")
    email_field = models.EmailField(default="")
    url_field = models.URLField(default="")
    ip_field = models.GenericIPAddressField(null=True, blank=True)

    # Numeric fields
    int_field = models.IntegerField(default=0)
    bigint_field = models.BigIntegerField(default=0)
    smallint_field = models.SmallIntegerField(default=0)
    pos_int_field = models.PositiveIntegerField(default=0)
    float_field = models.FloatField(default=0.0)
    decimal_field = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    # Boolean
    bool_field = models.BooleanField(default=False)

    # Date/Time fields
    date_field = models.DateField(null=True, blank=True)
    datetime_field = models.DateTimeField(null=True, blank=True)
    time_field = models.TimeField(null=True, blank=True)
    duration_field = models.DurationField(null=True, blank=True)

    # Special fields
    uuid_field = models.UUIDField(default=uuid.uuid4)
    json_field = models.JSONField(default=dict)
    binary_field = models.BinaryField(null=True, blank=True)

    # File-like fields (stored as paths / CharFields by Tortoise)
    file_field = models.FileField(upload_to="uploads/", blank=True, default="")

    # Auto timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "demo_wide_model"

    def __str__(self):
        return f"WideModel(id={self.pk})"


# ---------------------------------------------------------------------------
# Tier 3: Hierarchy models (3 levels)
# ---------------------------------------------------------------------------

class Department(models.Model):
    """Top-level organizational unit."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "demo_department"

    def __str__(self):
        return self.name


class Team(models.Model):
    """Mid-level unit belonging to a Department."""
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="teams"
    )
    focus_area = models.CharField(max_length=200, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "demo_team"

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Leaf-level: belongs to a Team (-> Department)."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="employees"
    )
    hire_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_manager = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "demo_employee"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
