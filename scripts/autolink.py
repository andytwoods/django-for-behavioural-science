"""Turn recurring proper nouns into hyperlinks, from one definitions file.

Sister to ``scripts/glossary.py``. That hook gives jargon a tooltip from
``includes/abbreviations.md``; this one gives names a link from ``includes/links.md``,
on the same principle: say it once, and every page gets it.

The alternative is to hand-link each sighting, which goes stale the moment a URL moves
and quietly gets skipped whenever a new paragraph mentions the thing.

Deliberately narrow. A mention is linked only when it is plain prose:

- nothing inside a ``<pre>`` block, so code samples are never touched,
- nothing inside inline ``<code>``, so ``jsPsych.run`` stays code rather than becoming
  a link,
- nothing already inside an ``<a>``, so a hand-written link (with its own, more specific
  URL) wins and links never nest,
- nothing in a heading, where a link would fight the heading's own styling,
- and the match must stand alone as a word: ``jsPsych`` is linked,
  ``jsPsychHtmlKeyboardResponse`` is not.

Wired up via `hooks:` in mkdocs.yml.
"""

import re
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS = REPO_ROOT / "includes" / "links.md"

# Link *every* mention, which is what the tutorial asks for. Set this to False to link
# only the first sighting on each page, the more conventional house style.
EVERY_MENTION = True

# `[jsPsych]: https://www.jspsych.org/`
DEFINITION_LINE = re.compile(r"^\[(?P<term>[^\]]+)\]:\s*(?P<url>\S+)$")

# Elements whose text must be left exactly as it is (see the module docstring).
SKIP = {"a", "pre", "code", "abbr", "script", "style"} | {f"h{n}" for n in range(1, 7)}

# One pass over the rendered page as comments, tags and the text between them.
TOKEN = re.compile(r"<!--.*?-->|<[^>]+>|[^<]+", re.S)
TAG = re.compile(r"<\s*(?P<close>/?)\s*(?P<name>[a-zA-Z][a-zA-Z0-9]*)")


def _definitions():
    """``{term: (url, compiled pattern)}``.

    Read per page rather than cached, so editing the file shows up on the next
    `mkdocs serve` rebuild instead of needing the server restarted. It is a handful of
    lines; the reading costs nothing.
    """
    terms = {}
    if DEFINITIONS.is_file():
        for line in DEFINITIONS.read_text().split("\n"):
            match = DEFINITION_LINE.match(line.strip())
            if match:
                term = match["term"]
                # Word boundaries of our own: \b would happily match the "jsPsych" inside
                # "jsPsychHtmlKeyboardResponse", because the boundary it wants sits
                # between "h" and "H".
                pattern = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(term))
                terms[term] = (match["url"], pattern)
    return terms


def _link(text, terms, seen):
    for term, (url, pattern) in terms.items():
        if not EVERY_MENTION and term in seen:
            continue
        anchor = '<a href="%s">%s</a>' % (escape(url, quote=True), escape(term))
        text, hits = pattern.subn(lambda _: anchor, text, count=0 if EVERY_MENTION else 1)
        if hits:
            seen.add(term)
    return text


def on_page_content(html, page, config, files, **kwargs):
    terms = _definitions()
    if not terms:
        return html

    seen = set()
    out = []
    depth = 0  # how deep we are inside elements from SKIP
    for token in TOKEN.finditer(html):
        chunk = token.group(0)
        if chunk.startswith("<!--"):
            out.append(chunk)
        elif chunk.startswith("<"):
            tag = TAG.match(chunk)
            if tag and tag["name"].lower() in SKIP:
                depth = max(0, depth - 1) if tag["close"] else depth + 1
            out.append(chunk)
        else:
            out.append(chunk if depth else _link(chunk, terms, seen))
    return "".join(out)
