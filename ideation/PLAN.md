# Django Science Tutorial — Plan

Companion tutorial to the BRM paper *"First Steps in Django Web Development: Applied Examples
from Behavioural Research"* (Woods, 2026). This document is the ideation / scoping plan; it is
not the tutorial itself.

---

## 1. Why this exists

Two things drive this project:

1. **Reviewer pressure on the paper.** Reviewers 2 and 3 (and the editor) asked for a more
   hands-on, step-by-step path for researchers — from "I have an experiment" to "it's deployed
   and collecting data." We deliberately keep the *paper* at the mental-model altitude and let
   this companion carry the practical walkthrough. See `../DjangoPaperCorrections/response_to_reviewers.md`
   (items R2.1, R2.5, R2.9, R1.1, R1.2, R3.3, R3.6).

2. **Reviewer 1's specific, concrete suggestion.** R1 pointed out that the paper is too dismissive
   of SPAs / JavaScript and that many readers *already have* a front-end experiment (jsPsych,
   lab.js) and simply need somewhere to **host it and store the data** (R1.20, R1.21). That is the
   killer use case and the spine of this tutorial:

   > **You have a jsPsych experiment. How do you host it on your own Django backend and capture the
   > data — the way DataPipe / Pavlovia / JATOS do, but bespoke and under your own control?**

This is a genuinely useful, research-specific thing that the official Django tutorial and Django
Girls do *not* teach, so we are not duplicating them — we build on top of them.

## 2. Positioning — what it is and isn't

**It is:** a research-focused, worked tutorial that takes a real client-side experiment (jsPsych)
and connects it to a Django backend that stores, manages, and exports the data, then deploys it.

**It is not:** a from-zero "install Python, what is a variable" course. It assumes (and links to)
the basics:
- Official Django tutorial — https://docs.djangoproject.com/en/6.0/intro/tutorial01/
- Django Girls — https://tutorial.djangogirls.org/en/

**Audience:** a behavioural researcher who can write some Python, has (or can make) a jsPsych study,
and wants control over hosting + data that off-the-shelf platforms don't give them.

**Tone:** practical, opinionated, one blessed path per problem (link out for alternatives), every
step tied to the research app rather than a toy.

## 3. The core worked example

> **DECIDED — unified example.** This tutorial **extends the paper's running example** rather than
> starting a new app. The paper teaches the participant panel (`Study` ↔ `Researcher`, ManyToMany;
> views/templates/admin) using the `django_paper_2026` repo. This tutorial builds on that *same app*
> and adds the jsPsych-hosting + data-capture layer (`Participant`, `Session`, `Trial`, an API
> endpoint). Models are a clean subset→superset, so a reader flows paper-concept → tutorial-build with
> one continuous codebase. Keep model/app **names identical** to the paper so figures and code match.

A minimal-but-real Django project that is not just a jsPsych *host* but a
**mini study-hosting platform**: the researcher adds their own studies, the platform provides the
data-capture harness. This mirrors what TestXR / DataPipe / Pavlovia do, and *is* the paper's
participant-panel example extended (researchers register studies; participants now actually complete
them and their data is captured).

**The one-sentence thesis the tutorial teaches:**
> The platform provides the data-capture harness; the researcher provides only the experiment logic.

The app:

1. **Lets a researcher add their own study** (design decision below) — v1: paste their jsPsych
   *timeline* code into a `Study.code` field via a form / admin. The platform seeds a couple of
   classic paradigms (e.g. Flanker + Stroop) so a reader sees it working immediately.
2. **Serves each study** by wrapping the researcher's code with the jsPsych library + the
   data-capture plumbing. **Whether to sandbox is a trust-model decision, not a default** (see the
   trust-model note below) — v1 is single-tenant and un-sandboxed for simplicity.
3. **Identifies participants** via URL parameters: `participant_id`, `condition`, `study_id`
   (directly the R1.7 point — participant/condition IDs in URLs).
