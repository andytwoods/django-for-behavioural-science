# Django for Behavioural Science

A research-focused companion tutorial (and its "answer-key" app) showing how to host a
**jsPsych** experiment on your own **Django** backend and capture the data, the way
DataPipe / Pavlovia / JATOS do, but bespoke and under your own control.

## What the app does

A small study-hosting platform: a researcher adds a study (a pasted jsPsych timeline),
the platform wraps it with the data-capture plumbing, serves it to participants, stores
every trial in a relational schema, and lets the researcher view and export the data.

> The platform provides the data-capture plumbing; the researcher provides only the
> experiment logic.

## Quick start

```bash
uv sync
uv run python manage.py migrate     # applies schema + seeds Flanker & Stroop
uv run python manage.py runserver
```

Then visit:

- `/`: the studies index
- `/study/flanker/?participant_id=demo`: run the seeded Flanker task
- `/study/flanker/dashboard/`: the researcher dashboard (view + export data)
- `/admin/`: the Django admin

Create an admin login with `uv run python manage.py createsuperuser`.

## Make targets

```bash
make test      # run the test suite
make serve     # run the dev server
make refresh   # regenerate the tutorial screenshots (Playwright)
```

## Building blocks

- **Python 3.14 · Django 6.1** (blessed line; CI also tests Django `main`). Managed with
  [uv](https://docs.astral.sh/uv/).
- **jsPsych 8.2.3** vendored into `study/static/` (pinned; no CDN dependency).
- **SQLite** for local development.
- Docs site built with **MkDocs Material**; code snippets are transcluded from this app
  so they cannot drift from the tested source.

## Repository layout

```
config/            # Django project (settings, urls, asgi/wsgi)
study/             # the app: models, views, api, templates, static (jsPsych), tests
docs/              # MkDocs tutorial source
scripts/           # screenshots.py, the figure-refresh runbook
```

## Licence

Example code under [MIT](LICENSE); the tutorial prose in `docs/` under
[CC BY 4.0](LICENSE-DOCS). Third-party images and the vendored jsPsych keep their
own licences, listed in `LICENSE-DOCS`.
