from django.contrib import admin

from .models import Participant, Researcher, Study, StudyData


@admin.register(Researcher)
class ResearcherAdmin(admin.ModelAdmin):
    list_display = ["name", "email"]


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created"]
    prepopulated_fields = {"slug": ["name"]}  # auto-fill the slug from the name while typing
    filter_horizontal = ["researchers"]  # a nicer picker for the ManyToMany


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ["external_id", "created"]


@admin.register(StudyData)
class StudyDataAdmin(admin.ModelAdmin):
    list_display = ["id", "study", "participant", "condition", "created"]
    list_filter = ["study", "condition"]
    readonly_fields = ["study", "participant", "condition", "data", "created"]
