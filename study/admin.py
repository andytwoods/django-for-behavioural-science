from django.contrib import admin

from .models import Study


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created"]
    prepopulated_fields = {"slug": ["name"]}  # auto-fill the slug from the name while typing
