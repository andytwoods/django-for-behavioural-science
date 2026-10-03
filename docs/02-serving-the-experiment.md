# 2 · Serving the experiment

<span class="time-pill">About 45 minutes</span>

<figure class="apparatus" markdown>
![A Holmes stereoscope, 1861](assets/img/gear/ch3-tachistoscope.jpg)
<figcaption markdown="span">
A [stereoscope](https://en.wikipedia.org/wiki/Stereoscope) presented a prepared image to the viewer.
<br>Image: [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Holmes_Stereoscope_1861.png), CC0.
</figcaption>
</figure>


**By the end of this chapter** a real jsPsych study will run in the browser, served by
your Django app. [Here's a live demo](demo/flanker/index.html){ target="_blank" }.

<figure markdown="span">
  ![The Flanker instructions screen](assets/img/flanker-instructions.png){ width="520" }
  <figcaption markdown="span">The Flanker task you'll add later in this chapter, served from /study/flanker/. [Try it](demo/flanker/index.html){ target="_blank" }.</figcaption>
</figure>

## The plan

We need: 

1. a directory to hold jsPsych
2. a view that is called when someone visits your URL suffixed with `/study/<slug>/`
3. a template that combines the researcher's timeline code with jsPsych to run your study

## Keep jsPsych local

Download the
[jsPsych library files](https://www.jspsych.org/latest/tutorials/hello-world/#option-2-download-and-host-jspsych)
(the `jspsych.zip` attached to a release). Create the folders `study/static/study/jspsych/`, then copy everything from the zip's `dist/` folder into it. You don't need anything else from the zip.

??? warning "Why `study/static/study/` and not just `study/static/`?"
    That doubled-up folder name looks like a mistake, but it isn't! Django searches every app's static directory and uses
    the **first** filename-matching file it finds in a specific subfolder. The same rule applies when
    `collectstatic` gathers files for deployment: it copies the first match and ignores
    later files with the same path. If two apps both shipped
    `jspsych.js` directly in their `static/` folder, Django could not distinguish between
    them, and which file won would depend on the order in which its static-file finders
    searched those locations.

    Putting the files inside a second folder named after the app gives every file a unique
    path (`study/jspsych/jspsych.js`), so there's nothing to collide. Django's own
    tutorial explains this under
    ["Static file namespacing"](https://docs.djangoproject.com/en/6.1/intro/tutorial06/#customize-your-app-s-look-and-feel).

They end up here:

```text
study/
└── static/
    └── study/
        └── jspsych/
            ├── jspsych.css                       the look of the trials
            ├── jspsych.js                        the core library
            ├── survey.min.css                    styles for the survey plugin
            ├── plugin-animation.js               one file per trial type…
            ├── plugin-audio-button-response.js
            ├── …                                 (42 or 53 of them)
            └── plugin-visual-search-circle.js
```

jsPsych loads each **[trial type](https://www.jspsych.org/v8/overview/plugins/) from its own plugin file**. A timeline can only
use the trial types whose plugin files the page has loaded.

That's easy in a standalone experiment, where you know your own trial types and add a
`<script>` for each. A platform though needs to take into account that a future study may require any of the plugins...

So we add all of them, and (for the time being) we load all of them for each study (there's a note below though on how to build a system to only load in modules that are needed for a given study). You copied every `plugin-*.js` along with the rest of `dist/`, so there's nothing more to do here.

??? tip "Getting all 53 files"
    This tutorial was built with jsPsych 8.2.3. The
    [8.2.3 zip](https://github.com/jspsych/jsPsych/releases/tag/jspsych%408.2.3) holds the
    core library plus 42 of the plugins. The other 11 (`survey-text`, the `video-*` set,
    `virtual-chinrest`, `visual-search-circle` and the `webgazer-*` set) are published
    only as [separate packages](https://www.jspsych.org/v8/plugins/list-of-plugins/).
    The newer [8.3.0 zip](https://github.com/jspsych/jsPsych/releases/tag/jspsych%408.3.0)
    includes all 53. Either is enough for this tutorial.

    The sizes on this page are for the minified files this app ships. The zip's files are
    unminified and roughly twice as big, but the proportions hold.

    One exception is worth knowing about. At **1.3 MB**, `plugin-survey.js` is almost five
    times larger than all the other plugins combined (269 KB) because it includes the
    complete [SurveyJS library](https://surveyjs.io/form-library/documentation/overview).
    Our load-everything approach means every participant
    downloads it, even when a study does not use surveys. That is the trade-off for avoiding
    per-study plugin lists.

## The view

Open `study/views.py`.

Add the imports below, replacing the existing `render` import. You'll add more imports as you work through the chapters.

You'll create `study/jspsych.py` at the end of this chapter. Until then, Django will report `ModuleNotFoundError: No module named 'study.jspsych'`. That's expected for now.

```python
from django.shortcuts import render, get_object_or_404

from .jspsych import plugin_files
from .models import Study
```


Then add a view that looks up the study by its slug and sends the study (and other information) to a template:

```python
--8<-- "study/views.py:study-detail-view"
```

Don't worry about the `participant_id` and `condition` lines yet as we cover that later. For now
the important part is the last line where we find the study and render a template with it.

Next, we need to **create
`study/urls.py`** and add the below to it:

<!-- source: study/urls.py -->
```python
from django.urls import path

from . import views

app_name = "study"

urlpatterns = [
    path("study/<slug:slug>/", views.study_detail, name="detail"),
]
```
Above, see `<slug:slug>`; that's a placeholder. A request for `/study/flanker/` sets
`slug` to `"flanker"`, and this is sent to the view in the `slug` parameter.

One easy thing to miss is that the project doesn't know your app's `urls.py` exists until you
include it. In `config/urls.py`, add the `include` (and import it). The whole file should now read:

<!-- source: config/urls.py -->
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("study.urls")),   # hand every non-admin URL to the study app
]
```


`config/urls.py` is the entry to your app. Django checks every incoming URL against the patterns defined in there first. The admin pattern handles `/admin/`, while `include()` passes the
URLs reaching that point to `study/urls.py` for a more specific match. In this fashion, app-specific
routes are stored within that app's own `urls.py` file.

```text
     a participant asks for /study/flanker/
                        │
                        ▼
   ┌─────────────────────────────────────────┐
   │ config/urls.py            THE FRONT DOOR│
   ├─────────────────────────────────────────┤
   │ path("admin/", admin.site.urls)         │
   │ path("", include("study.urls"))         │
   └─────────────────────────────────────────┘
                        │
    nothing matches /admin/, so the catch-all
     include hands the URL to the study app
                        │
                        ▼
   ┌─────────────────────────────────────────┐
   │ study/urls.py         THE APP'S OWN MAP │
   ├─────────────────────────────────────────┤
   │ path("study/<slug:slug>/", study_detail)│
   └─────────────────────────────────────────┘
                        │
             match! slug = "flanker"
                        │
                        ▼
   views.study_detail(request, slug="flanker")
```

Django tries the patterns in order and stops at the first match.

## The template

The view above renders `study/study_detail.html`. Let's make that now.
Templates live in a `templates/` folder inside the app. **Create
`study/templates/study/study_detail.html`** and add the below.


<!-- source: study/templates/study/study_detail.html -->
```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{{ study.name }}</title>
    <link rel="stylesheet" href="{% static 'study/jspsych/jspsych.css' %}">
    <link rel="stylesheet" href="{% static 'study/jspsych/survey.min.css' %}">
    <script src="{% static 'study/jspsych/jspsych.js' %}"></script>
    {% for plugin in jspsych_plugins %}<script src="{% static 'study/jspsych/'|add:plugin %}"></script>
    {% endfor %}
</head>
<body>
<script>
    // chapters 3 and 4 add their lines here, above initJsPsych

    const jsPsych = jsPsychModule.initJsPsych({ /* ...on_finish, chapter 4... */ });
    let timeline = [];

    {{ study.code|safe }}   {# the researcher's pasted timeline goes here #}

    jsPsych.run(timeline);
</script>
</body>
</html>
```

The first line, `{% load static %}`, lets you use `{% static %}` to turn a file path into
the URL the file is served from. Leave it out and you'll get this error: `Invalid block tag ... 'static'`.
Add it to every template that uses `{% static %}`, as it isn't inherited.


In a nutshell, the platform loads `jsPsych`. You, the researcher, then provide the code that fills a space for the jsPsych timeline, replacing `{{ study.code|safe }}` shown above.

### Which plugins to load

In this tutorial we load all the `jspsych_plugins` so they are available for whatever study
the researcher has designed. To achieve this, the app reads the plugin folder and hands the
template every file it finds. **Create `study/jspsych.py`**:
    
```python
--8<-- "study/jspsych.py:plugin-files"
```

??? tip "Could we load only the plugins each study uses?"
    Absolutely. Give `Study` a `plugins` field (a
    `JSONField` holding a list of filenames), show the files as a tick-list on
    the admin form, and load only the files that are ticked. An empty
    selection would mean "load everything", so a half-drafted study still runs.

    Via this method, a study page currently carries about **2.4 MB**: the 53 plugins
    (1.6 MB, of which `plugin-survey.js` alone is 1.3 MB), the core library (77 KB) and the
    two stylesheets (770 KB). The seeded Flanker task uses exactly one trial type, so
    picking plugins would serve it in **544 KB**, a saving of roughly **1.9 MB**.

    Why not build that here? It would add about 70 lines across the model, a custom admin
    form, a helper, and a migration. More importantly, researchers would have to
    select the right plugins for their study, and if they miss one out, the experiment fails to run.

    Note that if you never use surveys, you can just remove
    `plugin-survey.js` and `survey.min.css` from `study/static/study/jspsych/`, reducing page load from 2.4 MB to **810 KB**.

## Add some studies

Start the server:

```bash
uv run python manage.py runserver
```

Open [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/), log in with the superuser you made in chapter 1, and
click **Studies → Add study**. Fill in three fields:

- Name: `Flanker task`
- Slug: this fills itself in from the name as `flanker-task`. Change it to just `flanker`, so the address (`/study/flanker/`) matches the links in this tutorial
- Code: paste one of the timelines below

<figure markdown="span">
  ![The Add study form in the Django admin, with Name, Slug and Code filled in](assets/img/admin-study-add.png){ width="620" }
  <figcaption markdown="span">Adding the Flanker task. The slug fills itself in from the
  name, and `code` takes the timeline as-is.</figcaption>
</figure>


Save it, and the study is live at `http://127.0.0.1:8000/study/flanker/`.

??? example "Flanker task: `study/seed_studies/flanker.js`"
    Respond to the centre arrow while the flanking arrows agree (`<<<<<`) or disagree
    (`>><>>`) with it. Uses one plugin, `html-keyboard-response`.

    ```javascript
    --8<-- "study/seed_studies/flanker.js"
    ```

??? example "Stroop task: `study/seed_studies/stroop.js`"
    Name the ink colour of a colour word, where word and ink match or clash. Also one
    plugin, `html-keyboard-response`.

    ```javascript
    --8<-- "study/seed_studies/stroop.js"
    ```
??? note "I've found a jsPsych study on the web. What code do I copy from it to get it to work here?"
    Just the JavaScript that builds your trials, not a whole HTML page. The platform
    already calls `initJsPsych()` and `jsPsych.run(timeline)` for you, so your code should
    push its trials onto the `timeline` that's already there and leave the setup alone.

    A standalone experiment that starts like this:

    ```javascript
    const jsPsych = initJsPsych();
    const timeline = [instructions, trial];
    jsPsych.run(timeline);
    ```

    becomes just this when pasted in:

    ```javascript
    timeline.push(instructions, trial);
    ```



Open `http://127.0.0.1:8000/study/flanker/`. You should get the instructions screen from
the top of this chapter; press a key and the trials begin. That's your Django backend
serving a live jsPsych experiment.

The study now runs, but we don't yet know *who* is doing the study. That's what we explore next.
