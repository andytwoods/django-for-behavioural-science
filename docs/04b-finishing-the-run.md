# 4b · Finishing the run

<span class="time-pill">About 15 minutes</span>

Your study now saves its data. This short chapter adds two things you'll want before running a real study: sending participants back to Prolific when they finish, so they get paid, and a way to try a study without saving anything.

## Returning participants to Prolific

On [Prolific](https://www.prolific.com/) a submission has to be marked
**complete** before you approve and the person is paid. The
recommended way to record completion is to redirect the participant to a specific URL at Prolific. This is what the `completion_url` field on `Study` is for. Add it to `study/models.py`, inside the `Study` class (indented, just below the `created` field):

```python
--8<-- "study/models.py:study-flags"
```

Then run the migrations:

--8<-- "includes/migrate-reminder.md"

The template adds `completion_url` to the page. Add this line next to your other constants:

<!-- source: study/templates/study/study_detail.html -->
```javascript
const COMPLETION_URL = "{{ study.completion_url|escapejs }}";
```

and then, once the data is stored, we let the participant know and redirect to Prolific. Replace the `.then(result => { ... })` block in `saveData` with this one:

<!-- source: study/templates/study/study_detail.html -->
```javascript
.then(result => {
    if (COMPLETION_URL) {
        message("<p>Data saved. Returning you to Prolific…</p>" +
            "<p>If you're not redirected, <a href='" + COMPLETION_URL + "'>click here to finish</a>.</p>");
        setTimeout(function () { window.location = COMPLETION_URL; }, 1500);
    } else {
        message("<p>Thank you, your data has been saved.</p>");
    }
})
```

If you leave `completion_url` blank you just get the thank-you. If we do have a `completion_url` though, we confirm the save *and* then
auto-redirect (Prolific recommend this). There's a short 1500ms delay so participants see their data was saved. 


## Trying a study without saving

Sometimes you want to run a study and *not* record any data. Adding `?preview=1` to the URL does this. The server reads `?preview=1` and informs the page not to save data. Add the `PREVIEW` line next to your other constants, and put the `if (PREVIEW)` check at the top of `saveData`, just below the `const message` statement:


<!-- source: study/templates/study/study_detail.html -->
```javascript
const PREVIEW = {{ preview|yesno:"true,false" }};   // set from ?preview=1 in the URL

function saveData() {
    const message = html => document.body.innerHTML =
        "<div style='text-align:center;margin-top:3em;'>" + html + "</div>";
    if (PREVIEW) {
        message("<p>Preview finished. This run was <b>not</b> saved to the platform database.</p>");
        return Promise.resolve();   // never POST
    }
    // ...otherwise save as usual
}
```

## Checkpoint

??? example "The whole of `study/templates/study/study_detail.html` at this point"
    If anything above didn't land where you expected, compare against this. It's the
    finished template, so it also has a small banner that makes preview runs obvious, a viewport tag that helps it display on phones, and more comments. You don't need to add those.

    ```html
    --8<-- "study/templates/study/study_detail.html"
    ```

To try the redirect, open your study in the admin, put any address in **Completion url**
(for example `https://example.com/`) and save. Run the study to the end: you'll see
*"Data saved. Returning you to Prolific…"*, then land on that address. Clear the field
again afterwards.

Then run [http://127.0.0.1:8000/study/flanker/?preview=1](http://127.0.0.1:8000/study/flanker/?preview=1).
At the end you'll see *"Preview finished. This run was **not** saved to the platform
database."*, and no new row appears under **Study data** in the admin.

