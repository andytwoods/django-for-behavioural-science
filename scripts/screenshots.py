#!/usr/bin/env python
"""Regenerate the tutorial's screenshots from the *running* answer-key app.

This is the manual "figure refresh" runbook described in PLAN §9e: run it on each
Django / jsPsych / Bulma bump (the Dependabot PR is your reminder). It boots its
own dev server, drives a headless Chromium via Playwright over each documented
page, and writes PNGs into ``docs/assets/img/``. It also doubles as a headless
check that jsPsych genuinely renders (not just that the HTML is served).

Usage:  uv run python scripts/screenshots.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "assets" / "img"
PORT = 8009
BASE = f"http://127.0.0.1:{PORT}"
M1_PORT = 8010  # the chapter-2 milestone runs its own server, see capture_m1_admin()
ADMIN_USER, ADMIN_PASS = "admin", "admin"  # dev-only superuser


def wait_for_server(url: str, timeout: float = 30.0) -> None:
    """Poll until the server answers (any HTTP status counts as 'up')."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except urllib.error.HTTPError:
            return  # a 404 still means the server is listening
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.3)
    raise SystemExit(f"Server did not come up at {url} within {timeout}s")


def capture(page, path: str, out_name: str, *, advance_key: str | None = None,
            expect_text: str | None = None) -> None:
    page.goto(f"{BASE}{path}", wait_until="networkidle")
    if expect_text:
        # Headless proof that jsPsych rendered into the DOM, not just that HTML was served.
        page.wait_for_selector(f"text={expect_text}", timeout=5000)
    if advance_key:
        page.keyboard.press(advance_key)   # dismiss the jsPsych instructions screen
        page.wait_for_timeout(900)         # fixation (500ms) then the trial stimulus
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT_DIR / out_name))
    print(f"  captured {out_name}")


SEED_DEMO = """
from study.models import Study, Participant, Researcher, StudyData
flanker = Study.objects.get(slug='flanker')
stroop = Study.objects.get(slug='stroop')
# The same three researchers, and the same ownership, as the models/tables figure in the
# paper: Flanker has two owners, Laryssa owns both studies, Marusa owns none yet (which
# also leaves someone in the picker's unselected pane for that screenshot).
Researcher.objects.all().delete()
woods = Researcher.objects.create(name='Andy Woods', email='a.woods@example.edu')
whittaker = Researcher.objects.create(name='Laryssa Whittaker', email='l.whittaker@example.edu')
Researcher.objects.create(name='Maruša Levstek', email='m.levstek@example.edu')
flanker.researchers.set([woods, whittaker])
stroop.researchers.set([whittaker])
study = flanker
StudyData.objects.filter(study=study, condition='demo').delete()
for i in range(3):
    p, _ = Participant.objects.get_or_create(external_id=f'demo-p{i+1}')
    StudyData.objects.create(
        study=study, participant=p, condition='demo',
        data=[{'rt': 400 + j * 25, 'correct': j % 4 != 0} for j in range(8)],
    )
"""


# Enough of the real Flanker timeline to make the Code field look like a pasted study
# rather than an empty box, without the screenshot turning into a wall of JavaScript.
ADD_FORM_CODE = """const fixation = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: '<p style="font-size:48px;">+</p>',
  choices: "NO_KEYS",
  trial_duration: 500
};
"""


def capture_study_form(page) -> None:
    """The site's own "register a study" form (Going further: registering studies).

    Two shots: the form filled in and ready to send, then the same form after a POST with
    a slug that is already taken, which is where the ModelForm's validation shows itself.
    Neither leaves a row behind. The first is never submitted, and the second is rejected.
    """
    page.set_viewport_size({"width": 1000, "height": 830})
    page.goto(f"{BASE}/study/new/", wait_until="networkidle")
    page.fill("#id_name", "Posner cueing task")
    page.fill("#id_slug", "posner")
    page.fill("#id_code", ADD_FORM_CODE)
    # fill() leaves the last field focused, and its focus ring in the shot would suggest
    # the reader had clicked there. Blur it.
    page.eval_on_selector("#id_code", "el => el.blur()")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT_DIR / "study-form.png"))
    print("  captured study-form.png")

    # The failure path: 'flanker' is taken, so the unique=True on Study.slug comes back as
    # a message on the field rather than as a database error. The error line adds a row,
    # hence the slightly taller viewport.
    page.set_viewport_size({"width": 1000, "height": 855})
    page.fill("#id_slug", "flanker")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("text=already exists")
    page.screenshot(path=str(OUT_DIR / "study-form-errors.png"))
    print("  captured study-form-errors.png")


