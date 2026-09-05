/* Open links in the page body in a new tab, so following a reference never
 * navigates the reader away from the tutorial they're in.
 *
 * Scope is deliberately the article content (.md-content) only: the header,
 * the left nav, the table of contents and the previous/next footer are the
 * site's own navigation, and new-tabbing those would just spawn stray tabs.
 * In-page anchors (#section, heading permalinks) are left alone for the same
 * reason. `rel="noopener"` is set alongside target for the usual security
 * reason (the opened page can't reach back through window.opener).
 *
 * `document$` fires on first load and again after every instant-navigation
 * swap, so links added by a page change get the treatment too.
 */
document$.subscribe(() => {
  document.querySelectorAll(".md-content a[href]").forEach((link) => {
    const href = link.getAttribute("href");
    if (!href || href.startsWith("#")) return; // in-page jumps stay in place
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  });
});
