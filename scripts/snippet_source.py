"""Put a "source on GitHub" link under every transcluded code block.

Code in this tutorial isn't typed into the markdown; it's pulled out of the answer-key app
by pymdownx.snippets, so a block looks like this in the source:

    ```python
    --8<-- "study/models.py:study-model"
    ```

That keeps the tutorial honest (the snippet is the tested code), but it also means the
reader only ever sees an excerpt. This hook gives them the whole file: it runs over the raw
markdown before conversion, spots those transclusion lines, and appends a link to the file
on GitHub — deep-linked to the exact lines the snippet region covers.

The line numbers are read out of the source file at build time rather than written down
here, so they follow the code around as it's edited and can't go stale.

Wired up via `hooks:` in mkdocs.yml.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# A transclusion line: `--8<-- "study/models.py:study-model"`, the section being optional.
SNIPPET_LINE = re.compile(r'^--8<--\s+"(?P<path>[^":]+)(?::(?P<section>[^"]+))?"\s*$')

# Not every block can be transcluded. Where a chapter shows a deliberately simpler version
# of a file than the finished one (chapter 1's StudyAdmin, say), the code is typed into the
# markdown, and it says where it's headed with a comment on the line above the fence:
#
#     <!-- source: study/admin.py -->
#
# which gets the same link treatment, minus the line range: the block isn't a copy of any
# particular span of the file.
SOURCE_COMMENT = re.compile(r"^<!--\s*source:\s*(?P<path>[^\s:>]+)(?::(?P<section>[^\s>]+))?\s*-->$")

# The markers that bound a named region inside a source file, e.g.
# `# --8<-- [start:study-model]`. The comment character varies with the language.
def _region_markers(section):
    return (
        re.compile(r"--8<--\s+\[start:%s\]" % re.escape(section)),
        re.compile(r"--8<--\s+\[end:%s\]" % re.escape(section)),
    )


def _line_range(path, section):
    """The 1-based lines a snippet region spans, excluding the marker lines themselves."""
    if not section:
        return None
    source = REPO_ROOT / path
    if not source.is_file():
        return None
    start_re, end_re = _region_markers(section)
    start = end = None
    for number, line in enumerate(source.read_text().split("\n"), start=1):
        if start is None and start_re.search(line):
            start = number + 1
        elif start is not None and end_re.search(line):
            end = number - 1
            break
    if start is None or end is None or end < start:
        return None
    return start, end


def _blob_base(config):
    """`https://github.com/owner/repo/blob/<branch>`, with the branch taken from edit_uri.

    edit_uri is `edit/main/docs/`, so its second segment is the branch the docs are built
    from — one place to change if the default branch is ever renamed.
    """
    repo_url = (config.get("repo_url") or "").rstrip("/")
    if not repo_url:
        return None
    parts = (config.get("edit_uri") or "").strip("/").split("/")
    branch = parts[1] if len(parts) > 1 else "main"
    return "%s/blob/%s" % (repo_url, branch)


# The GitHub mark, inlined so the link needs no icon font or network request. Sized and
# coloured from the surrounding text by the `.snippet-source svg` rules in extra.css.
GITHUB_MARK = (
    '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 '
    "2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69"
    "-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 "
    "1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15"
    "-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 "
    "1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 "
    '3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 '
    '8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>'
)


def _link(path, section, config):
    base = _blob_base(config)
    if not base:
        return None
    url = "%s/%s" % (base, path)
    span = _line_range(path, section)
    if span:
        url += "#L%d-L%d" % span
    return (
        '<p class="snippet-source"><a href="%s" title="See this code in the companion '
        'repository">%s%s on GitHub</a></p>' % (url, GITHUB_MARK, path)
    )


def on_page_markdown(markdown, page, config, files, **kwargs):
    out = []
    in_fence = False
    pending = []
    declared = None  # a `<!-- source: ... -->` waiting for its code block
    for line in markdown.split("\n"):
        stripped = line.strip()
        if not in_fence:
            declaration = SOURCE_COMMENT.match(stripped)
            if declaration:
                declared = (declaration["path"], declaration["section"])
                continue  # the comment itself is scaffolding; keep it out of the HTML
            if stripped.startswith("```"):
                in_fence = True
                pending = [declared] if declared else []
                declared = None
            elif stripped:
                declared = None  # anything else between the comment and a block cancels it
            out.append(line)
            continue
        # Inside a fence: a bare ``` closes it, anything else is code.
        if stripped == "```":
            in_fence = False
            out.append(line)
            indent = line[: len(line) - len(line.lstrip())]
            for path, section in pending:
                link = _link(path, section, config)
                if link:
                    out.append(indent + link)
            pending = []
            continue
        match = SNIPPET_LINE.match(stripped)
        if match:
            pending.append((match["path"], match["section"]))
        out.append(line)
    return "\n".join(out)
