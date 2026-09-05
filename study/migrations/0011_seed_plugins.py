from django.db import migrations

# The seeded paradigms (0002) are both plain keyboard-response tasks, so they need exactly
# one plugin. Setting it here means a fresh clone serves them with one small script file
# rather than falling back to "load every plugin we ship".
SEED_PLUGINS = {
    "flanker": ["plugin-html-keyboard-response.js"],
    "stroop": ["plugin-html-keyboard-response.js"],
}


def set_seed_plugins(apps, schema_editor):
    Study = apps.get_model("study", "Study")
    for slug, plugins in SEED_PLUGINS.items():
        Study.objects.filter(slug=slug).update(plugins=plugins)


def clear_seed_plugins(apps, schema_editor):
    Study = apps.get_model("study", "Study")
    Study.objects.filter(slug__in=SEED_PLUGINS).update(plugins=[])


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0010_study_plugins"),
    ]

    operations = [
        migrations.RunPython(set_seed_plugins, clear_seed_plugins),
    ]
