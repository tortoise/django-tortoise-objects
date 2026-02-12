"""
Test Django models used by the django-tortoise-objects test suite.

Provides a comprehensive set of models exercising different field types,
relational patterns, and Meta options.
"""

from django.db import models


class Category(models.Model):
    """A simple model with basic field types."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "testapp_category"
        verbose_name_plural = "categories"


class Tag(models.Model):
    """A minimal model with a unique CharField."""

    name = models.CharField(max_length=50, unique=True)


class Article(models.Model):
    """A model exercising many field types and relational patterns."""

    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="articles")
    tags = models.ManyToManyField(Tag, related_name="articles", blank=True)
    views = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    uuid = models.UUIDField(unique=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("title", "category")]


class Profile(models.Model):
    """A model with a OneToOneField to auth.User."""

    user = models.OneToOneField("auth.User", on_delete=models.CASCADE)
    bio = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", blank=True, default="")


class Status(models.IntegerChoices):
    DRAFT = 1, "Draft"
    PUBLISHED = 2, "Published"
    ARCHIVED = 3, "Archived"


class Color(models.TextChoices):
    RED = "red", "Red"
    GREEN = "green", "Green"
    BLUE = "blue", "Blue"


PLAIN_CHOICES = [
    (1, "Low"),
    (2, "Medium"),
    (3, "High"),
]


class EnumTestModel(models.Model):
    """A model exercising enum-backed and plain-tuple choices."""

    status = models.IntegerField(choices=Status, default=Status.DRAFT)
    color = models.CharField(choices=Color, max_length=10, default=Color.RED)
    priority = models.IntegerField(choices=PLAIN_CHOICES, default=1)
    no_choices = models.IntegerField(default=0)


class Comment(models.Model):
    """A model with a self-referential ForeignKey and various field types."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    author_name = models.CharField(max_length=100)
    body = models.TextField()
    email = models.EmailField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