4. **Receives trial data** posted from jsPsych's `on_finish` / `on_data_update` to a Django API
   endpoint (fetch/AJAX → view), handling CSRF correctly.
5. **Stores it** in models: the paper's `Study` ↔ `Researcher` (ManyToMany) **plus** new
   `Participant`, `Session`, `Trial` — a real relational schema showing both ManyToMany (from the
   paper, kept intact) and the new ForeignKeys for data capture (ties back to paper R1.15–R1.17, R3.8).
6. **Lets the researcher see & export the data** — Django admin + a CSV/JSON export view.
7. **Is deployable** — one concrete PaaS path end-to-end.

This single example naturally teaches: URL routing, views, templates, static files, forms, models &
migrations, an API endpoint (POST/JSON), CSRF, sandboxing/trust boundaries, the admin, data export,
and deployment — i.e. the whole paper's mental model, made concrete around data collection.

### "How does a researcher add a study?" — v1 decision
- **Chosen (v1): paste a snippet + externally-hosted assets.** Researcher pastes their jsPsych
  timeline JS (+ optional HTML) into a `Study.code` field via a form/admin. **Media assets
  (images/audio/video) are hosted wherever the researcher likes** — GitHub / GitHub Pages, S3, their
  own CDN — and referenced by absolute HTTPS URL in the pasted code. The platform therefore never
  handles file uploads in v1: **it stores the *data*, the researcher's host serves the *media*.**
  That separation is itself a clean teaching point.
  - **Caveats to teach:** assets must be served over **HTTPS** (else mixed-content blocking);
    external hosts should be durable (link-rot warning); some asset access needs **CORS** headers
    (plain `<img>`/`<audio>` are fine cross-origin, but `fetch()`-ed assets need them) — a good,
    concrete web lesson.
- **Deferred to ch.12: upload a bundle** (zip of experiment with assets served by the platform) —
  now genuinely optional, since external hosting covers media-rich studies in v1.
- **Rejected: point-to-a-URL for the whole experiment** — defeats the purpose (they're not using our
  hosting/data capture).

