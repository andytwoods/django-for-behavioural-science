# Deploying: getting your study online

By the end of this chapter the app will be running on the public internet, and capable of collecting real data.

There are many ways to host Django. This chapter outlines one approach I have been using
recently: I rent a small cloud server from [Hetzner](https://www.hetzner.com/cloud/) and
use [Appliku](https://appliku.com/) to install and manage (currently 15) applications.
I developed a [Copier template](https://github.com/andytwoods/django-appliku-copier) to
prepare each app automatically for deployment through Appliku with a
[PostgreSQL](https://www.postgresql.org/) database.

For a modest Django deployment, Hetzner's **CX33** is a good starting point: 4 shared
vCPUs, 8 GB of RAM, and 80 GB of storage leave room for the app, Postgres, and several
other small projects. As of August 2026 it costs €8.49 per month before VAT, plus €0.50
for an IPv4 address — about €10.79 with 20% VAT (see [Hetzner's current pricing](https://www.hetzner.com/cloud/)).

!!! info "Why Appliku?"
    Appliku's Hobby plan currently costs
    [$10 per month](https://docs.appliku.com/docs/team-management/billing). Alternatives
    include [Coolify](https://coolify.io/pricing), which is free when self-hosted and also
    offers a managed cloud service. I prefer Appliku because I find it easier to use and it takes more work off my hands.

## Requirements of production

- A real web server. `runserver` is for development only. In production
  [gunicorn](https://gunicorn.org/) is a popular option
- A real database. In production we typically use Postgres
- Static files served properly. `runserver` hands them out one by one, and only
  while `DEBUG` is on, so in production something else has to do it
- [WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html), which does
  exactly that from inside Django, once `collectstatic` has gathered the files into
  one folder for it

The Python packages for all of this — gunicorn, `psycopg` and WhiteNoise — are already
declared in
[`pyproject.toml`](https://github.com/andytwoods/django-for-behavioural-science/blob/main/pyproject.toml),
and the WhiteNoise wiring is already in `config/settings.py`. Copier won't add them for
you, so it is worth knowing they are there. The database itself comes from Appliku.

## Before you start

Push the project to GitHub or GitLab, create an [Appliku](https://www.appliku.com/)
account, and connect that account to your Git provider under **Settings → Git
Integrations**.

The Django Appliku Copier tools used below are currently alpha software. Review the files
Copier generates before committing them, and do not use `appliku-setup` for irreplaceable
data without a tested backup plan.

## 1. Generate the deployment files

Install [Copier](https://copier.readthedocs.io/) once:

```bash
uv tool install copier
```

From the root of this project, run my
[Django Appliku Copier](https://github.com/andytwoods/django-appliku-copier):

```bash
copier copy gh:andytwoods/django-appliku-copier . --trust
```

Copier asks a short series of questions. For this tutorial, use `config` as the project
slug, `config.settings` as the settings module, `DJANGO_SECRET_KEY` as the secret-key
variable, Python 3.14, uv, gunicorn, and Postgres. Say yes to WhiteNoise manifest storage;
the project enables it when debug mode is off. The defaults of no task runner, no media
storage, console email, and no Sentry are sufficient for this app.

The command generates the deployment plumbing around the Django code you have already
written:

- `Dockerfile` builds a Python image, installs the locked dependencies, and runs
  `collectstatic`
- `run.sh` starts gunicorn when the web container runs
- `release.sh` checks Django's configuration and applies migrations before a release. It
  can also create the first superuser if you supplied an email
- `appliku.yml` describes the web and release processes, Postgres database, and
  environment variables Appliku should provide

The generated build uses dummy values only while `collectstatic` imports the settings.
They are not production secrets. Review the four files, then commit and push them:

```bash
git add Dockerfile run.sh release.sh appliku.yml .copier-answers.yml
git commit -m "Add Appliku deployment files"
git push
```

!!! note "Why `--trust`?"
    Copier templates can run tasks on your computer. `--trust` permits this template to
    adjust the generated WhiteNoise build command. Only use that option with a template
    whose source you trust.

## 2. Provision Appliku and deploy

Run the companion setup command from the same project directory:

```bash
uvx --from git+https://github.com/andytwoods/django-appliku-copier.git appliku-setup
```

The first run asks for an Appliku API key, available under **Appliku → Account → API
Keys**. It stores the key in the gitignored `.env.appliku` file. The `appliku-setup`
command then:

1. connects this Git repository to a new or existing Appliku app
2. provisions Postgres and supplies its `DATABASE_URL`
3. generates and uploads a production secret key
4. discovers the initial domain and configures the allowed host name
5. triggers the first deployment and waits for it to finish

Before recruiting anyone, open the app's **Config Vars** in Appliku and add:

```text
DJANGO_DEBUG=False
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-appliku-domain
```

Use the exact `https://` domain Appliku assigned, without a trailing slash, then redeploy.
The host now builds the Docker image, runs `release.sh` to migrate the database, and starts
gunicorn through `run.sh`.

!!! danger "Never deploy with the tutorial's secret key"
    The `SECRET_KEY` default in `config/settings.py` is committed to this repository, so
    it is public. The `appliku-setup` command generates a fresh `DJANGO_SECRET_KEY`
    automatically. Check that it appears in Appliku's **Config Vars** before going live.
    If you configure
    another host manually, generate one yourself:

    ```bash
    python -c "import secrets; print(secrets.token_urlsafe(64))"
    ```

## A custom domain

Appliku provides a domain, but if you want something snazzier you can buy your own (I
find [Porkbun](https://porkbun.com/) good value) and point it at your server with an
**A record**, which sends a name straight to an IP address. Once you've done that you
need to *then* tell Appliku, so it can issue an SSL certificate. The same domain, with
`https://` on the front, needs adding to `DJANGO_CSRF_TRUSTED_ORIGINS`. You then redeploy.

In Appliku that lives under the app's **Domains** tab. It's a two-way handshake between
the host and your domain registrar, and the order matters:

1. Appliku gives you an IP. A line reading "A-Record must point to ..." is your
   server's address. That's what a custom domain has to resolve to.
2. You add the A record at your registrar. Wherever you bought the domain (Porkbun,
   Namecheap, Cloudflare and so on), create an **A record** for the name: `@` for the
   bare domain, and a second for `www`, each pointing at that IP. This is the one step
   Appliku can't do for you, because it doesn't control your domain. Only your registrar
   does.
3. You tell Appliku the domain with **+ Add**. It waits until DNS actually resolves
   to its IP, then issues a free HTTPS certificate for it. A **Deployed** ✓ against each
   row is Appliku confirming both happened. Add the domain *before* DNS has propagated
   and the certificate step just fails, so do it in this order.

Two names, the bare domain and its `www` version, each need their own A record and their
own row here. Then update both settings under **Config Vars**: put the comma-separated
host names (without `https://`) in `DJANGO_ALLOWED_HOSTS`, and their full `https://` URLs
in `DJANGO_CSRF_TRUSTED_ORIGINS`. Redeploy for the changes to take effect.

## You're live

That's it! A researcher pastes a jsPsych study, a participant runs it, and every
submitted run lands in a Postgres database you control, on a server you own, which you
can browse and export at any time. No third-party experiment or data-capture platform
sits in the middle (your host, your DNS and any external media are still part of the
picture, but the study and its data are yours).

Where you take it next is up to you:
[several researchers per study](study-ownership.md), Prolific completion codes,
uploading media, counterbalancing. Have fun!
