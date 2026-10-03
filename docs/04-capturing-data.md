# 4a · Capturing the data

<span class="time-pill">About 45 minutes</span>

**By the end of this chapter**, when a participant finishes a study, their data will be stored and they will be thanked for completing the study.

<figure markdown="span">
  ![The dashboard showing collected sessions](assets/img/dashboard.png){ width="620" }
  <figcaption markdown="span">Where we're heading: data landing in the database, ready to browse and export. This is chapter 5's dashboard, shown with the optional styling from [Sharing page layout](advanced/base-template.md).</figcaption>
</figure>


```
participant finishes the study
        │
        └── POST /api/study/<slug>/data  (JSON) ──►  Django view ──► database (one StudyData row)
```

These are the steps we need to complete here:

- Server side: two models are set up to hold the data, and a view receives it
- Browser side: a few lines of code in the study's template send the data when the study ends

## The idea

<figure class="apparatus" markdown>
![Bluma Zeigarnik, photographed in 1921](assets/img/gear/ch5-zeigarnik.jpg)
<figcaption markdown="span">
[Bluma Zeigarnik](https://en.wikipedia.org/wiki/Bluma_Zeigarnik) in 1921, a few years before the [work](https://en.wikipedia.org/wiki/Zeigarnik_effect) that carries her name. She showed
that people remember an *interrupted* task better than a completed one. This was prompted, the
story goes, by waiters who could recall an unpaid order in detail and forgot it the moment
the bill was settled.
<br>Photo: Andrey Zeigarnik, public domain, via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Bluma_Zeigarnik,_April_3,_1921.jpg).
</figcaption>
</figure>

