#!/usr/bin/env python
"""Build a static, try-it-yourself copy of the seeded Flanker study for the docs site.

GitHub Pages can't run Django, but a study page is plain HTML and JavaScript once Django
has rendered it. So this renders the real ``study_detail.html`` template in preview mode
(nothing is ever posted), points its script tags at copies of the jsPsych files next to
it, and writes the lot into ``docs/demo/flanker/``. mkdocs copies that folder into the
built site as-is.

Only the one plugin the Flanker timeline uses is loaded, rather than all 53, so the demo
is a fraction of the size of a real study page.

Usage:  uv run python scripts/build_demo.py
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.template.loader import render_to_string  # noqa: E402

from study.models import Study  # noqa: E402

JSPSYCH_DIR = ROOT / "study" / "static" / "study" / "jspsych"
OUT_DIR = ROOT / "docs" / "demo" / "flanker"
FILES = ["jspsych.js", "jspsych.css", "plugin-html-keyboard-response.js"]


def main():
    # An unsaved Study: the template only reads its name, slug, code and completion_url.
    study = Study(
        name="Flanker task",
        slug="flanker",
        code=(ROOT / "study" / "seed_studies" / "flanker.js").read_text(),
    )
    html = render_to_string(
        "study/study_detail.html",
        {
            "study": study,
            "preview": True,  # the page never POSTs, so there's no backend to miss
            "jspsych_plugins": ["plugin-html-keyboard-response.js"],
            "participant_id": "",
            "condition": "",
            "csrf_token": "",
        },
    )
    # Static URLs become paths relative to the demo folder. The survey stylesheet is
    # only needed by the survey plugin, which this demo doesn't load.
    html = html.replace("/static/study/jspsych/", "jspsych/")
    html = "\n".join(line for line in html.splitlines() if "survey.min.css" not in line)

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "jspsych").mkdir(parents=True)
    (OUT_DIR / "index.html").write_text(html + "\n")
    for name in FILES:
        shutil.copy(JSPSYCH_DIR / name, OUT_DIR / "jspsych" / name)
    print(f"Wrote {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