### Trust model & sandboxing — the real lesson (DECISION: teach it, don't blanket-sandbox)
The question is *who is the threat*, which depends on single- vs multi-tenant:
- **Single-tenant (v1, and the paper's core framing):** the researcher deploys this backend for
  *their own* studies. Pasted code is *their own*, served to *their own* participants — trusted, no
  more dangerous than any code they deploy. **No sandbox.** Bonus: keeps the data flow simple —
  jsPsych `on_finish` POSTs straight to the same-origin Django API, CSRF cookie works.
- **Multi-tenant (optional hardening chapter):** if one deployment hosts *many* researchers' pasted
  studies, their JS runs on the app's origin. The real risk is an admin/researcher **previewing a
  study while logged into `/admin`** → same-origin JS hits admin endpoints with their cookies →
  takeover. Mitigation, best-first: **serve study code from a separate origin/subdomain**
  (CodePen/JSFiddle/googleusercontent model); lighter option: `<iframe sandbox="allow-scripts">`
  (null origin). Cost: data POST becomes cross-origin (no CSRF cookie) → route data out via
  `postMessage` to the parent, which does the authenticated POST.
- **Why teach it this way:** "always sandbox" is cargo-cult; reasoning from the trust model is the
  transferable skill. Ties to the paper's Cloud Security material (R1.19).
- **Status:** author undecided on whether to build the multi-tenant hardening path in v1 — currently
  planned as an optional later chapter, with v1 single-tenant.

### Data flow to teach explicitly
```
Researcher ──► form/admin: paste jsPsych timeline code ──► DB (Study.code)

Participant browser  ──GET /study/<id>/?participant_id=…&condition=…──►  Django view
        │                                            wraps Study.code + jsPsych in sandboxed iframe
        │  ◄──────────── HTML page (iframe: study code) + participant/condition context ─┘
        │
   participant runs trials
        │
        └──POST /api/study/<id>/data  (JSON trial data)──►  Django API view ──► DB (Trial rows)
                                                                   │
Researcher ──► /admin  or  /study/<id>/export.csv  ◄───────────────┘
```

## 4. Chapter outline (living doc — order may shift)

| # | Chapter | Core content | Paper item(s) it supports |
|---|---------|--------------|---------------------------|
| 0 | Before you start | Links to official + Django Girls basics; `uv` env in ~5 lines; what this adds | R2.1 |
| 1 | The problem | Why host your own experiment? DataPipe/Pavlovia/JATOS vs bespoke; when each wins | R1.20, R1.21, §7 |
| 2 | How the web works | Address → HTTP request → server → response, traced through *this* app; why a backend | R3.3, R3.6, R3.7 |
| 3 | Project setup | `startproject`, an app, settings/urls wiring — tied to the study app | R2.1, R2.9 |
| 4 | Serving the experiment | Drop a jsPsych study into Django; static files; the study template view | R1.20 |
| 5 | Identifying participants | URL params (participant/condition/study id); passing context to the front-end | R1.7, R1.9 |
| 6 | Capturing the data | The API endpoint; POST JSON from jsPsych `on_finish`; CSRF; validation | R1.10, R2.5(api) |

> **Build order note:** although numbered 5 then 6, ch5 (participants) comes *before* ch6 (capture)
> in the build so there's participant/session context to attach data to when the endpoint lands.
> (Milestone mapping: ch5→M4, ch6→M3 — see §9b.)
| 7 | Modelling research data | Study/Participant/Session/Trial; ForeignKey vs ManyToMany; migrations; relational vs NoSQL note | R1.15–R1.17, R3.8 |
| 8 | Seeing & exporting data | Admin; CSV/JSON export; a simple researcher dashboard (HTMX optional) | R1.24, R3.11 |
| 9 | Testing it | Define unit tests; test the data-capture endpoint; why it matters for data integrity | R1.18, R3.6 |
| 10 | Secrets & services | django-environ; storing secrets properly; sending a reminder email (API example) | R1.19, R2.3 |
| 11 | Deploying | One concrete PaaS path, end to end; custom domain; link out for alternatives | R2.1, deployment |
| 12 | Going further (optional modules) | Counterbalancing/conditions, longitudinal/multi-session, Prolific completion codes, lab.js as an alternative front end, Huey for async (blessed; not Celery) | R2.6 (asides live here) |

### 4a. Length target & the core-spine / optional-modules split — DECIDED: ~3 h guided

"Length" hides three clocks; beginners get burned when authors quote the smallest. Be explicit:

| Clock | What it measures | Estimate |
|-------|------------------|----------|
| **Reading time** | Skimming the prose | ~45–60 min |
| **Guided build time** | Typing along, everything works first try | **~3 hours** ← headline |
| **Realistic wall-clock** | With typos, env issues, a CDN hiccup, one CSRF head-scratch | a weekend (6–10 h) |

Audience isn't zero (they write some Python, have a jsPsych study), so we skip the "what is a
variable" tax; but most are new to Django/backends/deploy, so realistic ≈ 2.5–3× guided.

**Advertise "~3 hours to a working, deployed data-collector" (= guided build time),** and say in the
intro that a first pass over a weekend is normal. That number is credible and competitive — Django
Girls quietly eats a day; the official tutorial is 4–6 h and yields a *polls* app, not something a
researcher wants.

13 chapters ÷ 3 h ≈ 14 min/chapter is too tight for hands-on-with-debugging, so we split. This also
serves the deadline: the citable DOI must exist before paper resubmission (§7, 14-Jan-2027), so v1
must be *complete enough to cite*, not exhaustive — **ship the spine, add modules later.**

**Core spine (counted in the ~3 h; each is a working, tag-able M-milestone from §9b):**

| Ch | Milestone | Guided |
|----|-----------|--------|
| 0 | Before you start (env, `uv`, links out) | 10 min |
| 1–2 | Why a backend + how the web works (read, traced through *this* app) | 20 min |
| 3 | Project setup → **M1** Study model + admin | 25 min |
| 4 | Serve a seeded Flanker study → **M2** | 30 min |
| 5 | Identify participants (URL params) → **M4** | 20 min |
| 6 | Capture data (POST JSON, CSRF) → **M3** | 35 min |
| 7 | Model the data (FK/M2M, migrations) | 25 min |
| 8 | See & export (admin + CSV) → **M5** | 20 min |
| 11 | Deploy (one PaaS path) → **M7** | 25 min |
| | **Total** | **≈ 3 h 10 m** |

**Testing exception (keeps the paper honest):** the *chapter* (ch9) is optional, but the **single
data-capture endpoint test is written at M3**, alongside the capture code — cheap, and the paper
points readers at `study/tests.py` (R1.18, R2.9), so that file must exist even before ch9 ships. Ch9
is then just the *expansion* (what/why of unit tests, more cases), not the first test.

**Optional modules (NOT counted; "coming soon" stubs are acceptable for v1):** Testing (ch9, **M6** —
expands the M3 endpoint test),
Secrets & email (ch10), and all of ch12 (Prolific codes, counterbalancing, multi-session, lab.js,
Huey for async, multi-tenant sandboxing). This resolves the R2.6-vs-R3.13 "fewer asides / more depth" tension
structurally: the core stays lean; depth lives in clearly-labelled optional modules.

### 4b. Per-page anatomy — the 7-beat skeleton every core page follows

Each beat maps to a native MkDocs Material feature, so this is cheap to author consistently:

1. **"By the end of this page you'll have…"** — outcome first, with a screenshot/gif of the result
   (the running Flanker, the CSV file).
2. **Where we are** — the §3 data-flow diagram, *the same diagram every page*, with the current arrow
   highlighted. This recurring visual spine is the tutorial's strongest pedagogical asset.
3. **The concept** (short) — the mental-model bit; this is where each page links back to the paper.
4. **Do it** — steps using **code annotations** (numbered dots) for line-by-line, and **content tabs**
   for `models.py` / `views.py` / `urls.py`.
5. **Checkpoint** — "run this, you should see X" + the **`git tag`** for this milestone, so a stuck
   reader can `git checkout m4-…` and continue. This beat is what makes a 3-hour tutorial survivable
   across multiple sittings and stops a broken step dead-ending anyone.
6. **Why it worked** — a short reflection admonition.
7. **Troubleshooting** — a *collapsible* admonition of the 3–4 real errors (mixed-content HTTPS, CSRF
   403, forgotten migration). Owning the failure modes is where we earn trust over tutorials that
   pretend nothing breaks.

## 5. Tech decisions

### 5a. The tutorial's Django app
- **Django** — **6.0 (current stable) is the blessed development line** (Python 3.14); CI also proves
  5.2 LTS + `main`. *Must* be a supported version (the paper's demo used unsupported 4.2 — R2.n3 —
  don't repeat that mistake).
- **Python 3.14** (already set in `pyproject.toml`), **uv** for env/deps (matches R2's `uv` suggestion).
- **jsPsych** — pin a version; vendor the bundle into static files so the tutorial is reproducible
  and doesn't rot when a CDN changes.
- **DB** — SQLite for the tutorial (zero-config, honest for small studies); note the Postgres upgrade path.
- Keep third-party deps minimal: django-environ (secrets), maybe django-crispy-forms in an optional
  chapter, HTMX in an optional chapter.
- **Async task queue — blessed = Huey, not Celery.** When the optional async module lands (ch12), the
  one blessed path is **Huey** (author preference: far simpler to run — SQLite/Redis broker, no
  RabbitMQ, minimal ops), with Celery mentioned only as the heavier alternative to link out to. NB the
  paper's Table 1 lists `django-celery` because it's from the JetBrains *popularity* survey, not as an
  endorsement — no conflict.

### 5b. The site itself — DECIDED: MkDocs Material
- **Single ecosystem** — pip/uv-installable, same toolchain as the Django app; low maintenance for a
  solo maintainer.
- **Code annotations** (numbered dots on code lines that expand) — best-in-class for line-by-line
  tutorial walkthroughs; directly serves "explain the example properly" (R2.9, R1.11).
- **Versioning via `mike`** — version dropdown (v5.2 / v6.0), so the "keep in sync with Django
  versions" plan works (R1.2, R2.6).
- Built-in offline search, content tabs, admonitions, instant nav.
- **Live jsPsych demo** — done via a `<iframe>` to a real running demo page (works fine in Markdown;
  actually cleaner than inline, as it isolates the jsPsych runtime). This neutralises the only real
  advantage Docusaurus had.
- Docusaurus was considered; only wins on glossy marketing-site feel / inline React, neither needed
  for a tutorial.

### 5d. Continuous integration — "stays current" as a feature
Answers the reviewers' "resources go stale" concern (R1.2, R2.6) structurally:
- **GitHub Actions matrix** — run the example app's tests against Django **6.0 (current, blessed)**,
  5.2 LTS, and pre-release/`main` (early warning before a release lands).
- **Scheduled weekly cron run** — catches new Django releases / security patches without a push.
- **Dependabot** — auto-PRs dependency bumps.
- Docs published as 6.0 via `mike`; a "tested against 6.0 / 5.2 / main" badge is the credibility
  signal that distinguishes this from a tutorial that will rot.

### 5c. Publishing & archival
- Host the **living** site on GitHub Pages.
- Mint a **citable DOI** per release via GitHub→Zenodo (or deposit on OSF). The paper cites the DOI
  as supplementary material (permanence for the editor); the DOI page links to the living site.
- **Licences:** MIT for the example code, CC-BY for the prose.
- Keep it **educational-first**; at most a modest author/contact footer. No services framing in the
  body, and keep consultancy off the paper entirely (avoids competing-interest disclosure issues).

## 6. Repo layout (proposed)

```
DjangoScienceTutorial/
├── ideation/            # this plan and scoping notes
├── <app>/               # the Django project the tutorial builds (the "answer key"); name TBD
│   ├── config/          # settings, urls, asgi/wsgi
│   ├── study/           # app: models, views, api, templates, static (jsPsych), tests
│   └── manage.py
├── docs/                # MkDocs Material source (mkdocs.yml at root)
├── mkdocs.yml
├── pyproject.toml       # uv-managed
└── README.md
```
Chapters in `site/` reference real, tagged commits/branches of `studyhost/` so code snippets always
match a working state (addresses R2.9 "uncommented, no application logic" and R1.1 "reference the repo").

## 7. Relationship to the paper

- Paper stays mental-model altitude; adds **one short "research requirement → MVT design" worked
  example** so it still stands alone (agreed essential).
- Paper references this companion throughout (R1.1) and cites its DOI as supplementary material.
- The **live DOI needs to exist before paper resubmission** — "we plan to" is far weaker to reviewers
  than a working, citable artifact. Deadline 14-Jan-2027 gives runway, but sequence accordingly.

## 8. Decisions log & open questions

**Decided:**
- ☑ **Site generator:** MkDocs Material (single ecosystem, code annotations, `mike` versioning;
  live demos via iframe). See §5b.
- ☑ **Django version:** **6.0 (current stable) + Python 3.14** as the blessed/published line
  (author decision, 2026-07; keeps the existing `pyproject.toml` pin), with a CI matrix also testing
  5.2 LTS + `main`. See §5d. NB the paper's own demo should track the same to avoid another R2.n3.
- ☑ **Study authoring:** v1 = paste jsPsych timeline into `Study.code`; media assets hosted
  externally by the researcher (HTTPS, CORS caveats); rendered in a sandboxed iframe. See §3.
- ☑ **Seed data:** ship a couple of classic paradigms (Flanker + Stroop) pre-loaded so the demo
  works immediately, alongside the "add your own" form.
- ☑ **Length & scope:** headline **~3 h guided build time** to a working, deployed data-collector;
  a **core spine** (ch 0–8 + 11) is counted, everything else (testing, secrets/email, ch12) is an
  **optional module** that may ship as a "coming soon" stub in v1. Per-page **7-beat skeleton** with
  a `git tag` checkpoint on every page. See §4a / §4b.

**Decided (cont.):**
- ☑ **Naming.** Descriptive tutorial/site title = **"Django for Behavioural Science"** (trademark-safe:
  DSF policy allows descriptive use, is cautious about "Django" *inside* a brand — esp.
  commercial/consultancy). App itself gets a short non-Django name — *shortlist still open*:
  StudyHost, StudyForge, Cohort, Panelry, Benchtop/OpenBench.

**Open:**
1. **App name** — pick from the shortlist above (title is settled; app name is not blocking).
2. **Prolific integration** — a completion-code chapter now, or later? (High researcher value.)
3. **lab.js as a second front-end** (R1.20 names it) — include in v1 or defer? Leaning defer;
   jsPsych only for v1.
4. **Chapter 12 asides** — how much to build now vs stub as "coming soon" (scope control).
5. **Which classic paradigms to seed** — Flanker + Stroop assumed; confirm.

---

## 9. Build guide — getting started & how to iterate

This repo is a fresh uv project (`pyproject.toml`, Python 3.14, git initialised, no commits yet).
The Django app is the "answer key"; the `docs/` site is written alongside it.

> **✅ Version RESOLVED (2026-07): Python 3.14 + Django 6.0 is the blessed line.** Django 6.0 targets
> Python 3.12–3.14, so the existing `pyproject.toml` `requires-python >=3.14` pin stands. CI (§5d)
> also proves 5.2 LTS + `main` for back-compat/early-warning.

### 9a. Bootstrap the Django project
```bash
# from repo root: /Users/andytwoods/PycharmProjects/DjangoScienceTutorial
uv add "django>=6.0,<6.1"        # blessed line (Python 3.14) — see version note above
uv add django-environ            # secrets/config
uv run django-admin startproject config .     # project = "config", manage.py at root
uv run python manage.py startapp study        # the study/data-capture app
uv run python manage.py migrate
uv run python manage.py runserver             # sanity check: http://127.0.0.1:8000
```

> **DECIDED — the answer-key app stays plain `startproject`, NOT cookiecutter-django.** The app the
> tutorial narrates is a *teaching object*; minimalism is load-bearing. A cookiecutter-django project
> (~50 files, split settings, Docker, allauth, CI, ~40 pre-made decisions) is unreadable to a beginner
> and would bury every snippet the docs point at — the exact "no application logic / can't map it"
> complaint (R2.9) and the opposite of R2.1's ask for *more* setup hand-holding. It also kills the ch2
> "trace a request through *this* app" spine. **cookiecutter-django is instead *named and handed off
> to*:** mention it in ch3 ("what real projects use; we build by hand so you understand what it
> generates") and hand off to the phase-2 science preset in ch11/12 ("now you know the pieces — here's
> how to start a real study in two minutes"). Learn by hand → ship with the preset. See §10.

### 9b. Suggested build order (milestones — each is a working, tag-able state)
Tag each milestone (`git tag m1-…`) so the docs can point snippets at a known-good commit (R2.9, R1.1).

- **M1 — Study model + admin.** `Study{ name, slug, code (TextField), created }`; register in admin;
  add via admin. *Teaches: models, migrations, admin.*
- **M2 — Serve a study.** `GET /study/<slug>/` view + template that injects `Study.code` and loads a
  pinned jsPsych bundle from static files. Seed Flanker + Stroop via a data migration or fixture.
  *Teaches: urls, views, templates, static files.*
- **M3 — Capture data.** `Participant`, `Session`, `Trial` models; `POST /api/study/<slug>/data`
  view that ingests jsPsych JSON; wire jsPsych `on_finish` to fetch()-POST it (CSRF handled).
  **Write the one endpoint test here** (`study/tests.py`) — the paper cites this file (R1.18, R2.9),
  so it must exist from M3 even though the *testing chapter* (ch9/M6) is optional. *Teaches: the API
  endpoint, CSRF, JSON, FK relationships.*
- **M4 — Identify participants.** Read `participant_id` / `condition` / `study_id` from URL params;
  pass into the template/context; store against the Session. *Teaches: R1.7 URL params.*
- **M5 — See & export.** CSV/JSON export view; optional simple researcher dashboard (HTMX optional).
  *Teaches: querysets, data export.*
- **M6 — Tests.** *Expands* the M3 endpoint test: unit tests for the model, more endpoint cases, and
  the what/why of unit tests (the tests the docs cite). *Teaches: R1.18 testing.*
- **M7 — Deploy.** One PaaS path end-to-end; env vars/secrets via django-environ. *Teaches: deployment.*
- **Later:** external-asset guidance (HTTPS/CORS), multi-tenant hardening (sandbox/separate origin),
  Prolific completion codes, bundle upload, lab.js.

### 9c. Bootstrap the docs site (MkDocs Material)
```bash
uv add mkdocs-material mike
uv run mkdocs new .                 # creates mkdocs.yml + docs/
# edit mkdocs.yml: theme: name: material; enable code annotations, content tabs, admonitions
uv run mkdocs serve                 # live preview at http://127.0.0.1:8000
# versioned publish later:  uv run mike deploy --push 5.2 latest
```
Note: both `runserver` and `mkdocs serve` default to port 8000 — run one on `:8001` when previewing
together (`uv run python manage.py runserver 8001`).

### 9d. CI (add once M1–M3 exist)
`.github/workflows/ci.yml`: matrix over Django {5.2, 6.0, main} × Python {3.13, 3.14}; run
`manage.py test`; a weekly `schedule:` cron; Dependabot config for pip/uv. Green badge = "maintained"
(the R1.2/R2.6 answer). Publish docs via `mike` on push to `main`.

**Snippet-rot is killed structurally, not by CI vigilance:** docs never copy-paste code — they
*transclude* it from the answer-key app with `pymdownx.snippets` (`--8<-- "study/models.py:marker"`),
and `mkdocs build --strict` in CI fails if an include path/marker goes missing. So the code CI runs
*is* the code the docs show; they can't drift. Same trick for behaviour claims — transclude the
passing test that proves the claim.

### 9e. Keeping current — DECIDED: automated tests, MANUAL figure refresh
The four rot-prone artifact types get different treatment (see design discussion): **code snippets**
(transcluded, §9d), **command output** (captured by the refresh script below), **screenshots**
(manual refresh), **diagrams** (authored in **Mermaid** = text, release-immune — no regeneration).

- **Tests: automated.** The §9d matrix + weekly cron prove the code still works on each Django line.
- **Figures/screenshots: manual, on each Django release.** Full auto-regenerate-and-PR infra isn't
  worth the maintenance for a solo author. Instead:
  - **Trigger = the Dependabot Django bump PR.** When Django releases, Dependabot opens a PR
    automatically — that PR *is* the reminder (and its CI run flags any test breakage). No extra cron
    or release-watcher needed; piggyback the ping you already get.
  - **One-command runbook** (`make refresh` / a script) so each run is identical: migrate + seed
    Flanker/Stroop → boot the app → **Playwright** captures the documented pages → PNGs land in
    `docs/assets/`. Author eyeballs the visual diff, edits any prose/caption a UI change affected,
    commits. Keep the Playwright script even though the trigger is manual — it's what makes runs
    consistent. (Screenshots are captured against the *blessed* Django version; when the blessed
    version bumps, `mike` mints a new docs version and older versions keep their old-but-correct PNGs.)
  - **jsPsych/Bulma bumps** drive most screenshot rot (more than Django itself) — same refresh script,
    triggered by their Dependabot PRs.

### 9f. First iteration target for the author
Get to **M2** (a seeded Flanker study actually running in the browser, served by Django). That's the
smallest thing that feels real and is worth demoing — and it de-risks the jsPsych-in-Django mechanics
before investing in the data pipeline.

---

## 10. Productization (phase 2 — POST-v1, do not start before M2)

A "start a real study fast" path for readers who've finished the tutorial. **Two distinct artifacts —
keep them separate; do not collapse one into the other:**

| Artifact | Scaffold | Audience | Framing |
|----------|----------|----------|---------|
| Tutorial answer-key app (§6, §9) | plain `startproject`, minimal | learners | narrated, hand-built |
| Science preset + pip-app (this §) | **on top of cookiecutter-django, auto-answered** | shippers | packaged |

Same underlying `study/` code — narrated-minimal for learners, extracted-and-packaged for shippers.

### 10a. "Build on top + auto-answer" — the chosen approach (NOT a fork)
Don't fork cookiecutter-django (perpetual-rebase trap, and it forfeits the maintenance we want to
inherit). Instead drive it with pre-supplied answers — a first-class cookiecutter feature:
```bash
cookiecutter gh:cookiecutter/cookiecutter-django \
  --no-input --config-file science.yaml  project_name="MyStudy"
```
`science.yaml` holds a `default_context:` mapping cookiecutter-django's ~40 prompts to the house
answers, so the researcher is asked ~6–8 things they actually care about (project name, author/email,
deploy target, Postgres-or-SQLite, seed paradigms, Prolific y/n, researcher-accounts y/n) instead of 40.
**Inheriting upstream's Docker / CI / security / Django-version currency is the whole point** — it's the
structural answer to "resources go stale" (R1.2, R2.6).

### 10b. Two buckets — auto-answer only covers what cookiecutter-django *asks*
- **Bucket A (auto-answerable):** `username_type=email`, `mail_service=Brevo`, `use_celery=n`,
  `use_sentry=n`, `ci_tool=GitHub`, `use_whitenoise=y`, `cloud_provider=None`, Postgres version → one
  line each in `science.yaml`.
- **Bucket B (NOT a prompt → post-gen overlay):** **Huey** (upstream only offers Celery), **Rollbar**
  (only offers Sentry), **Bulma + crispy-bulma + htmx + SweetAlert2** (not in `frontend_pipeline`), and
  the **research harness** (Study/Participant/Session/Trial, vendored jsPsych, CSV export, seeded
  Flanker/Stroop). This is where the value *and* the maintenance live.

### 10c. Ship Bucket B as a versioned pip-app, not a settings-patcher
A script that string-edits the generated `settings/base.py` is brittle (upstream restructures settings
between releases → silent breakage). Instead put the harness in a **pip-installable app**
(`uv add django-<appname>`); the overlay then shrinks to: add to `LOCAL_APPS`, `include()` its urls,
run its migration, add Huey. **A versioned package is *updatable*** (security fixes reach existing
users; generated-and-forgotten cookiecutter code never does) — answering "release the code" (R2.8) and
"real logic + tests" (R2.9) at the same time.

### 10d. Caveats
- **Coupling:** building on top couples us to cookiecutter-django's prompt *names* + file layout. Pin
  the version we target, bump deliberately, keep logic in the pip-app not in settings-patching, and
  extend the §9d CI to run *generate → overlay → `manage.py test`* on the weekly cron so an upstream
  change is a red badge, not silent rot.
- **Naming:** DSF is cautious about "Django" inside a brand (§8) → `cookiecutter-behavioural-science`
  or a neutral app name (StudyHost/StudyForge/Cohort/…), not "cookiecutter-django-science".
- **Sequencing:** phase 2. The paper resubmission (§7, 14-Jan-2027) needs the *tutorial + DOI*, not the
  template. The `study/` app must reach M1–M7 first — you can't package a harness you haven't built.
