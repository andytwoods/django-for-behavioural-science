from django.db import models


# --8<-- [start:study-model]
class Study(models.Model):
    """A single experiment a researcher wants to host and collect data for.

    In v1 the researcher pastes their jsPsych *timeline* code into ``code``; the
    platform wraps it with the jsPsych library and the data-capture plumbing when
    it serves the study. Media assets are hosted externally by the researcher and
    referenced by absolute HTTPS URL from within ``code`` (see the tutorial's
    "adding a study" chapter for the HTTPS/CORS caveats).
    """

    name = models.CharField(max_length=200, help_text="Human-readable study title, e.g. 'Flanker task'.")
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
