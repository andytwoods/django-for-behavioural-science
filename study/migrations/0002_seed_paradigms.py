from pathlib import Path

from django.db import migrations

# Two classic paradigms shipped pre-loaded so a fresh clone works immediately and the
# tests have data (PLAN §8). The timeline code lives as plain .js files in
# study/seed_studies/ (a single source of truth the docs can link to and readers can
# copy); this migration just reads them into Study.code.
SEED_DIR = Path(__file__).resolve().parent.parent / "seed_studies"

SEEDS = [
    ("Flanker task", "flanker", "flanker.js"),
    ("Stroop task", "stroop", "stroop.js"),
]


def seed_paradigms(apps, schema_editor):
    Study = apps.get_model("study", "Study")
    for name, slug, filename in SEEDS:
        code = (SEED_DIR / filename).read_text()
        Study.objects.update_or_create(slug=slug, defaults={"name": name, "code": code})


def unseed_paradigms(apps, schema_editor):
    Study = apps.get_model("study", "Study")
    Study.objects.filter(slug__in=[slug for _, slug, _ in SEEDS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_paradigms, unseed_paradigms),
    ]
