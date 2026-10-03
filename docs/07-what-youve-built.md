# 7 · What you've built

<span class="time-pill">About 15 minutes, including the exercise</span>

You've built a small study-hosting platform. It can:

- serve any jsPsych timeline you paste into the admin, each study with its own url
- if you use Prolific, it can read who the participant is, and which condition they're in, from the study link
- check submissions, then store study data alongside its associated study and participant
- send participants back to Prolific when they finish their study
- run a preview of the study that does not save
- show staff a dashboard, and export the data as long-format CSV or nested JSON

## It only runs on your computer

Everything so far runs on `runserver`, at `127.0.0.1`, so you're the only person who can
reach it. Here we are using Django's development server, which is the right tool for building web apps. To run a real study you need to deploy the app: put it on a server with a
public address, HTTPS and a production database, and switch off debug mode.
On that server, Django isn't run with `runserver`, which isn't built to be secure or fast
enough for real visitors. A production server such as [Gunicorn](https://gunicorn.org/)
or [Uvicorn](https://uvicorn.dev/) runs it instead.

The paper's *Deployment* section goes through the options for this, from platform-as-a-service
hosts to renting your own server, along with monitoring and keeping your accounts secure.
For my own research apps I use a managed deployment tool ([Appliku](https://appliku.com/),
about €10 a month) with a fixed-price server in the EU ([Hetzner](https://www.hetzner.com/),
about €6 a month). Before you deploy, also work through Django's own
[deployment checklist](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/).

!!! note "Coming soon: deploying your app"
    This tutorial doesn't cover deployment yet. A chapter is on its way that takes the app
    you've built from your computer to a live server that participants can reach. Until
    then, the paper and Django's checklist above are the places to start.

## From a Flanker task to your own study

The platform we have developed here follows the same patterns used in some of the bigger applications mentioned in the
[paper](https://osf.io/preprints/psyarxiv/xrm5w_v2): a front-end that runs the study, and
a back-end that knows who each participant is and stores what they did. The paper calls
this a *hybrid* approach. You keep an established experiment library like jsPsych, and add
a back-end for the things it can't do on its own.

Once you have a back-end, a lot more becomes possible. The paper's examples include:

- linking one participant's sessions across days, or across devices (TestXR hands a
  participant from a shared iPad to their own phone with a QR code)
- inviting only the participants who have the right hardware, or who live near a testing
  site
- running a diary study over WhatsApp (LiveQual)
- taking in data from hardware, such as a Raspberry Pi counting the people in a room

Each of these starts with models and views like the ones you've written. Your
`Participant` model, for example, already groups every run a person does under one ID, so
a second session is just a second `StudyData` row.

If [Pavlovia](https://pavlovia.org) or
[Gorilla](https://gorilla.sc/) already does what your study needs, use it. The paper's
section *When to use bespoke web applications* has a short set of questions to help you
decide.

## Try it yourself: count the trials

Here's a challenge. Add a **Trials** column to the
dashboard, showing how many trials each dataset holds.

??? tip "Hint"
    You don't need to touch the view. Each dataset's `data` field is a list, and Django's
    [`length`](https://docs.djangoproject.com/en/6.1/ref/templates/builtins/#length)
    template filter counts the items in a list.

??? example "Answer"
    In `study/templates/study/dashboard.html`, add a heading to the header row:

    ```html
    <tr><th>Dataset</th><th>Participant</th><th>Condition</th><th>Trials</th><th>Collected</th></tr>
    ```

    then a matching cell in each dataset's row, between the condition and the date:

    ```html
    <td>{{ dataset.data|length }}</td>
    ```

    The table now has five columns, so change the empty row's `colspan="4"` to
    `colspan="5"`.

## Where next

If you'd like to keep going with this app, the Going further pages add researchers who
own studies, a shared page layout, and a form for registering studies without the admin.
For learning Django more widely, [Where to go next](resources.md) lists the documentation,
books, podcasts and communities I'd recommend.

