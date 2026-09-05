"""Extend the abbreviation tooltips to inline code spans.

The `abbr` markdown extension gives jargon a dotted underline and a tooltip — the browser's
own "there's more to say about this word" affordance — from the definitions in
``includes/abbreviations.md``. It only touches prose, though, and in a programming tutorial
half the sightings of a word like *slug* are inline code: ``sets `slug` to "flanker"``.

So this hook does the other half. After a page is rendered it finds inline code spans whose
whole content is a defined term and wraps them in the same ``<abbr>``, using the same
definitions file, so there's still only one place to edit a term.

Deliberately narrow: only spans that are *exactly* the term (``<code>slug</code>``, not
``<code>&lt;slug:slug&gt;</code>``), and nothing inside a ``<pre>`` block, so code samples
are never touched.

Wired up via `hooks:` in mkdocs.yml.
"""

import re
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS = REPO_ROOT / "includes" / "abbreviations.md"

# `*[slug]: A short, URL-safe label ...`
DEFINITION_LINE = re.compile(r"^\*\[(?P<term>[^\]]+)\]:\s*(?P<meaning>.+)$")

# Everything from a <pre ...> to its </pre>, so code blocks can be held out of the way.
PRE_BLOCK = re.compile(r"<pre\b.*?</pre>", re.S)

def _definitions():
    """{term: meaning}, from the same file the abbr extension appends to every page.

    Read on every page rather than cached, so editing a definition shows up on the next
    `mkdocs serve` rebuild instead of needing the server restarted. The file is a handful
    of lines; the reading costs nothing.
    """
    terms = {}
    if DEFINITIONS.is_file():
        for line in DEFINITIONS.read_text().split("\n"):
            match = DEFINITION_LINE.match(line.strip())
            if match:
                terms[match["term"]] = match["meaning"].strip()
    return terms


def _wrap(html, terms):
    for term, meaning in terms.items():
        html = re.sub(
            r"<code>%s</code>" % re.escape(escape(term)),
            '<abbr title="%s"><code>%s</code></abbr>' % (escape(meaning, quote=True), escape(term)),
            html,
        )
    return html


def on_page_content(html, page, config, files, **kwargs):
    terms = _definitions()
    if not terms:
        return html

    # Rebuild the page around its <pre> blocks, transforming only what's between them.
    out = []
    cursor = 0
    for block in PRE_BLOCK.finditer(html):
        out.append(_wrap(html[cursor : block.start()], terms))
        out.append(block.group(0))
        cursor = block.end()
    out.append(_wrap(html[cursor:], terms))
    return "".join(out)
