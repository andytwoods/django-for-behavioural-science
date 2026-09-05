/* Toggles for hiding the comments in code blocks: one in the header that acts on
 * the whole site, and one on each block that carries comments.
 *
 * This feature is intentionally self-contained in this one file — it injects its
 * own <style> below rather than relying on extra.css. That keeps all its moving
 * parts together and means a single cache-busting filename change refreshes both
 * behaviour and styling at once.
 *
 * How the hiding works. Pygments already wraps each comment in a span with a
 * `c`-family class, so the hiding itself is one CSS rule. The work in JS is
 * deciding what else goes with the comment: a comment on its own line should
 * take the line's indentation and newline with it (otherwise hiding leaves a
 * blank gap), and a trailing comment should take the whitespace in front of it
 * (otherwise the line keeps a ragged tail). We wrap those runs in marker spans
 * once, at page load.
 *
 * Copying is handled for free: Material's copy button reads `innerText`, which
 * skips `display: none`, so a reader who hides comments copies code without them.
 *
 * State lives in class names, block-level winning over the site-wide default:
 *   body.comments-hidden  - the site-wide default, remembered in localStorage
 *   .highlight.cmt-hide   - this block overrides the default to hidden
 *   .highlight.cmt-show   - this block overrides the default to shown
 * Flipping the header toggle clears every per-block override.
 */

const STORAGE_KEY = "comments-hidden";
const COMMENT_CLASSES = ["c", "c1", "cm", "ch", "cs"];

const isComment = (node) =>
  node.nodeType === Node.ELEMENT_NODE &&
  COMMENT_CLASSES.some((c) => node.classList.contains(c));

/* Indentation reaches us two ways: as a plain text node, or as Pygments'
   <span class="w"> whitespace token. Both count as space in front of a comment. */
const isSpace = (node) =>
  (node.nodeType === Node.TEXT_NODE && !node.nodeValue.trim()) ||
  (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("w"));

/* anchor_linenums puts an empty <a id="__codelineno-..."> at the head of every
   line. It renders nothing, so it must not stop a line counting as comment-only. */
const isLineAnchor = (node) =>
  node.nodeType === Node.ELEMENT_NODE &&
  node.tagName === "A" &&
  !node.textContent;

/* ---------- styles ---------- */

