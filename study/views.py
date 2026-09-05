import csv
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import StudyForm
from .jspsych import plugin_files
from .models import Participant, Study, StudyData

# A public endpoint shouldn't accept an unbounded run. This caps the trials in one
# submission; Django's DATA_UPLOAD_MAX_MEMORY_SIZE (2.5 MB by default) caps the raw body.
MAX_TRIALS = 10_000


# --8<-- [start:study-detail-view]
def study_detail(request, slug):
    """Serve a single study to a participant.

    The study is identified by a *path* parameter (``slug``, matched by the URL
    pattern); the participant and condition arrive as *query* parameters, e.g.
    ``/study/flanker/?participant_id=p01&condition=A``. We read them here on the
    server and pass them into the template.
    """
    study = get_object_or_404(Study, slug=slug)

    # ?preview=1 runs the study but skips saving (see the template). Match "1" exactly, so
    # ?preview=0 doesn't accidentally turn it on.
    preview = request.GET.get("preview") == "1"
    participant_id = request.GET.get("participant_id", "")
    condition = request.GET.get("condition", "")

    context = {
        "study": study,

        # maybe we want to give a collaborator our draft study but we dont
        # want their data to save. Preview lets us do this.
        "preview": preview,

        # Every plugin. The researcher's pasted code can use any trial type
        # without telling us which, so the page is given them all (see study.jspsych).
        "jspsych_plugins": plugin_files(),

        # Who is doing the study, and which condition they're in, read from the query string
        # so the front-end never has to parse the URL itself.
        "participant_id": participant_id,
        "condition": condition,
    }
    return render(request, "study/study_detail.html", context)
# --8<-- [end:study-detail-view]


# --8<-- [start:submit-data-view]
@require_POST  # a GET (or anything but POST) gets a 405; this endpoint only receives data
def submit_data(request, slug):
    """Receive the trial data jsPsych posts at the end of a study.
    """
    study = get_object_or_404(Study, slug=slug)  # this is a bit of Django magic. If our database can't find the slug in question, the participant is immediately shown a 404 page

    # Everything in the body came from the open internet, so it's checked before we
    # touch the database by parse_submission
    try:
        participant_id, condition, trials = parse_submission(request.body)
    except SubmissionError as exc:
        return HttpResponseBadRequest(str(exc))

    # Look up (or create) the participant, then store their whole run as one row.
    # get_or_create returns a (object, created) tuple; we only want the object, so we
    # unpack the "created" flag into `_`, the conventional name for a value to ignore.
    participant = None
    if participant_id:
        participant, _ = Participant.objects.get_or_create(external_id=participant_id)
    dataset = StudyData.objects.create(
        study=study, participant=participant, condition=condition, data=trials
    )

    # A reply, so the front-end can show its thank-you message.
    return JsonResponse({"status": "ok", "id": dataset.pk})
# --8<-- [end:submit-data-view]


class SubmissionError(Exception):
    """The posted body isn't a usable submission. The message is safe to show."""


def parse_submission(body):
    """Check a posted body and return the ``(participant_id, condition, trials)`` in it.

    Nothing here is trusted: it all arrived from a public endpoint, so every field is
    checked before any of it reaches the database. Raising (rather than returning an
    error) keeps the happy path in ``submit_data`` a straight line.
    """
    # jsPsych sends a JSON body like {participant_id, condition, trials: [...]}.
    # Reject anything malformed with a 400 rather than storing half of it. Valid JSON
    # of the wrong shape (a bare list, null, a string) is still bad input, so check
    # the top level is an object before we start calling .get() on it. (UnicodeDecodeError:
    # a body that isn't valid UTF-8 fails before it can fail as JSON.)
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SubmissionError("Request body must be valid JSON.") from None
    if not isinstance(payload, dict):
        raise SubmissionError("JSON body must be an object.")

    # A JSONField would happily store a number where we expect a string, and creating a
    # model doesn't run field validation for us, so this is where we enforce the contract.
    participant_id = payload.get("participant_id", "")
    condition = payload.get("condition", "")
    trials = payload.get("trials")
    if not isinstance(participant_id, str) or len(participant_id) > 200:
        raise SubmissionError("'participant_id' must be a string of at most 200 characters.")
    if not isinstance(condition, str) or len(condition) > 100:
        raise SubmissionError("'condition' must be a string of at most 100 characters.")
    # A whitespace-only ID is no ID.
    participant_id = participant_id.strip()
    condition = condition.strip()
    if not isinstance(trials, list):
        raise SubmissionError("'trials' must be a list.")
    if len(trials) > MAX_TRIALS:
        raise SubmissionError(f"Too many trials (max {MAX_TRIALS}).")
    if not all(isinstance(trial, dict) for trial in trials):
        raise SubmissionError("Every trial must be a JSON object.")

    return participant_id, condition, trials


