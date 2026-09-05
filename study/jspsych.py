"""Which vendored jsPsych plugin files a study page should load: all of them.

jsPsych keeps each trial type in its own plugin file, so a timeline can only use the
trial types whose plugins the page has loaded. A researcher pastes their own code into
``Study.code``, and the platform can't know in advance which trial types that code uses,
so we ship every plugin and load the lot. A pasted study then can't fail on a plugin
nobody remembered to add.

Loading everything is cheap enough to be the right default: the 52 small plugins come to
269 KB all together, on top of a 77 KB core. The exception is ``plugin-survey.js``, which
bundles the whole SurveyJS library and weighs 1.3 MB on its own — the price of never
having to think about this again.

Listing the directory (rather than naming 53 files in the template) means vendoring a new
or updated plugin is a file copy with no code change. The list is cached, so adding a file
needs a server restart to show up.
"""
# --8<-- [start:plugin-files]
from functools import cache
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent / "static" / "study" / "jspsych"


@cache
def plugin_files():
    """Every vendored ``plugin-*.js``, sorted so the page's script order is stable."""
    return sorted(path.name for path in PLUGIN_DIR.glob("plugin-*.js"))
# --8<-- [end:plugin-files]
