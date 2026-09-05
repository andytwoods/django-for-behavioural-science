from django.db import models


# --8<-- [start:researcher-model]
class Researcher(models.Model):
    """A researcher who owns and registers studies.

    This gives us the other half of a ManyToMany relationship with Study: one study can
    have several researchers, and one researcher can own several studies. Django creates
    the link table (``study_researchers``) for that relationship automatically.
    """

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name
# --8<-- [end:researcher-model]


# --8<-- [start:study-model]
class Study(models.Model):
    """A single experiment a researcher wants to host and collect data for.

    jsPsych *timeline* code will end up being stored in `code`; the
    platform takes this and wraps it with the jsPsych library and the data-capture plumbing when it serves the study. Media assets (images, sounds) are hosted externally by the
    researcher and referenced by absolute HTTPS URL from within `code`.
    """

    name = models.CharField(max_length=200, help_text="Human-readable study title, e.g. 'Flanker task'.")

    # A slug is a short label built only from letters, numbers, hyphens and
    # underscores. These characters are safe in URLs.
    slug = models.SlugField(
        unique=True,
        help_text="Short URL-safe identifier; appears in the study URL, e.g. /study/flanker/.",
    )
    code = models.TextField(help_text="The researcher's jsPsych timeline code (JavaScript).")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "studies"
        ordering = ["-created"]

    def __str__(self):
        return self.name
# --8<-- [end:study-model]

    # The fields below are added by later chapters of the tutorial, each in its own
    # snippet region so the chapter that teaches a field is the chapter that shows it.
    # Declaring them after ``Meta`` and ``__str__`` is unusual to look at but makes no
    # difference to Django: it collects fields by their creation order, not their
    # position relative to the methods.

    # --8<-- [start:study-flags]
    completion_url = models.URLField(
        blank=True,
        default="",
        help_text="Where participants go when they finish, e.g. your Prolific completion URL. "
        "Leave blank to just show a thank-you message.",
    )


    # --8<-- [end:study-flags]

    # A study can have many researchers, and a researcher many studies: a ManyToMany.
    # (Explained in the "Study ownership" page of Going Further.)
    # --8<-- [start:researchers-field]
    researchers = models.ManyToManyField(
        Researcher,
        related_name="studies",
        blank=True,
        help_text="The researcher(s) who own this study.",
    )
    # --8<-- [end:researchers-field]


# --8<-- [start:capture-models]
class Participant(models.Model):
    """A person completing studies, identified by the ``participant_id`` URL param."""

    external_id = models.CharField(
        max_length=200,
        unique=True,
        # Nullable so the recruitment ID can be removed without destroying the row. A
        # blank string wouldn't do: the second anonymised participant would collide on
        # the unique constraint, where NULLs don't count as equal to one another.
        null=True,
        blank=True,
        help_text="The participant_id passed in the study URL",
    )
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.external_id or f"anonymised participant #{self.pk}"

    def anonymise(self):
        """Deletes the recruitment ID, keeping the runs grouped as one person.
        """
        self.external_id = None
        self.save()


class StudyData(models.Model):
    """One participant's whole run of a study: every trial in a single ``JSONField``.

    jsPsych hands us study data as an array of trial objects, and we store it exactly as it arrived.
    """

    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name="datasets")
    participant = models.ForeignKey(
        Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="datasets"
    )
    condition = models.CharField(max_length=100, blank=True)
    data = models.JSONField(help_text="The whole jsPsych run: a list of trial objects.")
    created = models.DateTimeField(auto_now_add=True)

    # This section tells your database how to order data when it is returned to you. Django now also knows how you prefer data from this table to be called.
    class Meta:
        ordering = ["-created"]
        verbose_name_plural = "study data"

    def __str__(self):
        return f"{self.study.slug} data #{self.pk}"
# --8<-- [end:capture-models]
