"""Admin registration for demo models."""

from django.contrib import admin

from demo.models import Department, Employee, Tag, Team, WideModel

admin.site.register(Tag)
admin.site.register(WideModel)
admin.site.register(Department)
admin.site.register(Team)
admin.site.register(Employee)
