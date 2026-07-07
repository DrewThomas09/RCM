"""Saved Charts library — reopen named Chart Builder / Exhibit configs.

A saved chart is a route + query string (the chart IS its URL), so the
library is a gallery of chart-config cards: opening one relinks to the
live page, deleting one posts to the owner-scoped store. Saving happens
on the chart pages themselves via a small POST strip that snapshots
``location.search``.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell,
    ck_arrow_link,
    ck_editorial_head,
    ck_empty_state,
    ck_fmt_number,
    ck_page_actions,
    ck_section_header,
    ck_signal_badge,
)

_ROUTE_LABELS = {"/chart-builder": "Chart", "/exhibit": "Exhibit"}


# ── Page-scoped CSS (gallery grid + chart cards) ──────────────────────
# All colour comes from the kit's canonical CSS custom properties so the
# page tracks the v5 chartis palette; the fallbacks match the shell.
# NOTE: this is RAW css (no <style> wrapper) because chartis_shell wraps
# extra_css in its own <style> tag. A stray inner <style> here double-
# wraps and silently kills the FIRST rule (.sc-gallery's grid), which
# made saved charts stack full-width instead of tiling as a card grid.
_SAVED_CHARTS_CSS = """
.sc-gallery{list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(258px,1fr));gap:14px;}
.sc-card{display:flex;flex-direction:column;gap:9px;
  background:var(--paper-card,#fefcf3);
  border:1px solid var(--sc-rule,#d6cfc0);border-radius:6px;
  padding:15px 16px 12px;position:relative;
  transition:border-color .15s ease,box-shadow .15s ease;}
.sc-card:hover{border-color:var(--green-deep,#154e36);
  box-shadow:inset 3px 0 0 var(--green-deep,#154e36);}
.sc-card-top{display:flex;align-items:center;justify-content:space-between;
  gap:10px;}
.sc-glyph{display:block;flex:none;}
.sc-glyph .g-fill{fill:var(--green-deep,#154e36);}
.sc-glyph .g-fill-2{fill:var(--green-deep,#154e36);opacity:.6;}
.sc-glyph .g-fill-3{fill:var(--green-deep,#154e36);opacity:.32;}
.sc-glyph .g-pane{fill:none;stroke:var(--green-deep,#154e36);
  stroke-width:1.6;opacity:.72;}
.sc-glyph .g-pane-fill{fill:var(--green-deep,#154e36);stroke:none;opacity:.5;}
.sc-card-title{font-family:var(--sc-serif,Georgia,serif);font-size:17px;
  font-weight:600;line-height:1.28;color:var(--ink,#16263a);
  text-decoration:none;display:block;}
.sc-card-title:hover{color:var(--green-deep,#154e36);
  text-decoration:underline;text-decoration-thickness:1px;
  text-underline-offset:2px;}
.sc-card-title:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:2px;border-radius:2px;}
.sc-card-hint{margin:0;font-family:var(--sc-mono,JetBrains Mono,monospace);
  font-size:10px;letter-spacing:.02em;color:var(--sc-text-faint,#7a8699);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;}
.sc-card-foot{display:flex;align-items:center;justify-content:space-between;
  gap:10px;margin-top:auto;padding-top:11px;
  border-top:1px solid var(--sc-rule,#e4ddca);}
.sc-card-date{font-family:var(--sc-mono,JetBrains Mono,monospace);
  font-variant-numeric:tabular-nums;font-size:11px;letter-spacing:.02em;
  color:var(--sc-text-dim,#6a7480);cursor:default;}
.sc-card-actions{display:inline-flex;align-items:center;gap:14px;}
.sc-card-actions .ck-arrow{font-size:10.5px;}
.sc-del{display:inline;margin:0;}
.sc-del-btn{border:none;background:none;padding:0;cursor:pointer;
  font-family:var(--sc-sans,Inter Tight,sans-serif);font-size:10.5px;
  font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--sc-text-faint,#7a8699);}
.sc-del-btn:hover{color:var(--sc-negative,#b5321e);}
.sc-del-btn:focus-visible{outline:2px solid var(--sc-negative,#b5321e);
  outline-offset:2px;border-radius:2px;color:var(--sc-negative,#b5321e);}
.sc-cta-row{display:flex;flex-wrap:wrap;gap:22px;align-items:center;
  margin-top:14px;}
"""

# The save strip embeds on /chart-builder and /exhibit, so its styling
# travels with it (self-contained <style>) rather than living in the
# shell those pages happen to use.
_SAVE_FORM_CSS = """
<style>
.sc-save{display:flex;gap:8px;justify-content:center;align-items:center;
  margin-top:10px;flex-wrap:wrap;}
.sc-save-input{height:28px;border:1px solid var(--sc-rule,#c9c1ac);
  border-radius:5px;padding:0 9px;width:220px;font-size:12px;
  font-family:var(--sc-sans,Inter Tight,sans-serif);color:var(--ink,#16263a);
  background:var(--paper-card,#fefcf3);}
.sc-save-input:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:1px;border-color:var(--green-deep,#154e36);}
.sc-save-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 13px;
  border:1px solid var(--sc-rule,#c9c1ac);border-radius:5px;
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a);
  font-family:var(--sc-sans,Inter Tight,sans-serif);font-size:12px;
  font-weight:600;cursor:pointer;transition:border-color .12s,color .12s;}
.sc-save-btn:hover{border-color:var(--green-deep,#154e36);
  color:var(--green-deep,#154e36);}
.sc-save-btn:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:1px;}
.sc-save-star{color:var(--green-deep,#154e36);}
.sc-save-link{font-family:var(--sc-mono,JetBrains Mono,monospace);
  font-size:11px;letter-spacing:.04em;color:var(--green-deep,#154e36);
  text-decoration:none;}
.sc-save-link:hover{text-decoration:underline;text-underline-offset:2px;}
</style>
"""


def save_chart_form(route: str) -> str:
    """The "save this chart" strip the two chart pages embed — a name
    box + POST. The hidden query_params field is snapshotted from
    ``location.search`` at submit so what's saved is exactly the URL
    being looked at (the CSRF shim patches the POST automatically)."""
    r = html.escape(route, quote=True)
    return (
        _SAVE_FORM_CSS
        + '<form method="post" action="/api/charts/save" class="sc-save" '
        'onsubmit="this.query_params.value='
        'window.location.search.slice(1);">'
        f'<input type="hidden" name="route" value="{r}">'
        '<input type="hidden" name="query_params" value="">'
        '<input type="text" name="title" class="sc-save-input" '
        'aria-label="Chart name" placeholder="Name this chart…" '
        'maxlength="160" required>'
        '<button type="submit" class="sc-save-btn">'
        '<span class="sc-save-star" aria-hidden="true">★</span> Save to '
        'library</button>'
        '<a class="sc-save-link" href="/charts">My saved charts →</a>'
        '</form>')


# ── Card helpers ──────────────────────────────────────────────────────

_CHART_GLYPH = (
    '<svg class="sc-glyph" viewBox="0 0 26 26" width="26" height="26" '
    'aria-hidden="true">'
    '<rect class="g-fill" x="3" y="14" width="5" height="9" rx="1"/>'
    '<rect class="g-fill-2" x="11" y="9" width="5" height="14" rx="1"/>'
    '<rect class="g-fill-3" x="19" y="4" width="5" height="19" rx="1"/>'
    '</svg>'
)
_EXHIBIT_GLYPH = (
    '<svg class="sc-glyph" viewBox="0 0 26 26" width="26" height="26" '
    'aria-hidden="true">'
    '<rect class="g-pane" x="3" y="3" width="9" height="9" rx="1.5"/>'
    '<rect class="g-pane-fill" x="14" y="3" width="9" height="9" rx="1.5"/>'
    '<rect class="g-pane-fill" x="3" y="14" width="9" height="9" rx="1.5"/>'
    '<rect class="g-pane" x="14" y="14" width="9" height="9" rx="1.5"/>'
    '</svg>'
)


def _param_hint(query_params: str) -> str:
    """A one-line mono digest of the saved query string so two charts
    with similar names stay distinguishable without opening both.

    A saved chart IS its query string; surfacing the lead param + a
    count is the cheapest way to tell ``type=pareto`` from
    ``type=column`` at a glance. Returns plain text (escaped by the
    caller)."""
    pairs = [p for p in (query_params or "").split("&") if p]
    if not pairs:
        return "No parameters"
    head = pairs[0]
    if len(head) > 30:
        head = head[:29] + "…"
    if len(pairs) > 1:
        return f"{head} · {len(pairs)} params"
    return head


def _chart_card(c: Dict[str, Any]) -> str:
    """One chart-config card: kind glyph + badge, serif title link, a
    mono query-string hint, and a footer with the saved date + open /
    delete affordances."""
    qp = c.get("query_params", "")
    route = c.get("route", "")
    href = html.escape(route + (f"?{qp}" if qp else ""), quote=True)
    kind = _ROUTE_LABELS.get(route, "Chart")
    glyph = _EXHIBIT_GLYPH if kind == "Exhibit" else _CHART_GLYPH
    title = c.get("title", "")
    title_esc = html.escape(title)
    title_attr = html.escape(title, quote=True)
    created = c.get("created_at", "") or ""
    when = html.escape(created[:10])
    created_attr = html.escape(created, quote=True)
    hint = html.escape(_param_hint(qp))

    # Confirm the destructive delete. Build a JS-safe string first
    # (escape backslash / quote / newline) THEN attribute-escape, so a
    # title carrying a quote can neither break out of the JS string nor
    # the HTML attribute.
    confirm_js = (
        ("Delete “" + title + "”?")
        .replace("\\", "\\\\").replace("'", "\\'")
        .replace("\n", " ").replace("\r", " ")
    )
    onsubmit = html.escape(f"return confirm('{confirm_js}')", quote=True)

    return (
        '<li class="sc-card">'
        '<header class="sc-card-top">'
        f'{glyph}{ck_signal_badge(kind)}'
        '</header>'
        f'<a class="sc-card-title" href="{href}">{title_esc}</a>'
        f'<p class="sc-card-hint">{hint}</p>'
        '<footer class="sc-card-foot">'
        f'<time class="sc-card-date" datetime="{created_attr}" '
        f'title="{created_attr}">{when}</time>'
        '<span class="sc-card-actions">'
        f'{ck_arrow_link("Open", route + (f"?{qp}" if qp else ""))}'
        '<form method="post" action="/api/charts/delete" class="sc-del" '
        f'onsubmit="{onsubmit}">'
        f'<input type="hidden" name="id" value="{int(c["id"])}">'
        f'<button type="submit" class="sc-del-btn" '
        f'aria-label="Delete {title_attr}">Delete</button>'
        '</form>'
        '</span>'
        '</footer>'
        '</li>')


def render_saved_charts_page(
    charts: List[Dict[str, Any]],
    owner: str = "",
    qs: "Optional[Dict[str, Any]]" = None,
) -> str:
    n_exhibit = sum(1 for c in charts if c.get("route") == "/exhibit")
    n_chart = len(charts) - n_exhibit
    counts_meta = (
        f"{ck_fmt_number(len(charts))} SAVED · "
        f"{ck_fmt_number(n_chart)} CHART · "
        f"{ck_fmt_number(n_exhibit)} EXHIBIT"
    )

    if not owner:
        head_meta = "SESSION REQUIRED · SIGN IN TO VIEW"
        content = ck_empty_state(
            "Sign in to keep a chart library",
            "Saved charts are per-user. Sign in, configure a chart on "
            "Chart Builder or Exhibit Composer, and click “★ Save to "
            "library”.",
            eyebrow="CHART LIBRARY",
            icon="★",
            cta_label="Sign in",
            cta_href="/login",
        )
    elif not charts:
        head_meta = counts_meta
        content = (
            ck_empty_state(
                "No saved charts yet",
                "Configure a chart on Chart Builder or Exhibit Composer "
                "and click “★ Save to library” — it reopens from here "
                "exactly as you left it.",
                eyebrow="CHART LIBRARY",
                icon="★",
                cta_label="Open Chart Builder",
                cta_href="/chart-builder",
            )
            + '<nav class="sc-cta-row">'
            + ck_arrow_link("Or open the Exhibit Composer", "/exhibit")
            + '</nav>'
        )
    else:
        head_meta = counts_meta
        cards = "".join(_chart_card(c) for c in charts)
        content = (
            f'<ul class="sc-gallery">{cards}</ul>'
            + ck_section_header("Build something new", eyebrow="KEEP GOING")
            + '<nav class="sc-cta-row">'
            + ck_arrow_link("Open Chart Builder", "/chart-builder")
            + ck_arrow_link("Exhibit Composer", "/exhibit")
            + '</nav>'
        )

    head = ck_editorial_head(
        "RESEARCH · CHART LIBRARY",
        "Saved Charts",
        meta=head_meta,
        # Literal <em> keeps the italic-serif green-deep lede in the
        # page's own source (the chartis cadence anchor) rather than
        # hidden behind a runtime helper wrap.
        lede_body=(
            "<em>A chart is its URL</em> — named Chart Builder and "
            "Exhibit Composer configurations that reopen exactly as you "
            "left them."
        ),
        show_legend=False,
    )

    body = head + content + ck_page_actions()
    return chartis_shell(
        body, "Saved Charts", active_nav="/research",
        subtitle="Chart library", extra_css=_SAVED_CHARTS_CSS)
