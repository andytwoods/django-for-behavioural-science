# Django for Behavioural Science

A research-focused tutorial showing how to host a
**jsPsych** experiment on your own Django backend and save the data.

**Read the tutorial: <https://andytwoods.github.io/django-for-behavioural-science/>**

## What the app does

A small study-hosting platform. A researcher adds a study (jsPsych). The platform adds the data-capture ability, serves it to participants, stores data, and lets the researcher view and export the data.

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

- **Python 3.14 · Django 6.1** (CI also tests Django `main`). Managed with
  [uv](https://docs.astral.sh/uv/).
- **jsPsych 8.2.3** vendored into `study/static/` (pinned; no CDN dependency).
- **SQLite** for local development.
- Docs site built with **MkDocs Material** and published to
  [GitHub Pages](https://andytwoods.github.io/django-for-behavioural-science/) on every
  push to `main`; code snippets are gathered from this app so they cannot drift from
  the source.

## Repository layout

```
config/            # Django project (settings, urls, asgi/wsgi)
study/             # the app: models, views, api, templates, static (jsPsych), tests
docs/              # MkDocs tutorial source
scripts/           # screenshots.py, the figure-refresh runbook
```

## Licence

Example code under [MIT](LICENSE); the tutorial prose in `docs/` under
[CC BY 4.0](LICENSE-DOCS). Third-party images and jsPsych licences are listed in `LICENSE-DOCS`.
