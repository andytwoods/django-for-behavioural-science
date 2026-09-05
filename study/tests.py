from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .jspsych import plugin_files
from .models import Participant, Study, StudyData


class DataCaptureTests(TestCase):
    """The data-capture endpoint is the heart of the platform, so it is the first
    thing we test. The paper points readers at this file (R1.18, R2.9)."""

    # --8<-- [start:capture-test]
    def test_posting_trials_creates_a_dataset(self):
        # 'flanker' is seeded by the 0002 data migration, which runs for the test DB.
        url = reverse("study:data", args=["flanker"])
        payload = {
            "participant_id": "p01",
            "condition": "congruent-first",
            "trials": [
                {"rt": 512, "response": "f", "correct": True},
                {"rt": 634, "response": "j", "correct": False},
            ],
        }

        response = self.client.post(url, data=payload, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudyData.objects.count(), 1)

        dataset = StudyData.objects.get()
        self.assertEqual(dataset.condition, "congruent-first")
        self.assertEqual(dataset.participant.external_id, "p01")
        # The whole run lands in one JSONField, in order.
        self.assertEqual(len(dataset.data), 2)
        self.assertEqual(dataset.data[0]["rt"], 512)
    # --8<-- [end:capture-test]

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse("study:data", args=["flanker"]))
        self.assertEqual(response.status_code, 405)

    def test_unknown_study_returns_404(self):
        url = reverse("study:data", args=["does-not-exist"])
        response = self.client.post(url, data={"trials": []}, content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_malformed_json_is_rejected(self):
        url = reverse("study:data", args=["flanker"])
        response = self.client.post(url, data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudyData.objects.count(), 0)

    def test_non_object_json_is_rejected(self):
        # Valid JSON, but a bare list (or null, or a string) is the wrong shape.
        url = reverse("study:data", args=["flanker"])
        response = self.client.post(url, data="[]", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudyData.objects.count(), 0)

    def test_non_utf8_body_is_rejected(self):
        # Invalid bytes should be a clean 400, not a UnicodeDecodeError -> 500.
        url = reverse("study:data", args=["flanker"])
        response = self.client.post(url, data=b"\xff\xfe\x00", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudyData.objects.count(), 0)

    def test_too_many_trials_are_rejected(self):
        from .views import MAX_TRIALS

        url = reverse("study:data", args=["flanker"])
        response = self.client.post(
            url,
            data={"trials": [{} for _ in range(MAX_TRIALS + 1)]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StudyData.objects.count(), 0)

    def test_wrong_field_types_and_lengths_are_rejected(self):
        url = reverse("study:data", args=["flanker"])
        bad_payloads = [
            {"participant_id": ["not", "a", "string"], "trials": []},   # id wrong type
            {"participant_id": "x" * 201, "trials": []},                # id too long
            {"condition": {"a": 1}, "trials": []},                      # condition wrong type
            {"condition": "c" * 101, "trials": []},                     # condition too long
            {"trials": "not a list"},                                   # trials wrong type
            {},                                                         # trials missing
            {"trials": [{"rt": 1}, "not an object"]},                   # a trial is a scalar
        ]
        for payload in bad_payloads:
            response = self.client.post(url, data=payload, content_type="application/json")
            self.assertEqual(response.status_code, 400, msg=payload)
        self.assertEqual(StudyData.objects.count(), 0)


class StudyServeTests(TestCase):
    """Serving a study and reading the participant/condition from the URL (R1.7)."""

    def test_study_page_renders(self):
        response = self.client.get(reverse("study:detail", args=["flanker"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "jsPsych.run")

    def test_participant_and_condition_read_from_url_params(self):
        url = reverse("study:detail", args=["flanker"]) + "?participant_id=p42&condition=B"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'const PARTICIPANT_ID = "p42";')
        self.assertContains(response, 'const CONDITION = "B";')

    def test_unknown_study_page_returns_404(self):
        response = self.client.get(reverse("study:detail", args=["does-not-exist"]))
        self.assertEqual(response.status_code, 404)

    def test_preview_flag_reflects_the_url(self):
        # ?preview=1 sets the front-end PREVIEW flag; anything else leaves it false.
        detail = reverse("study:detail", args=["flanker"])
        self.assertContains(self.client.get(detail), "const PREVIEW = false")
        self.assertContains(self.client.get(detail + "?preview=1"), "const PREVIEW = true")
        # ?preview=0 must NOT turn preview on (the old bool() bug did).
        self.assertContains(self.client.get(detail + "?preview=0"), "const PREVIEW = false")

    def test_completion_url_rendered_into_page_when_set(self):
        # With a completion URL set, the page should carry it so it can send the
        # participant on at the end (e.g. back to Prolific to get paid).
        study = Study.objects.get(slug="flanker")
        study.completion_url = "https://app.prolific.com/submissions/complete?cc=ABC123"
        study.save()
        response = self.client.get(reverse("study:detail", args=["flanker"]))
        # escapejs escapes '=' to a \\u003D unicode escape (which is still '=' at runtime),
        # so assert on the path part rather than the query string.
        self.assertContains(response, "app.prolific.com/submissions/complete")

    def test_public_study_list_hides_researcher_data(self):
        # The landing page is public, so it must not link to the staff-only dashboard
        # or reveal how many sessions have been collected.
        response = self.client.get(reverse("study:list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("study:dashboard", args=["flanker"]))
        self.assertNotContains(response, "collected")


class ExportTests(TestCase):
    """Dashboard + CSV/JSON export (M5). These are staff-only, so we log in first."""

    def setUp(self):
        self.study = Study.objects.get(slug="flanker")
        participant = Participant.objects.create(external_id="p01")
        StudyData.objects.create(
            study=self.study,
            participant=participant,
            condition="A",
            data=[{"rt": 500, "correct": True}, {"rt": 620, "correct": False}],
        )
        staff = get_user_model().objects.create_user("staff", password="pw", is_staff=True)
        self.client.force_login(staff)

    def test_data_views_require_staff_login(self):
        anon = Client()  # not logged in
        for name in ["study:dashboard", "study:export_csv", "study:export_json"]:
            response = anon.get(reverse(name, args=["flanker"]))
            self.assertEqual(response.status_code, 302)  # redirected to the admin login

    def test_dashboard_shows_counts(self):
        response = self.client.get(reverse("study:dashboard", args=["flanker"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "p01")

    def test_csv_neutralises_formulas_in_ids_and_headings(self):
        # participant_id, condition and the data-derived column headings are all
        # externally controlled, so they get the apostrophe treatment too.
        hostile = Participant.objects.create(external_id="=HYPERLINK(evil)")
        StudyData.objects.create(
            study=self.study, participant=hostile, condition="+SUM(A1)",
            data=[{"=key": 1, " \t=padded": 2}],
        )
        body = self.client.get(reverse("study:export_csv", args=["flanker"])).content.decode()
        self.assertIn("'=HYPERLINK(evil)", body)   # id neutralised
        self.assertIn("'+SUM(A1)", body)           # condition neutralised
        self.assertIn("'=key", body)               # heading neutralised
        self.assertIn("' \t=padded", body)         # leading whitespace doesn't hide it

    def test_csv_export_has_header_and_rows(self):
        response = self.client.get(reverse("study:export_csv", args=["flanker"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        body = response.content.decode()
        lines = body.strip().splitlines()
        self.assertIn("participant_id", lines[0])
        self.assertIn("rt", lines[0])           # a data key discovered from the trials
        self.assertEqual(len(lines), 3)         # header + 2 trials
        self.assertIn("p01", body)

    def test_csv_keeps_its_own_counter_apart_from_jspsychs(self):
        # jsPsych stamps a trial_index onto every trial it records, so the exporter's own
        # counter is called trial_row. Both belong in the CSV, under names of their own.
        StudyData.objects.create(
            study=self.study, participant=None, condition="",
            data=[{"trial_index": 7, "rt": 1}],
        )
        response = self.client.get(reverse("study:export_csv", args=["flanker"]))
        header = response.content.decode().splitlines()[0].split(",")
        self.assertEqual(header.count("trial_row"), 1)      # ours, the position in the run
        self.assertEqual(header.count("trial_index"), 1)    # jsPsych's, from the trial data

    def test_json_export_structure(self):
        response = self.client.get(reverse("study:export_json", args=["flanker"]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["study"], "flanker")
        self.assertEqual(len(payload["datasets"]), 1)
        self.assertEqual(len(payload["datasets"][0]["trials"]), 2)
        self.assertEqual(payload["datasets"][0]["participant_id"], "p01")


class StudyFormTests(TestCase):
    """Registering a study through the site's own ModelForm (``study/forms.py``)."""

    def setUp(self):
        staff = get_user_model().objects.create_user("registrar", password="pw", is_staff=True)
        self.client.force_login(staff)

    def test_the_form_is_not_public(self):
        # `code` is JavaScript served to participants, so an anonymous visitor is sent
        # to the login page rather than being handed a way to inject it.
        response = Client().get(reverse("study:create"))
        self.assertEqual(response.status_code, 302)

    def test_public_study_list_does_not_advertise_the_form(self):
        response = Client().get(reverse("study:list"))
        self.assertNotContains(response, reverse("study:create"))

    # --8<-- [start:form-test]
    def test_valid_post_creates_the_study(self):
        response = self.client.post(
            reverse("study:create"),
            data={"name": "Posner cueing task", "slug": "posner", "code": "const timeline = [];"},
        )

        # A successful save redirects to the new study, so the researcher can try it.
        self.assertRedirects(response, reverse("study:detail", args=["posner"]))
        study = Study.objects.get(slug="posner")
        self.assertEqual(study.name, "Posner cueing task")
    # --8<-- [end:form-test]

    def test_the_form_offers_only_the_three_editable_fields(self):
        response = self.client.get(reverse("study:create"))
        self.assertEqual(response.status_code, 200)
        for field in ["name", "slug", "code"]:
            self.assertContains(response, 'name="%s"' % field)
        # `researchers` and `completion_url` are on the model but left off the form.
        self.assertNotContains(response, 'name="researchers"')
        self.assertNotContains(response, 'name="completion_url"')

    def test_a_taken_slug_is_reported_not_saved(self):
        # Study.slug is unique=True, and the ModelForm turns that into a form error
        # rather than letting the database raise.
        response = self.client.post(
            reverse("study:create"),
            data={"name": "Another flanker", "slug": "flanker", "code": "const timeline = [];"},
        )
        self.assertEqual(response.status_code, 200)  # re-rendered, not redirected
        self.assertContains(response, "already exists")
        self.assertEqual(Study.objects.filter(slug="flanker").count(), 1)

    def test_missing_fields_are_reported_not_saved(self):
        before = Study.objects.count()
        response = self.client.post(
            reverse("study:create"), data={"name": "", "slug": "", "code": ""}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Study.objects.count(), before)

    def test_a_slug_with_illegal_characters_is_rejected(self):
        response = self.client.post(
            reverse("study:create"),
            data={"name": "Bad slug", "slug": "not a slug!", "code": "const timeline = [];"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Study.objects.filter(name="Bad slug").exists())


class CsrfTests(TestCase):
    """The endpoint is *not* CSRF-exempt: a POST without a valid token is rejected.
    This stops *another* site from POSTing here using a logged-in researcher's cookies.
    It does not authenticate the data, which is why the view still validates the body."""

    def test_post_without_csrf_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)  # the default test client skips CSRF
        response = client.post(
            reverse("study:data", args=["flanker"]),
            data={"trials": []},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(StudyData.objects.count(), 0)

    def test_rendered_page_sets_cookie_and_token_then_posts(self):
        # The positive half: rendering the study page sets the CSRF cookie, and posting
        # that token back in the header passes the check with enforcement on.
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("study:detail", args=["flanker"]))
        self.assertIn("csrftoken", page.cookies)  # {{ csrf_token }} set the cookie
        token = page.cookies["csrftoken"].value
        response = client.post(
            reverse("study:data", args=["flanker"]),
            data={"participant_id": "p1", "trials": [{"rt": 1}]},
            content_type="application/json",
            headers={"x-csrftoken": token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudyData.objects.count(), 1)


class ModelTests(TestCase):
    """Model behaviour the higher-level tests rely on (M6)."""

    def test_str_methods(self):
        study = Study.objects.get(slug="flanker")
        self.assertEqual(str(study), "Flanker task")
        participant = Participant.objects.create(external_id="p9")
        self.assertEqual(str(participant), "p9")
        dataset = StudyData.objects.create(study=study, participant=participant, data=[])
        self.assertIn("flanker", str(dataset))

    def test_deleting_study_cascades_to_its_data(self):
        study = Study.objects.create(name="Temp", slug="temp", code="")
        StudyData.objects.create(study=study, data=[{}])
        study.delete()
        self.assertEqual(StudyData.objects.filter(study__slug="temp").count(), 0)

    def test_deleting_participant_delinks_but_keeps_the_data(self):
        # SET_NULL: removing the participant record delinks their datasets rather than
        # destroying them. Whether what remains counts as anonymised is a separate,
        # data-dependent question (see chapter 5).
        study = Study.objects.get(slug="flanker")
        participant = Participant.objects.create(external_id="pX")
        dataset = StudyData.objects.create(study=study, participant=participant, data=[])
        participant.delete()
        dataset.refresh_from_db()
        self.assertIsNone(dataset.participant)


class AnonymisationTests(TestCase):
    """Removing the recruitment ID without destroying the runs (chapter 5)."""

    def test_anonymise_drops_the_id_but_keeps_the_runs_grouped(self):
        study = Study.objects.get(slug="flanker")
        participant = Participant.objects.create(external_id="prolific-abc123")
        first = StudyData.objects.create(study=study, participant=participant, data=[{"rt": 1}])
        second = StudyData.objects.create(study=study, participant=participant, data=[{"rt": 2}])

        participant.anonymise()

        participant.refresh_from_db()
        self.assertIsNone(participant.external_id)
        # The whole point: still knowably one person, just not a knowable one.
        self.assertEqual(participant.datasets.count(), 2)
        first.refresh_from_db(), second.refresh_from_db()
        self.assertEqual(first.participant_id, second.participant_id)

    def test_several_participants_can_be_anonymised(self):
        # A blank string would fail here on the unique constraint; NULLs don't collide.
        for external_id in ["p01", "p02", "p03"]:
            Participant.objects.create(external_id=external_id).anonymise()
        self.assertEqual(Participant.objects.filter(external_id__isnull=True).count(), 3)

    def test_anonymised_participant_still_has_a_readable_label(self):
        participant = Participant.objects.create(external_id="p01")
        participant.anonymise()
        self.assertIn("anonymised", str(participant))

    def test_deleting_is_still_the_stronger_option(self):
        # Level 3: the runs survive, but they can no longer be grouped as one person.
        study = Study.objects.get(slug="flanker")
        participant = Participant.objects.create(external_id="p01")
        StudyData.objects.create(study=study, participant=participant, data=[{"rt": 1}])
        StudyData.objects.create(study=study, participant=participant, data=[{"rt": 2}])
        participant.delete()
        orphaned = StudyData.objects.filter(study=study, participant__isnull=True)
        self.assertEqual(orphaned.count(), 2)


class PluginLoadingTests(TestCase):
    """Every vendored plugin reaches the page, so any pasted timeline can run."""

    def test_every_vendored_plugin_is_found(self):
        names = plugin_files()
        self.assertIn("plugin-html-keyboard-response.js", names)
        self.assertTrue(all(n.startswith("plugin-") and n.endswith(".js") for n in names))

    def test_page_includes_every_plugin_script(self):
        response = self.client.get(reverse("study:detail", args=["flanker"]))
        for name in plugin_files():
            self.assertContains(response, "jspsych/%s" % name)

    def test_page_includes_the_survey_stylesheet(self):
        # The survey plugin needs its own stylesheet, and it always ships now.
        response = self.client.get(reverse("study:detail", args=["flanker"]))
        self.assertContains(response, "survey.min.css")
