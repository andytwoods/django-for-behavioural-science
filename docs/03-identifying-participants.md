# 3 · Identifying participants

<span class="time-pill">About 15 minutes</span>

<figure class="apparatus" markdown>
![Five iMac G3 computers in the translucent colours Apple called flavours](assets/img/gear/ch4-imac-g3.jpg)
<figcaption markdown="span">
The five "flavours" of the [iMac G3](https://en.wikipedia.org/wiki/IMac_G3), 1999. Machines like these filled university labs
around the turn of the century, running experiments through packages such as
[PsyScope](https://en.wikipedia.org/wiki/PsyScope) and
[SuperLab](https://www.cedrus.com/superlab/). Or
[DMDX](https://psy1.psych.arizona.edu/~jforster/dmdx.htm), if you were more of a PC user
like me back then.
<br>Image: Stephen Hackett, CC BY-SA 4.0, via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Imac_G3_5_flavors_side_lineup.jpg).
</figcaption>
</figure>

??? note "Remember DMDX and PsyScope?"
    If you were in a lab around 2000, one of these was probably how you built a study:

    - [DMDX](https://psy1.psych.arizona.edu/~jforster/dmdx.htm) on Windows, written by
      Jonathan and Kenneth Forster and still in use, which got millisecond timing out of a
      PC by talking to the display hardware
      ([Forster & Forster, 2003](https://doi.org/10.3758/BF03195503))
    - [PsyScope](https://en.wikipedia.org/wiki/PsyScope) on the Mac, where you
      assembled a trial by dragging boxes around instead of writing code. It was remarkable for
      1993, and the reason a generation of psychologists owned a Mac
      ([Cohen, MacWhinney, Flatt & Provost, 1993](https://doi.org/10.3758/BF03204507))
    - [SuperLab](https://www.cedrus.com/superlab/) and
      [E-Prime](https://pstnet.com/products/e-prime/), the commercial options. Both are still sold today


**By the end of this chapter** the study will know who is doing it and which condition
they're in, read from the URL 🔗.

## Two kinds of URL parameter

Look at a real study link:

```
/study/flanker/?participant_id=p01&condition=A
```

There are two things going on in this URL:

- `flanker` is a **path parameter**. It's part of the address itself, and it's how the
  URL pattern picks the study. This is the `<slug:slug>` we encountered in the last chapter
- `participant_id` and `condition` are **query parameters**, the `key=value` pairs after
  the `?`. They carry extra information *about* this particular visit

Recruitment tools like [Prolific](https://www.prolific.com/) add such query parameters to your study URL (unique for each participant), allowing you to know who has done your study and thus who to pay!

## Read query parameters on the server

You could read query parameters in the participant's browser via JavaScript
([`URLSearchParams`](https://developer.mozilla.org/en-US/docs/Web/API/URLSearchParams)). I'd rather achieve the same thing in the backend using Python, as we already need to do related tasks here. Keeping similar logic in the same place reduces complexity ([see the KISS computer science principle](https://en.wikipedia.org/wiki/KISS_principle)), which is always a good thing.

The `study_detail` view you copied in chapter 2 already reads these query parameters. Here it is again, so we can look at those lines:

```python
--8<-- "study/views.py:study-detail-view"
```

See how `request.GET` holds various key pieces of information. From there we can look up `participant_id` and `condition` (defaulting to an empty string if they're missing) and put each one in the context as its own variable.

## Hand the extracted query parameters as variables to the front-end

See how in the template the python variables we just defined are passed to JavaScript variables. Add these two lines to `study/templates/study/study_detail.html`, inside the `<script>` block and above the `const jsPsych = ...` line:

<!-- source: study/templates/study/study_detail.html -->
```javascript
const PARTICIPANT_ID = "{{ participant_id|escapejs }}";
const CONDITION = "{{ condition|escapejs }}";
```

??? note "What `escapejs` is doing there"
    Both of those values originate from the URL, so they came from whoever wrote the link, and they could have been manipulated to run dodgy code. [`escapejs`](https://docs.djangoproject.com/en/6.1/ref/templates/builtins/#escapejs) rewrites quotes, angle brackets, backslashes
    and newlines as `\uXXXX` escapes, so a value can't break out of its JavaScript string and run as code.

## Where the Prolific IDs come from

When you set your study up on Prolific, you
paste your study URL with Prolific's **placeholders**, and Prolific fills them in per
participant:

```
https://your-site.example/study/flanker/?participant_id={{%PROLIFIC_PID%}}&condition=A
```

Prolific swaps `{{%PROLIFIC_PID%}}` for each participant's real ID. In [chapter 4b](04b-finishing-the-run.md), at the end of the study we send participants back to Prolific so their submission is recorded as complete.

Prolific also passes `{{%STUDY_ID%}}` and `{{%SESSION_ID%}}`. We only read `participant_id` here. Note that `SESSION_ID` offers a security measure to check if participants manipulated the URLs provided by Prolific (for more, see [*Secure external URL*](https://researcher-help.prolific.com/en/articles/445133-recording-prolific-id-s)).

## Checkpoint

With the server running, open
[http://127.0.0.1:8000/study/flanker/?participant_id=p01&condition=A](http://127.0.0.1:8000/study/flanker/?participant_id=p01&condition=A).
The study looks exactly as before. To see the difference, have a look at the page source (right-click,
**View Page Source**) and find your two new lines:

```javascript
const PARTICIPANT_ID = "p01";
const CONDITION = "A";
```

No data is saved yet. The page knows who the participant is, but when the study finishes the
data just disappears. In the next chapter we sort this out!

