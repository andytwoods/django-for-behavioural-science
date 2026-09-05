from django.urls import path

from . import views

app_name = "study"

urlpatterns = [
    # / – landing page listing every study
    path("", views.study_list, name="list"),
    # /study/new/ – register a study through a form instead of the admin (staff only).
    # This must come *before* the <slug> pattern below, or "new" would be matched as a
    # slug and we'd 404 looking for a study called "new".
    path("study/new/", views.study_create, name="create"),
    # /study/<slug>/ – serve a study to a participant, e.g. /study/flanker/
    path("study/<slug:slug>/", views.study_detail, name="detail"),
    # /api/study/<slug>/data – jsPsych POSTs the trial data here at on_finish
    path("api/study/<slug:slug>/data", views.submit_data, name="data"),
    # researcher-facing views: dashboard + data export
    path("study/<slug:slug>/dashboard/", views.dashboard, name="dashboard"),
    path("study/<slug:slug>/export.csv", views.export_csv, name="export_csv"),
    path("study/<slug:slug>/export.json", views.export_json, name="export_json"),
]