jsPsych collects data throughout the study and hands it all to Django at once when the
timeline ends, through its `on_finish` [callback](https://developer.mozilla.org/en-US/docs/Glossary/Callback_function). 

??? example "Two advanced points"

    - We send the data as
      [JSON](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/JSON)
      (a popular data format) in a `POST` request. `GET` is for asking; `POST` is for
      sending something to be stored
    - We leave Django's [CSRF protection](https://docs.djangoproject.com/en/6.1/ref/csrf/)
      switched on. [Cross-site request forgery](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/CSRF)
      is the trick where another website quietly makes *your* browser send a request to our
      server, riding on the fact that your browser attaches your cookies to it. The defence is
      a secret token that Django puts in the page and expects back with every `POST`: another
      site can make your browser send a request, but it can't read our page to find the token

## The models that store the data

We need two new models:
`Participant` (who did it) and `StudyData` (one participant's whole run, with every trial
in a single field). Add them at the bottom of `study/models.py`, below `Study` (`StudyData` refers to `Study`, so it has to come after it):

```python
--8<-- "study/models.py:capture-models"
```

Then create the database tables for them:

--8<-- "includes/migrate-reminder.md"

Don't worry too much about concepts such as [ForeignKeys](https://docs.djangoproject.com/en/6.1/ref/models/fields/#foreignkey), `on_delete`
rules and `JSONField`. What matters here is that a `StudyData` row belongs to one study and
one participant, and holds this person's data as JSON. Register them in the admin so you can
see the data land, adding to `study/admin.py` (the first line replaces your existing `from .models import Study`):


<!-- source: study/admin.py -->
```python
from .models import Participant, Study, StudyData

@admin.register(StudyData)
class StudyDataAdmin(admin.ModelAdmin):
    list_display = ["id", "study", "participant", "condition", "created"]
    list_filter = ["study", "condition"]
    readonly_fields = ["study", "participant", "condition", "data", "created"]  # captured data: show it, don't edit it

admin.site.register(Participant)
```


Both of these links are **one-to-many**: a study has many datasets, a participant has many
datasets, and each dataset belongs to exactly one of each. The other kind of link, **many-to-many**,
fits when a study has several owners and each of those researchers runs several
studies. [Study ownership](advanced/study-ownership.md) in the Going further
section adds a `Researcher` model and links it to `Study` this way.

## The endpoint

Here's the view that receives the data. It needs a few more imports, so first make the top of `study/views.py` read:


<!-- source: study/views.py -->
```python
import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .jspsych import plugin_files
from .models import Participant, Study, StudyData
```


Then add the view to `study/views.py`, below `study_detail`.

```python
--8<-- "study/views.py:submit-data-view"
```


`submit_data` hands the checking to `parse_submission`, which raises a `SubmissionError`
when the body isn't usable. Add both below `submit_data`:

```python
--8<-- "study/views.py:submission-parsing"
```

Everything in the body came from the open internet, so each field is checked for type
and size before any of it reaches the database.


Wire it into the app's URLs, adding this line inside the `urlpatterns` list in `study/urls.py`, below the `study/<slug:slug>/` path:

=== "study/urls.py"

    <!-- source: study/urls.py -->
    ```python
    path("api/study/<slug:slug>/data", views.submit_data, name="data"),
    ```

## Sending the data from jsPsych

In the front end, we tell jsPsych what to do when the study finishes: `on_finish` runs the `saveData` function, which posts the collected trials to the endpoint.


`saveData` needs to know two things the server has: the address to post to, and Django's
CSRF token. Add these two lines to `study/templates/study/study_detail.html`, next to the
`PARTICIPANT_ID` and `CONDITION` lines from chapter 3:

<!-- source: study/templates/study/study_detail.html -->
```javascript
const CSRF_TOKEN = "{{ csrf_token }}";
const DATA_URL = "{% url 'study:data' study.slug %}";
```

`{{ csrf_token }}` puts the secret token into the page (and sets the matching cookie), and
`{% url %}` builds the endpoint's address from its name, `study:data`, the same way
`reverse()` does in Python.

Then add `saveData` below them, and replace chapter 2's `initJsPsych` line with the one
at the bottom of this block:


<!-- source: study/templates/study/study_detail.html -->
```javascript
function saveData() {
    const message = html => document.body.innerHTML =
        "<div style='text-align:center;margin-top:3em;'>" + html + "</div>";

    message("<p>Saving your data, please don't close this window...</p>");
    return fetch(DATA_URL, {
        method: "POST",
        mode: "same-origin",                       // don't send the CSRF token off-origin
        headers: {"Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN},
        body: JSON.stringify({
            participant_id: PARTICIPANT_ID,
            condition: CONDITION,
            trials: jsPsych.data.get().values()
        })
    })
        .then(response => {
            if (!response.ok) throw new Error("HTTP " + response.status);  // 4xx/5xx isn't success
            return response.json();
        })
        .then(result => {
            message("<p>Thank you, your data has been saved.</p>");
        })
        .catch(() => {
            // keep the data in the page and let them retry rather than losing the run
            message("<p>Sorry, saving failed.</p>" +
                "<button onclick='saveData()'>Try again</button>");
        });
}

const jsPsych = jsPsychModule.initJsPsych({ on_finish: saveData });
```

`fetch` sends the request. The `.then` steps run later, once the
server's reply arrives, and `.catch` runs if anything along the way fails.

??? example "Following one submission through (optional, for the curious)"
    Here's one submission traced from start to finish. To keep
    it readable, imagine a cut-down Flanker run with just two trials, opened at
    `/study/flanker/?participant_id=p01&condition=A`.

    1. Browser. As each trial ends, jsPsych adds an object to its data store. After two trials,
       `jsPsych.data.get().values()` returns this (a real record has a few more fields, such as
       `stimulus` and `time_elapsed`):

        ```json
        [
          {"trial_type": "html-keyboard-response", "trial_index": 0, "rt": 412,
           "response": "f", "congruency": "congruent", "correct": true},
          {"trial_type": "html-keyboard-response", "trial_index": 1, "rt": 563,
           "response": "j", "congruency": "incongruent", "correct": false}
        ]
        ```

    2. Browser. The timeline ends, so `on_finish` calls `saveData`. The participant sees *"Saving your
       data, please don't close this window..."*. Then `saveData` packs three things into one
       data packet: the participant's ID (`PARTICIPANT_ID`) and their condition (`CONDITION`),
       which chapter 3 read from the study link, plus the list of trials:

        ```json
        {"participant_id": "p01", "condition": "A", "trials": [ ...the two objects above... ]}
        ```

    3. Browser. `fetch` POSTs that text to `/api/study/flanker/data`, with the CSRF token in its
       `X-CSRFToken` header
    4. Server. Django's CSRF check compares the token in the header with the CSRF cookie. If it's missing
       or wrong, the reply is `403 Forbidden` and your view never runs
    5. Server. The URL matches `api/study/<slug:slug>/data`, so Django calls
       `submit_data(request, slug="flanker")`. `@require_POST` lets a POST through, and
       `get_object_or_404` finds the Flanker study
    6. Server. `parse_submission` checks the body. It's valid JSON and an object; `"p01"` and `"A"` are
       short strings; `trials` is a list of two objects, well under the 10,000 limit. So it
       returns `("p01", "A", [...the two trials...])`. Had any check failed, it would raise
       `SubmissionError`, the reply would be `400 Bad Request` (for example
       `'trials' must be a list.`), and nothing would be saved
    7. Server. `Participant.objects.get_or_create(external_id="p01")` finds no `p01`, so it creates
       one. If `p01` comes back for a second run, the same line finds that existing row instead
    8. Server. `StudyData.objects.create(...)` adds one row to the database:

        | Field | Value |
        | --- | --- |
        | `id` | `1` |
        | `study` | Flanker task |
        | `participant` | p01 |
        | `condition` | `A` |
        | `data` | the list of two trial objects, exactly as they were sent |
        | `created` | when it was saved (in UTC) |

    9. Server. The view replies `200 OK` with the body `{"status": "ok", "id": 1}`
    10. Browser. `response.ok` is true, so the first `.then` reads the JSON reply and the second replaces
        the page with *"Thank you, your data has been saved."* Had the reply been a `400`, `403`
        or `500`, or had the network failed, `.catch` would show *"Sorry, saving failed."* and a
        **Try again** button instead

    So one run of the study is saved as one `StudyData` row. It doesn't matter whether the run
    had two trials or two hundred: they're all stored together, as a list, in that row's
    `data` field. Chapter 5's CSV export later splits them out into one row per trial.

!!! warning "What saving at the end can't do"
    Sending everything in one go when the study finishes keeps the code short. It also has
    limits you should know about before you run a real study:

    - The data is sent only when the experiment finishes
    - Closing or refreshing the page before the end loses this data
    - The Try again button depends on the page staying open. It resends the data still
      held in that page. If the participant closes the tab after *"saving failed"*, the run
      is gone
    - A retry can create a duplicate data entry. If the server saved the data but its reply was lost
      on the way back (the connection dropped at just the wrong moment, say), the page
      reports a failure. Pressing **Try again** then saves a second, identical `StudyData`
      row. When you analyse your data, check for repeated runs from the same participant

??? warning "Troubleshooting"
    **`403 Forbidden` when the data posts.** This is a CSRF issue: the CSRF token is missing
    or is incorrect. Make sure that your template includes `{{ csrf_token }}`.

    **`405 Method Not Allowed`.** Something sent a `GET`, usually a link or an address-bar
    visit to the API URL. The endpoint only takes `POST`.

    **The data saves but every field is empty.** Check that your jsPsych trials actually
    record data. `jsPsych.data.get().values()` should return populated objects. An empty
    timeline posts empty trials.

## Checkpoint

??? example "The whole of `study/templates/study/study_detail.html` at this point"
    If anything above didn't land where you expected, compare against this.

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
        const PARTICIPANT_ID = "{{ participant_id|escapejs }}";
        const CONDITION = "{{ condition|escapejs }}";
        const CSRF_TOKEN = "{{ csrf_token }}";
        const DATA_URL = "{% url 'study:data' study.slug %}";

        function saveData() {
            const message = html => document.body.innerHTML =
                "<div style='text-align:center;margin-top:3em;'>" + html + "</div>";

            message("<p>Saving your data, please don't close this window...</p>");
            return fetch(DATA_URL, {
                method: "POST",
                mode: "same-origin",                       // don't send the CSRF token off-origin
                headers: {"Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN},
                body: JSON.stringify({
                    participant_id: PARTICIPANT_ID,
                    condition: CONDITION,
                    trials: jsPsych.data.get().values()
                })
            })
                .then(response => {
                    if (!response.ok) throw new Error("HTTP " + response.status);  // 4xx/5xx isn't success
                    return response.json();
                })
                .then(result => {
                    message("<p>Thank you, your data has been saved.</p>");
                })
                .catch(() => {
                    // keep the data in the page and let them retry rather than losing the run
                    message("<p>Sorry, saving failed.</p>" +
                        "<button onclick='saveData()'>Try again</button>");
                });
        }

        const jsPsych = jsPsychModule.initJsPsych({ on_finish: saveData });
        let timeline = [];

        {{ study.code|safe }}   {# the researcher's pasted timeline goes here #}

        jsPsych.run(timeline);
    </script>
    </body>
    </html>
    ```

Run the study at `/study/flanker/?participant_id=p01&condition=A`, finish it, and you should see *"Thank you, your data has been saved."*
Open the admin at `/admin/`, look under **Study data**, and your run is there, with the
whole trial array in its `data` field. Under **Participants** you'll find `p01`.

We've completed data capture now. [Chapter 4b](04b-finishing-the-run.md) adds two finishing touches: sending participants back to Prolific, and a preview mode that saves nothing.