def seed_demo_data() -> None:
    """Create a few illustrative runs so the dashboard screenshot isn't empty."""
    subprocess.run(["uv", "run", "python", "manage.py", "shell", "-c", SEED_DEMO],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


SEED_M1 = """
from django.contrib.auth.models import User
from study.models import Study
User.objects.create_superuser('admin', 'admin@example.com', 'admin')
Study.objects.create(name='Flanker task', slug='flanker', code='// your jsPsych timeline')
"""


def capture_m1_admin() -> None:
    """Capture the admin as it looks at the *chapter 1* milestone, not as it looks now.

    Chapter 1 ends at the ``m1-study-model`` tag, where ``Study`` is four fields and the
    app registers one model. Screenshotting today's admin there would show the reader
    columns and models they haven't written yet, so we check that tag out into a throwaway
    worktree and photograph it. Run from the repo's own interpreter (not ``uv run``) so uv
    doesn't try to build an environment inside the worktree.
    """
    work = Path(tempfile.mkdtemp(prefix="screenshots-m1-"))
    tree = work / "repo"
    subprocess.run(["git", "worktree", "add", "--detach", str(tree), "m1-study-model"],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server = None
    try:
        run = lambda *a: subprocess.run([sys.executable, "manage.py", *a], cwd=tree,
                                        check=True, stdout=subprocess.DEVNULL)
        run("migrate")
        run("shell", "-c", SEED_M1)
        server = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "--noreload", str(M1_PORT)],
            cwd=tree, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{M1_PORT}"
        wait_for_server(f"{base}/admin/")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1000, "height": 460})
            page.goto(f"{base}/admin/login/?next=/admin/study/study/", wait_until="networkidle")
            page.fill("#id_username", ADMIN_USER)
            page.fill("#id_password", ADMIN_PASS)
            page.click("input[type=submit]")
            page.wait_for_load_state("networkidle")
            page.wait_for_selector("text=Select study to change")
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(OUT_DIR / "admin-studies-m1.png"))
            print("  captured admin-studies-m1.png")
            browser.close()
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
        subprocess.run(["git", "worktree", "remove", "--force", str(tree)],
                       cwd=ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    seed_demo_data()
    server = subprocess.Popen(
        ["uv", "run", "python", "manage.py", "runserver", "--noreload", str(PORT)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server(f"{BASE}/study/flanker/")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1000, "height": 700})

            # Log in first: the dashboard is @staff_member_required, so an anonymous
            # capture would just screenshot the login redirect.
            page.goto(f"{BASE}/admin/login/?next=/admin/study/study/", wait_until="networkidle")
            page.fill("#id_username", ADMIN_USER)
            page.fill("#id_password", ADMIN_PASS)
            page.click("input[type=submit]")
            page.wait_for_load_state("networkidle")

            print("Capturing researcher pages:")
            capture(page, "/", "studies-index.png", expect_text="Studies")
            capture(page, "/study/flanker/dashboard/", "dashboard.png", expect_text="Datasets")
            capture_study_form(page)

            print("Capturing study pages (also verifies jsPsych renders):")
            capture(page, "/study/flanker/", "flanker-instructions.png",
                    expect_text="CENTRE arrow")
            capture(page, "/study/flanker/", "flanker-trial.png",
                    advance_key="f", expect_text="CENTRE arrow")
            capture(page, "/study/stroop/", "stroop-instructions.png",
                    expect_text="INK colour")

            print("Capturing admin:")
            page.set_viewport_size({"width": 1000, "height": 640})
            page.goto(f"{BASE}/admin/study/study/", wait_until="networkidle")
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(OUT_DIR / "admin-studies.png"))
            print("  captured admin-studies.png")

            # The Researcher changelist (Going further: study ownership), the same three
            # people the many-to-many diagram on that page walks through.
            page.goto(f"{BASE}/admin/study/researcher/", wait_until="networkidle")
            page.screenshot(path=str(OUT_DIR / "admin-researchers.png"))
            print("  captured admin-researchers.png")

            # The captured runs themselves (chapter 6): the StudyData changelist, one row
            # per participant run. Uses the demo data seeded above so it isn't empty.
            page.goto(f"{BASE}/admin/study/studydata/", wait_until="networkidle")
            page.screenshot(path=str(OUT_DIR / "admin-studydata.png"))
            print("  captured admin-studydata.png")

            # The "Add study" form (chapter 2), cropped to the three fields that chapter
            # asks the reader to fill in. The rest of the form arrives in later chapters,
            # so showing all of it here would hand them fields they haven't met yet.
            page.set_viewport_size({"width": 1200, "height": 1000})
            page.goto(f"{BASE}/admin/study/study/add/", wait_until="networkidle")
            page.fill("#id_name", "Flanker task")
            page.fill("#id_code", ADD_FORM_CODE)
            # prepopulated_fields fills the slug from the name as you type, so it has just
            # written "flanker-task". Set the value directly afterwards: typing into the
            # field races that JS and ends up with the two concatenated.
            page.wait_for_timeout(300)
            page.eval_on_selector("#id_slug", "el => el.value = 'flanker'")
            first = page.locator(".field-name").bounding_box()
            last = page.locator(".field-code").bounding_box()
            page.screenshot(path=str(OUT_DIR / "admin-study-add.png"), clip={
                "x": first["x"] - 12,
                "y": first["y"] - 12,
                # Stop at the code field's help text: a few pixels more and the top edge of
                # the next field (a later chapter's) creeps into the shot.
                "width": max(first["width"], last["width"]) + 24,
                "height": last["y"] + last["height"] - first["y"] + 14,
            })
            print("  captured admin-study-add.png")

            # The Study change form, cropped to the widget below: the full form is
            # dominated by the code textarea, and the researchers picker sits well down
            # the page.
            page.goto(f"{BASE}/admin/study/study/", wait_until="networkidle")
            page.click("text=Flanker task")
            page.wait_for_load_state("networkidle")
            page.set_viewport_size({"width": 1400, "height": 1200})

            # The researchers ManyToMany widget (filter_horizontal two-pane picker).
            researchers = page.locator(".field-researchers")
            researchers.scroll_into_view_if_needed()
            page.wait_for_timeout(500)  # let the admin's SelectFilter JS finish laying out
            researchers.screenshot(path=str(OUT_DIR / "admin-study-researchers.png"))
            print("  captured admin-study-researchers.png")

            browser.close()

        print("Capturing the chapter-2 milestone admin:")
        capture_m1_admin()

        print(f"\nAll screenshots written to {OUT_DIR.relative_to(ROOT)}/")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