# --8<-- [start:study-create-view]
# The `code` field is JavaScript that runs in every participant's browser, so this form
# is staff-only, exactly like the dashboard. See the "Registering studies" page in Going
# further before opening it to a wider group.
@staff_member_required
def study_create(request):
    """Register a study from a form on the site, rather than through the admin.

    One view handles both halves of a form's life. A GET renders an empty (*unbound*)
    form; a POST hands the submitted data back to the same form class to check. If it
    validates, ``form.save()`` writes the ``Study`` row and we send the researcher
    straight to their new study. If it doesn't, the same template is rendered again with
    the errors attached to the fields that caused them, and nothing is saved.
    """
    if request.method == "POST":
        form = StudyForm(request.POST)
        # is_valid() runs every field's own checks plus the model's, so the unique=True on
        # Study.slug becomes a "this slug is taken" message rather than a database error.
        if form.is_valid():
            study = form.save()
            return redirect("study:detail", slug=study.slug)
    else:
        form = StudyForm()
    return render(request, "study/study_form.html", {"form": form})
# --8<-- [end:study-create-view]


def study_list(request):
    """Public landing page: every study on the platform.

    This page is public (participants land here), so it shows no dataset counts and no
    links to the staff-only dashboard.
    """
    studies = Study.objects.all()
    return render(request, "study/study_list.html", {"studies": studies})


@staff_member_required  # participant data is not public: only logged-in staff may view it
def dashboard(request, slug):
    """A simple researcher view of the data collected for one study."""
    study = get_object_or_404(Study, slug=slug)
    datasets = study.datasets.select_related("participant").order_by("-created")
    context = {
        "study": study,
        "datasets": datasets,
        "n_datasets": datasets.count(),
        "n_participants": Participant.objects.filter(datasets__study=study).distinct().count(),
    }
    return render(request, "study/dashboard.html", context)


# --8<-- [start:export-csv-view]
@staff_member_required  # exports contain participant data, so they are staff-only too
def export_csv(request, slug):
    """Export every trial for a study as one CSV row per trial.

    We build the header rows from the unique combination of keys present in the data.
    """
    study = get_object_or_404(Study, slug=slug)
    # The database stores one row per *run* (a StudyData holding the whole JSON blob); the
    # CSV is the other way round, one row per *trial*, the long format R and pandas expect.
    # So further down each dataset needs to become several rows.

    datasets = list(
        study.datasets.select_related("participant").order_by("created", "id")
    )

    # jsPsych records different fields for different paradigms, so build the column set
    # from the union of keys across every trial in every dataset.
    data_keys = sorted(
        {k for d in datasets for t in d.data if isinstance(t, dict) for k in t}
    )
    # ``trial_row`` is this exporter's own counter, the trial's position in the run, so the
    # long format doesn't lose the order the trials arrived in. It's deliberately not
    # called ``trial_index``: jsPsych records a ``trial_index`` of its own (the trial's
    # place in the timeline), and that arrives as a data key below. The two usually agree,
    # but they part company as soon as a timeline loops or the researcher filters the data
    # before posting, so each gets its own column rather than one clashing with the other.
    base_cols = ["dataset_id", "participant_id", "condition", "collected", "trial_row"]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{slug}_data.csv"'
    writer = csv.writer(response)
    # The headings pass through _csv_cell too: data_keys come from submitted trials, so a
    # hostile trial key of "=..." would otherwise become an executable heading.
    writer.writerow([_csv_cell(col) for col in base_cols + data_keys])
    for d in datasets:

        participant_id = _csv_cell(d.participant.external_id if d.participant else "")
        condition = _csv_cell(d.condition)
        collected = d.created.isoformat()
        for trial_row, trial in enumerate(d.data):
            row = [d.pk, participant_id, condition, collected, trial_row]
            # A trial field can itself be nested (a list or dict, e.g. a response array),
            # to any depth. We don't explode that into more columns; we keep the whole
            # subtree in one cell as a JSON string (see _csv_cell). Left to itself the csv
            # module would str() a Python list to "['f', 'j']" — single quotes, not valid
            # JSON — which no JSON parser will read back. json.dumps writes ["f", "j"]
            # instead, so the cell re-parses cleanly with fromJSON() in R or json.loads in
            # pandas, where you can unpack the nesting knowing which question it came from.
            row += [_csv_cell(trial.get(k, "")) if isinstance(trial, dict) else "" for k in data_keys]
            writer.writerow(row)
    return response


def _csv_cell(value):
    """Render one externally-sourced value for a CSV cell.

    Nested values (e.g. a response array) become JSON so they can be dropped into R or
    pandas. A string a spreadsheet might read as a formula is prefixed with an
    apostrophe, so an opened CSV can't run a participant's ``=...`` answer as a
    calculation (CSV/formula injection); leading whitespace doesn't hide the trigger
    character. Analysis code reading the raw text may need to strip that apostrophe.
    """
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
# --8<-- [end:export-csv-view]


@staff_member_required  # nested JSON export of participant data: staff-only
def export_json(request, slug):
    """Export a study's data as JSON: one entry per run, each with its trials."""
    study = get_object_or_404(Study, slug=slug)
    datasets = study.datasets.select_related("participant").order_by("created", "id")
    payload = [
        {
            "id": d.pk,
            "participant_id": d.participant.external_id if d.participant else None,
            "condition": d.condition,
            "created": d.created.isoformat(),
            "trials": d.data,
        }
        for d in datasets
    ]
    return JsonResponse({"study": study.slug, "datasets": payload})
