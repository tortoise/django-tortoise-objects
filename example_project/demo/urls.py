"""URL patterns for the demo app."""

from django.urls import path

from demo import views

urlpatterns = [
    path("tags/", views.tag_list, name="tag-list"),
    path("tags/create/", views.tag_create, name="tag-create"),
    path("wide/", views.wide_model_list, name="wide-list"),
    path("employees/", views.employee_list, name="employee-list"),
    path("benchmark/quick/", views.quick_benchmark, name="quick-benchmark"),
]