const STYLE_ID = "code-comments-style";

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    body.comments-hidden .highlight:not(.cmt-show) .cmt-line,
    body.comments-hidden .highlight:not(.cmt-show) .cmt-inline,
    .highlight.cmt-hide .cmt-line,
    .highlight.cmt-hide .cmt-inline { display: none; }

    /* We deliberately do NOT reuse Material's .md-code__button class: on top of
       our inline svg it paints its own button icon, which showed up as a solid
       box beside the speech bubble (and squashed the svg). So the button is styled
       from scratch here to sit and fade like the copy button beside it. */
    .md-typeset .highlight .cmt-button {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 1.5em;
      height: 1.5em;
      margin: 0;
      padding: 0;
      border: 0;
      background: transparent;
      cursor: pointer;
      color: var(--md-default-fg-color--lightest);
      transition: color 125ms;
    }
    .md-typeset .highlight:hover .cmt-button,
    .md-typeset .highlight .cmt-button:hover {
      color: var(--md-default-fg-color--light);
    }
    /* Force an outline icon regardless of any theme rule that fills svgs. */
    .cmt-button svg,
    [data-cmt-toggle] svg {
      fill: none !important;
      stroke: currentcolor !important;
      stroke-width: 2px;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    /* The code-block button sizes to its own (16px) em. */
    .cmt-button svg { width: 1.05em; height: 1.05em; }
    /* The header button's em is only 10px, so size the header icon in rem to
       match the other header icons (1.2rem) instead. */
    [data-cmt-toggle] svg { width: 1.2rem; height: 1.2rem; }
    /* With comments hidden site-wide, the block button is the only route back,
       so keep it visible rather than waiting for a hover. */
    body.comments-hidden .md-typeset .highlight .cmt-button {
      color: var(--md-default-fg-color--light);
      opacity: 1;
    }
  `;
  document.head.appendChild(style);
}

/* ---------- marking up the comments ---------- */

/* Split the code element's direct text children so that every newline sits in a
   text node of its own. That makes "one line" a simple run of sibling nodes. */
function isolateNewlines(code) {
  for (const node of [...code.childNodes]) {
    if (node.nodeType !== Node.TEXT_NODE) continue;
    let current = node;
    let index;
    while ((index = current.nodeValue.indexOf("\n")) !== -1) {
      if (index > 0) current = current.splitText(index);
      if (current.nodeValue.length === 1) break;
      current = current.splitText(1);
    }
  }
}

function wrap(nodes, className) {
  if (!nodes.length) return;
  const span = document.createElement("span");
  span.className = className;
  nodes[0].parentNode.insertBefore(span, nodes[0]);
  nodes.forEach((n) => span.appendChild(n));
}

/* Returns true if the block turned out to contain any comments at all. */
function markComments(code) {
  if (!code.dataset.cmtMarked) {
    code.dataset.cmtMarked = "1";
    isolateNewlines(code);

    let line = [];
    const flush = (newline) => {
      const comments = line.filter(isComment);
      if (comments.length) {
        if (line.every((n) => isComment(n) || isSpace(n) || isLineAnchor(n))) {
          // Comment-only line: the whole line goes, newline included. The line
          // anchor stays put — it renders nothing, and keeping it means the ids
          // don't come and go as comments are toggled.
          const body = line.filter((n) => !isLineAnchor(n));
          wrap(newline ? [...body, newline] : body, "cmt-line");
        } else {
          // Trailing comment: take the run from the first comment span back
          // through any whitespace immediately in front of it.
          let start = line.indexOf(comments[0]);
          while (start > 0 && isSpace(line[start - 1])) start--;
          wrap(line.slice(start), "cmt-inline");
        }
      }
      line = [];
    };

    for (const node of [...code.childNodes]) {
      if (node.nodeType === Node.TEXT_NODE && node.nodeValue === "\n") flush(node);
      else line.push(node);
    }
    flush(null);
  }
  return !!code.querySelector(".cmt-line, .cmt-inline");
}

/* ---------- buttons ---------- */

/* Outline (stroked) icons — a speech bubble for "comments showing", the same
   bubble struck through for "comments hidden". */
const ICON_SHOW = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
const ICON_HIDE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M3 3l18 18"/></svg>`;

const globalHidden = () => document.body.classList.contains("comments-hidden");

/* What a given block is actually showing right now. */
const blockHidden = (block) =>
  block.classList.contains("cmt-hide") ||
  (globalHidden() && !block.classList.contains("cmt-show"));

function dressButton(button, hidden, label) {
  button.innerHTML = hidden ? ICON_HIDE : ICON_SHOW;
  const title = (hidden ? "Show" : "Hide") + label;
  button.title = title;
  button.setAttribute("aria-label", title);
  button.setAttribute("aria-pressed", String(hidden));
}

function refresh() {
  const header = document.querySelector("[data-cmt-toggle]");
  if (header) dressButton(header, globalHidden(), " code comments");
  document.querySelectorAll("[data-cmt-block]").forEach((button) => {
    dressButton(button, blockHidden(button.closest(".highlight")), " comments in this block");
  });
}

function setGlobal(hidden) {
  document.body.classList.toggle("comments-hidden", hidden);
  try {
    localStorage.setItem(STORAGE_KEY, String(hidden));
  } catch (e) {
    /* private browsing: the toggle still works, it just won't be remembered */
  }
  // The header toggle is the master switch, so drop any per-block overrides.
  document.querySelectorAll(".highlight").forEach((b) => {
    b.classList.remove("cmt-hide", "cmt-show");
  });
  refresh();
}

function installHeaderButton() {
  if (document.querySelector("[data-cmt-toggle]")) return;
  const palette = document.querySelector("[data-md-component=palette]");
  if (!palette) return;
  const button = document.createElement("button");
  button.className = "md-header__button md-icon";
  button.type = "button";
  button.setAttribute("data-cmt-toggle", "");
  button.addEventListener("click", () => setGlobal(!globalHidden()));
  palette.parentNode.insertBefore(button, palette);
}

/* Material collects a block's controls in .md-code__nav (the copy button lives
   there). Sitting in the same container means we inherit its placement and hover
   behaviour. The nav is built by Material's own subscriber, which may not have
   run yet, so fall back to the block itself. */
function installBlockButton(block) {
  if (block.querySelector("[data-cmt-block]")) return;
  const button = document.createElement("button");
  button.className = "cmt-button";
  button.type = "button";
  button.setAttribute("data-cmt-block", "");
  button.addEventListener("click", () => {
    const hidden = !blockHidden(block);
    block.classList.toggle("cmt-hide", hidden);
    block.classList.toggle("cmt-show", !hidden);
    refresh();
  });
  const nav = block.querySelector(".md-code__nav");
  if (nav) nav.insertBefore(button, nav.firstChild);
  else block.appendChild(button);
}

/* ---------- wiring ---------- */

let stored = false;
try {
  stored = localStorage.getItem(STORAGE_KEY) === "true";
} catch (e) {
  /* ignore */
}

/* `document$` fires on first load and again after every instant-navigation swap. */
document$.subscribe(() => {
  injectStyles();
  document.body.classList.toggle("comments-hidden", stored);
  installHeaderButton();
  document.querySelectorAll(".highlight").forEach((block) => {
    const code = block.querySelector("code");
    if (code && markComments(code)) installBlockButton(block);
  });
  refresh();
});
