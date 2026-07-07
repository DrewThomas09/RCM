"""Drug reference & NDC→RxCUI crosswalk — /rxnorm.

A working surface over the RxNorm vertical slice: crosswalk + class-coverage
KPIs, a live NDC resolver (paste any NDC format → RxCUI + concept + classes), a
concept/name search and RxCUI deep-dive (relations, drug classes, NDCs, the
molecule's competitive set), a drug-class explorer that sizes a target's
competitive set by therapeutic class or mechanism, and a retired/remapped audit
that proves stale codes resolve forward.

Why it matters for diligence: NDC→RxCUI is the spine that ties NDC-keyed records
(recalls, adverse events, drug spend) back to one molecule; RxClass grouping
sizes the competitive set; historystatus handling stops retired codes from
silently dropping joins.

Reads only from the RxNorm tables (no network at render). If the tables are
empty, the page offers a one-click 'populate from offline seed' action so it is
useful out of the box. Every user-supplied string is escaped before HTML.

Rendered in the v5 chartis editorial language: ck_editorial_head masthead,
ck_kpi_block strip, ck_data_cell/ck_data_table tables, ck_signal_badge status
chips, ck_empty_state / ck_affirm_empty for the no-data and clean-audit
surfaces. Page-scoped styling lives in one ``_RX_CSS`` class block (no inline
``style=`` attributes) so the kit's CSS custom properties stay the single
source of color truth.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _urlparse
from typing import Any, Dict, List, Optional, Sequence, Tuple

from rcm_mc.data_public.rxnorm import analytics, registry, validation
from rcm_mc.data_public.rxnorm import query as rxquery
from rcm_mc.data_public.rxnorm import store as rxstore
from rcm_mc.ui._chart_kit import ck_hbar_chart
from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_action_button,
    ck_affirm_empty,
    ck_data_cell,
    ck_data_table,
    ck_editorial_head,
    ck_empty_state,
    ck_fmt_number,
    ck_kpi_block,
    ck_page_actions,
    ck_panel,
    ck_provenance_tooltip,
    ck_section_header,
    ck_signal_badge,
    ck_source_purpose,
)


def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))


# Page-scoped classes. Every color is a kit CSS custom property with its
# canonical fallback — no ad-hoc hexes. Focus-visible outlines cover the
# inputs, selects, buttons and pills (impossible with inline styles).
_RX_CSS = (
    '<style>'
    '.rx-form{display:flex;flex-wrap:wrap;gap:8px;align-items:center;'
    'margin:2px 0 18px;}'
    '.rx-form label{font:500 10.5px/1 var(--sc-mono,monospace);'
    'letter-spacing:.12em;text-transform:uppercase;'
    'color:var(--sc-text-dim,#465366);}'
    '.rx-form input[type=text],.rx-form select{padding:7px 10px;'
    'border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;'
    'background:#fff;color:var(--sc-text,#1a2332);'
    'font-family:var(--sc-sans,sans-serif);font-size:12.5px;}'
    '.rx-form input[type=text]{width:340px;max-width:90%;}'
    '.rx-form input[type=text]:focus-visible,.rx-form select:focus-visible,'
    '.rx-form button:focus-visible,.rx-pill:focus-visible,'
    'a.rx-link:focus-visible{outline:2px solid var(--sc-teal,#155752);'
    'outline-offset:1px;}'
    'a.rx-link{color:var(--sc-teal,#155752);}'
    '.rx-lede{font:400 15px/1.6 var(--sc-serif,serif);'
    'color:var(--ink-2,#2b3e54);max-width:64ch;margin:0 0 8px;}'
    '.rx-lede em{color:var(--green-deep,#154e36);font-style:italic;}'
    '.rx-detail{font-size:13px;color:var(--sc-text,#1a2332);margin:4px 0;}'
    '.rx-detail-name{font:400 19px/1.3 var(--sc-serif,serif);'
    'color:var(--sc-navy,#0b2341);margin:0;}'
    '.rx-meta{font-family:var(--sc-mono,monospace);font-size:11px;'
    'color:var(--sc-text-dim,#465366);margin:4px 0 0;}'
    '.rx-note{font-family:var(--sc-mono,monospace);font-size:10.5px;'
    'letter-spacing:.04em;color:var(--sc-text-faint,#7a8699);'
    'margin:6px 0 24px;}'
    '.rx-callout{border:1px solid var(--sc-rule,#c9c1ac);'
    'border-left:3px solid var(--sc-rule-2,#bfb6a2);'
    'background:var(--sc-bone,#ece5d6);border-radius:2px;padding:10px 14px;'
    'max-width:640px;color:var(--sc-text-dim,#465366);font-size:12.5px;'
    'margin:4px 0 16px;}'
    '.rx-callout.warn{border-left-color:var(--sc-negative,#b5321e);'
    'color:var(--sc-negative,#b5321e);background:#fff;}'
    '.rx-seg-l{color:var(--sc-teal,#155752);}'
    '.rx-seg-p{color:var(--sc-warning,#b8732a);}'
    '.rx-seg-k{color:var(--sc-navy,#0b2341);}'
    '.rx-pill{display:inline-flex;align-items:center;gap:6px;'
    'padding:5px 11px;font-family:var(--sc-mono,monospace);font-size:10.5px;'
    'letter-spacing:.06em;text-transform:uppercase;font-weight:600;'
    'background:#fff;color:var(--sc-text,#1a2332);'
    'border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;'
    'text-decoration:none;}'
    '.rx-pill:hover{border-color:var(--sc-teal,#155752);'
    'color:var(--sc-teal,#155752);}'
    '.rx-export-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;'
    'margin:14px 0 26px;}'
    '.rx-export-label{font:500 10.5px/1 var(--sc-mono,monospace);'
    'letter-spacing:.14em;text-transform:uppercase;'
    'color:var(--sc-text-faint,#7a8699);margin-right:4px;}'
    '.rx-chip-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;'
    'margin:2px 0 12px;font-size:12.5px;}'
    '.rx-pager{display:flex;gap:16px;align-items:center;'
    'font-family:var(--sc-mono,monospace);font-size:11px;'
    'color:var(--sc-text-dim,#465366);margin:8px 0 2px;}'
    'th.rx-sort a{color:var(--sc-teal,#155752);text-decoration:none;}'
    'th.rx-sort a:hover{text-decoration:underline;}'
    '.rx-seed-form{display:flex;justify-content:center;'
    'margin:-6px auto 30px;max-width:640px;}'
    '</style>'
)

# Keys every tool form carries forward so resolving an NDC while a search /
# RxCUI detail / class drill-down / dataset view is open doesn't silently
# reset the rest of the page.
_STATE_KEYS = ("ndc", "q", "rxcui", "class_type", "class_id", "dataset",
               "sort", "desc", "ds_page")


def _hidden_state(params: Dict[str, str], *skip: str) -> str:
    """Emit hidden inputs for every active query param a form doesn't own."""
    out: List[str] = []
    for k in _STATE_KEYS:
        if k in skip:
            continue
        v = (params.get(k) or "").strip()
        if v:
            out.append(f'<input type="hidden" name="{k}" '
                       f'value="{_html.escape(v)}"/>')
    return "".join(out)


def _rx_href(**kw: Any) -> str:
    """Build an attribute-safe /rxnorm href.

    URL-encodes each value (defense in depth on top of the upstream
    dataset/sort whitelisting) and HTML-escapes the result for the
    attribute context.
    """
    pairs = {k: str(v) for k, v in kw.items()
             if v is not None and str(v) != ""}
    qs = _urlparse.urlencode(pairs)
    return _html.escape(f"/rxnorm?{qs}" if qs else "/rxnorm")


_STATUS_TONE = {"active": "positive", "retired": "negative",
                "remapped": "warning"}


def _status_badge(status: str) -> str:
    return ck_signal_badge(status or "—",
                           tone=_STATUS_TONE.get(status, "neutral"))


def _td(html_val: str, align: str = "left", mono: bool = False,
        tone: Optional[str] = None) -> str:
    return ck_data_cell(html_val, align=align, mono=mono, tone=tone)


def _table(headers: Sequence[Tuple[str, ...]], rows_html: str) -> str:
    cols = [{"label": h[0], "align": (h[1] if len(h) > 1 else "left")}
            for h in headers]
    return ck_data_table(headers=cols, rows_html=rows_html)


def _section(title: str, sub: str = "", *, count: Optional[int] = None,
             anchor: str = "") -> str:
    anchor_html = (f'<span id="{_html.escape(anchor)}"></span>'
                   if anchor else "")
    return anchor_html + ck_section_header(title, eyebrow=(sub or None),
                                           count=count)


def _callout(html_msg: str, *, tone: str = "muted") -> str:
    cls = "rx-callout warn" if tone == "warn" else "rx-callout"
    return f'<div class="{cls}">{html_msg}</div>'


# ── tools ───────────────────────────────────────────────────────────────────

def _ndc_tool(store: Any, ndc: str, params: Dict[str, str]) -> str:
    box = (
        '<form method="get" action="/rxnorm" class="rx-form">'
        + _hidden_state(params, "ndc")
        + '<input type="text" name="ndc" aria-label="NDC code" '
        'placeholder="Paste any NDC (e.g. 0409-1896-20 or 00409189620)" '
        f'value="{_html.escape(ndc)}"/>'
        + ck_action_button("Resolve")
        + '</form>'
    )
    if not ndc:
        return box
    res = rxquery.lookup_ndc(store, ndc)
    if res.get("error"):
        return box + _callout(
            f'Could not normalize {_html.escape(ndc)}: '
            f'{_html.escape(res["error"])}', tone="warn")
    ndc_11 = res.get("ndc_11") or ""
    match = res.get("match")
    if not match:
        return box + _callout(
            f'Normalized to <code class="mn">{_html.escape(ndc_11)}</code> — '
            f'no crosswalk row. (Resolve live or populate the seed to extend '
            f'coverage.)')
    rxcui = match.get("current_rxcui", match.get("rxcui", ""))
    seg = (f'<span class="rx-seg-l">{_html.escape(ndc_11[:5])}</span>-'
           f'<span class="rx-seg-p">{_html.escape(ndc_11[5:9])}</span>-'
           f'<span class="rx-seg-k">{_html.escape(ndc_11[9:])}</span>')
    card = (
        f'<p class="rx-detail">Canonical NDC-11: '
        f'<code class="mn">{_html.escape(ndc_11)}</code> '
        f'(raw <code class="mn">{_html.escape(match.get("ndc_raw", ""))}'
        f'</code>)</p>'
        f'<p class="rx-meta">5-4-2 segments: {seg} '
        '<span class="rx-seg-l">labeler</span>&middot;'
        '<span class="rx-seg-p">product</span>&middot;'
        '<span class="rx-seg-k">package</span></p>'
        f'<p class="rx-detail">RxCUI '
        f'<a class="rx-link" href="{_rx_href(rxcui=rxcui)}">'
        f'{_html.escape(rxcui)}</a> &middot; '
        f'<strong>{_html.escape(match.get("current_name", ""))}</strong> '
        f'{_status_badge(match.get("status", ""))}</p>'
    )
    return box + ck_panel(card, title="NDC resolved", code="XWALK")


def _search_tool(store: Any, q: str, params: Dict[str, str]) -> str:
    box = (
        '<form method="get" action="/rxnorm" class="rx-form">'
        + _hidden_state(params, "q")
        + '<input type="text" name="q" aria-label="Drug name" '
        'placeholder="Search a drug name (e.g. atorvastatin)" '
        f'value="{_html.escape(q)}"/>'
        + ck_action_button("Search")
        + '</form>'
    )
    if not q:
        return box
    hits = analytics.search_concepts(store, q, limit=15)
    if not hits:
        return box + _callout(f'No concept matches “{_html.escape(q)}”.')
    rows = "".join(
        '<tr>'
        + _td(f'<a class="rx-link" href="{_rx_href(rxcui=h["rxcui"])}">'
              f'{_html.escape(h["rxcui"])}</a>', mono=True)
        + _td(_html.escape(h["name"]))
        + _td(_html.escape(h["tty"]), mono=True)
        + _td(_status_badge(h["status"]), "center")
        + '</tr>'
        for h in hits
    )
    return box + _table(
        [("RxCUI", "left"), ("Name", "left"), ("TTY", "left"),
         ("Status", "center")], rows)


def _rxcui_detail(store: Any, rxcui: str) -> str:
    detail = rxquery.lookup_rxcui(store, rxcui)
    resolved = detail.get("resolved")
    if not resolved:
        return _callout(f'RxCUI {_html.escape(rxcui)} not found in the '
                        f'concept universe.', tone="warn")
    comp = analytics.molecule_competitive_set(store, rxcui)
    head = (
        f'<p class="rx-detail-name">{_html.escape(resolved.get("name", ""))} '
        f'{_status_badge(resolved.get("status", ""))}</p>'
        f'<p class="rx-meta">RxCUI {_html.escape(resolved.get("rxcui", ""))} '
        f'&middot; TTY {_html.escape(resolved.get("tty", ""))} &middot; '
        f'{ck_fmt_number(comp["ndc_count"])} NDC(s) &middot; '
        f'{ck_fmt_number(comp["brand_count"])} brand(s) &middot; '
        f'{ck_fmt_number(comp["branded_drug_count"])} branded / '
        f'{ck_fmt_number(comp["clinical_drug_count"])} clinical drugs</p>'
    )
    header = ck_panel(head, title="RxCUI detail", code="CONCEPT")
    # drug classes
    cls = detail.get("drug_classes", [])
    cls_rows = "".join(
        '<tr>' + _td(_html.escape(c["class_type"]), mono=True)
        + _td(_html.escape(c["class_name"] or c["class_id"]))
        + _td(_html.escape(c["class_id"]), mono=True) + '</tr>'
        for c in cls
    )
    cls_tbl = (_table([("Type",), ("Class",), ("Class ID",)], cls_rows)
               if cls else _callout("No drug-class grouping."))
    # related / competitive set
    rel_rows = ""
    n_rel = 0
    for rel, members in sorted(comp["by_relationship"].items()):
        for m in members:
            n_rel += 1
            rel_rows += (
                '<tr>' + _td(_html.escape(rel), mono=True)
                + _td(f'<a class="rx-link" '
                      f'href="{_rx_href(rxcui=m["related_rxcui"])}">'
                      f'{_html.escape(m.get("name") or m["related_rxcui"])}'
                      f'</a>')
                + _td(_html.escape(m.get("tty") or ""), mono=True) + '</tr>')
    rel_tbl = (_table([("Relationship",), ("Concept",), ("TTY",)], rel_rows)
               if rel_rows else _callout("No related concepts recorded."))
    return (header
            + _section("Drug classes",
                       "ATC / therapeutic / mechanism of action",
                       count=len(cls) or None)
            + cls_tbl
            + _section("Competitive set", "concepts sharing this molecule",
                       count=n_rel or None)
            + rel_tbl)


def _class_explorer(store: Any, class_type: str, class_id: str,
                    params: Dict[str, str]) -> str:
    if class_id:
        members = analytics.class_members(store, class_id, limit=100)
        rows = "".join(
            '<tr>'
            + _td(f'<a class="rx-link" href="{_rx_href(rxcui=m["rxcui"])}">'
                  f'{_html.escape(m["rxcui"])}</a>', mono=True)
            + _td(_html.escape(m.get("name") or ""))
            + _td(_html.escape(m.get("tty") or ""), mono=True)
            + _td(_status_badge(m.get("status") or ""), "center") + '</tr>'
            for m in members
        )
        body = (_table([("RxCUI",), ("Name",), ("TTY",), ("Status", "center")],
                       rows)
                if members else _callout("No members for that class."))
        chip = ('<p class="rx-chip-row">'
                + ck_signal_badge(f"Class {class_id}", tone="neutral")
                + f'<span class="rx-meta">{ck_fmt_number(len(members))} '
                f'molecule(s)</span>'
                '<a class="rx-link" href="/rxnorm">clear</a></p>')
        return chip + body
    # filter first, then the ranked chart, then the class table — the
    # control that scopes the chart should sit above it.
    filt = (
        '<form method="get" action="/rxnorm" class="rx-form">'
        + _hidden_state(params, "class_type", "class_id")
        + '<label for="rx-class-type">Class type</label>'
        '<select id="rx-class-type" name="class_type" '
        'onchange="this.form.submit()">'
        + "".join(
            f'<option value="{v}"{" selected" if class_type == v else ""}>'
            f'{lbl}</option>'
            for v, lbl in (("", "All"), ("ATC", "ATC"),
                           ("therapeutic", "Therapeutic"),
                           ("mechanism_of_action", "Mechanism of action")))
        + '</select>'
        + ck_action_button("Apply")
        + '</form>'
    )
    classes = analytics.competitive_set_by_class(
        store, class_type=class_type, limit=25)
    rows = "".join(
        '<tr>'
        + _td(_html.escape(c["class_type"]), mono=True)
        + _td(f'<a class="rx-link" href="{_rx_href(class_id=c["class_id"])}">'
              f'{_html.escape(c["class_name"] or c["class_id"])}</a>')
        + _td(_html.escape(c["class_id"]), mono=True)
        + _td(ck_fmt_number(c["n_rxcui"]), "right", mono=True) + '</tr>'
        for c in classes
    )
    tbl = (_table([("Type",), ("Class",), ("Class ID",),
                   ("Molecules", "right")], rows)
           if classes else _callout("No drug-class rows yet."))
    return filt + _top_class_chart(store, class_type) + tbl


def _audit_table(audit: List[Dict[str, Any]]) -> str:
    if not audit:
        return ck_affirm_empty(
            headline="No retired or remapped concepts — clean universe.",
            body="Every code in the concept universe is active; nothing "
                 "re-keys forward, so no NDC-keyed join can silently drop "
                 "rows on a stale code.")
    rows = "".join(
        '<tr>' + _td(_html.escape(a["rxcui"]), mono=True)
        + _td(_html.escape(a.get("name") or ""))
        + _td(_status_badge(a.get("status") or ""), "center")
        + _td(_html.escape(a.get("remapped_to_rxcui") or "—"), mono=True)
        + _td(_html.escape(a.get("resolves_to_name") or "—")
              + (" " + _status_badge(a["resolves_to_status"])
                 if a.get("resolves_to_status") else "")) + '</tr>'
        for a in audit
    )
    return _table(
        [("RxCUI",), ("Name",), ("Status", "center"), ("Remaps to",),
         ("Resolves to (active)",)], rows)


def _dataset_browser(store: Any, dataset: str, sort: str, desc: bool,
                     page: int, params: Dict[str, str]) -> str:
    """Paginated, sortable browser over any registered dataset.

    Exercises the uniform query contract (filter/select/sort/paginate)
    directly: the caller never sees RxNav's native shape, only the flat
    envelope.
    """
    ids = registry.dataset_ids()
    if dataset not in ids:
        dataset = ids[0]
    per_page = 15
    offset = max(0, page) * per_page
    try:
        res = rxquery.query_dataset(store, dataset, sort=sort or None,
                                    descending=desc, limit=per_page,
                                    offset=offset)
    except (ValueError, KeyError):
        res = rxquery.query_dataset(store, dataset, limit=per_page,
                                    offset=offset)
        sort = ""
    cols = list(res["rows"][0].keys()) if res["rows"] else []

    # dataset selector — labeled, with a keyboard-reachable Apply fallback
    # beside the auto-submit onchange.
    sel = ('<form method="get" action="/rxnorm" class="rx-form">'
           + _hidden_state(params, "dataset", "ds_page", "sort", "desc")
           + '<input type="hidden" name="ds_page" value="0"/>'
           '<label for="rx-dataset">Dataset</label>'
           '<select id="rx-dataset" name="dataset" '
           'onchange="this.form.submit()">'
           + "".join(
               f'<option value="{_html.escape(d)}"'
               f'{" selected" if d == dataset else ""}>'
               f'{_html.escape(d)}</option>'
               for d in ids)
           + '</select>'
           + ck_action_button("Apply")
           + '</form>')

    def _sort_th(col: str) -> str:
        is_cur = (sort == col)
        nd = (not desc) if is_cur else False
        arrow = (" ▲" if (is_cur and not desc) else
                 " ▼" if (is_cur and desc) else "")
        aria = ("ascending" if (is_cur and not desc) else
                "descending" if is_cur else "none")
        href = _rx_href(dataset=dataset, sort=col,
                        desc="1" if nd else "0", ds_page=0)
        return (f'<th scope="col" class="ck-cell ck-data-table-head rx-sort" '
                f'aria-sort="{aria}">'
                f'<a href="{href}">{_html.escape(col)}{arrow}</a></th>')

    head = "".join(_sort_th(c) for c in cols)
    body_rows = "".join(
        '<tr>' + "".join(
            _td(_html.escape(str(r.get(c, ""))), mono=(c in (
                "rxcui", "ndc_11", "class_id", "related_rxcui")))
            for c in cols) + '</tr>'
        for r in res["rows"])
    table = (
        '<div class="ck-data-table-scroll">'
        f'<table class="ck-data-table"><thead><tr>{head}</tr></thead>'
        f'<tbody>{body_rows}</tbody></table></div>'
    ) if cols else _callout("No rows for that dataset.")

    total = res["total"]
    shown_lo = offset + 1 if res["count"] else 0
    shown_hi = offset + res["count"]
    nav = []
    if page > 0:
        prev_href = _rx_href(dataset=dataset, sort=sort,
                             desc="1" if desc else "0", ds_page=page - 1)
        nav.append(f'<a class="rx-link" href="{prev_href}">&larr; prev</a>')
    if shown_hi < total:
        next_href = _rx_href(dataset=dataset, sort=sort,
                             desc="1" if desc else "0", ds_page=page + 1)
        nav.append(f'<a class="rx-link" href="{next_href}">next &rarr;</a>')
    pager = ('<p class="rx-pager">'
             f'<span>{ck_fmt_number(shown_lo)}–{ck_fmt_number(shown_hi)} of '
             f'{ck_fmt_number(total)}</span>'
             + "".join(nav) + '</p>')
    # target table + API path demoted to a mono provenance line under the
    # table — reference for tooling, not headline furniture.
    note = ('<p class="rx-note">Source: '
            f'<code>{_html.escape(res["target_table"])}</code> &middot; '
            f'GET /api/rxnorm &middot; /v1/query/{_html.escape(dataset)}</p>')
    return sel + table + pager + note


def _registry_table(reg_rows: List[Dict[str, Any]]) -> str:
    rows = "".join(
        '<tr>' + _td(_html.escape(r["dataset_id"]), mono=True)
        + _td(_html.escape(r["endpoint"]), mono=True)
        + _td(_html.escape(r["target_table"]), mono=True)
        + _td(_html.escape(r["refresh_cadence"]))
        + _td(_html.escape(", ".join(r["join_keys"])), mono=True) + '</tr>'
        for r in reg_rows
    )
    return _table(
        [("Dataset",), ("Endpoint",), ("Target table",), ("Cadence",),
         ("Join keys",)], rows)


def _seed_prompt() -> str:
    # ck_empty_state's CTA is an <a href>, but seeding is a POST — keep the
    # form (test-pinned action="/rxnorm/seed") as a kit-styled submit row
    # directly under the card.
    return (
        ck_empty_state(
            "No RxNorm data loaded yet",
            body="The RxNorm reference tables haven't been loaded yet — "
                 "populate them from the bundled offline seed (no network "
                 "required) to explore the drug ontology, NDC crosswalk and "
                 "drug classes.",
            eyebrow="OFFLINE SEED",
            icon="⚕",
        )
        + '<form method="post" action="/rxnorm/seed" class="rx-seed-form">'
        + ck_action_button("Populate from offline seed")
        + '</form>'
    )


def _top_class_chart(store: Any, class_type: str) -> str:
    """Ranked bar chart of drug classes by competitive-set size."""
    rows = analytics.competitive_set_by_class(store, class_type=class_type,
                                              limit=12)
    if not rows:
        return ""
    tone_by_type = {"ATC": "teal", "therapeutic": "navy",
                    "mechanism_of_action": "amber"}
    items = [(f'{r["class_name"] or r["class_id"]}', r["n_rxcui"],
              tone_by_type.get(r["class_type"], "muted")) for r in rows]
    return ck_hbar_chart(
        "Largest competitive sets by drug class",
        items,
        value_fmt=lambda v: f"{int(v)}",
        subtitle="Distinct molecules grouped under each class — bigger bar = "
                 "more crowded competitive set",
        source="RxClass (ATC / therapeutic / mechanism of action) via RxNav.",
        label_w=180.0,
    )


def _openfda_quality_panel(store: Any) -> str:
    """Crosswalk-quality panel: how well the crosswalk joins to openFDA NDCs."""
    rep = validation.openfda_ndc_match_rate(store)
    pct = rep.get("match_rate", 0) * 100
    sample = ", ".join(_html.escape(s)
                       for s in rep.get("unmatched_sample", [])[:6])
    body = (
        f'<p class="rx-lede"><em>Joins are the product —</em> of '
        f'<strong>{ck_fmt_number(rep.get("normalizable", 0))}</strong> '
        f'openFDA drug-shortage NDCs, '
        f'<strong>{ck_fmt_number(rep.get("matched", 0))}</strong> resolve '
        f'through the crosswalk (<strong>{pct:.1f}%</strong> match rate); '
        f'{ck_fmt_number(rep.get("unnormalizable", 0))} were '
        f'unnormalizable.</p>'
        + (f'<p class="rx-meta">Unmatched sample (extend coverage via a live '
           f'pull): <code>{sample}</code></p>' if sample else "")
        + '<p class="rx-note">Read-only join against openFDA’s vendored '
          'drug-shortage snapshot (package_ndc). Match rate scales with '
          'crosswalk breadth.</p>'
    )
    return ck_panel(body, title="Crosswalk coverage vs openFDA",
                    code="OPENFDA")


# ── CSV export ──────────────────────────────────────────────────────────────

_EXPORT_TABLES = {
    "crosswalk": ("xwalk_ndc_rxcui",
                  ["ndc_11", "ndc_raw", "rxcui", "status"]),
    "concepts": ("dim_rxnorm_concept",
                 ["rxcui", "name", "tty", "status", "remapped_to_rxcui"]),
    "classes": ("dim_drug_class",
                ["rxcui", "class_id", "class_name", "class_type"]),
}


def build_export_df(store: Any, table: str):
    """Build a pandas DataFrame for a named export table (CSV download).

    ``table`` is one of crosswalk|concepts|classes|audit. Unknown names raise
    KeyError so the route returns a clean 404 rather than guessing.
    """
    import pandas as pd
    if table == "audit":
        rows = analytics.retired_remapped_audit(store, limit=1000)
        return pd.DataFrame(rows, columns=[
            "rxcui", "name", "status", "remapped_to_rxcui",
            "resolves_to_rxcui", "resolves_to_name", "resolves_to_status"])
    tbl, cols = _EXPORT_TABLES[table]
    with store.connect() as con:
        rxstore.ensure_tables(con)
        rows = con.execute(
            f"SELECT {', '.join(cols)} FROM {tbl} ORDER BY 1").fetchall()
    return pd.DataFrame([dict(r) for r in rows], columns=cols)


def _export_pills() -> str:
    return "".join(
        f'<a class="rx-pill" href="/rxnorm/export.csv?table={t}">{t}.csv</a>'
        for t in ("crosswalk", "concepts", "classes", "audit"))


# ── JSON API ────────────────────────────────────────────────────────────────

def build_rxnorm(store: Any, params: Optional[Dict[str, str]] = None
                 ) -> Dict[str, Any]:
    """JSON payload for /api/rxnorm — summary + any requested lookup."""
    params = params or {}
    out: Dict[str, Any] = {"summary": analytics.coverage_summary(store),
                           "datasets": registry.dataset_rows()}
    if params.get("ndc"):
        out["ndc_lookup"] = rxquery.lookup_ndc(store, params["ndc"])
    if params.get("rxcui"):
        out["rxcui_lookup"] = rxquery.lookup_rxcui(store, params["rxcui"])
        out["competitive_set"] = analytics.molecule_competitive_set(
            store, params["rxcui"])
    if params.get("q"):
        out["search"] = analytics.search_concepts(store, params["q"])
    out["top_classes"] = analytics.competitive_set_by_class(
        store, class_type=params.get("class_type", ""),
        limit=_clamp_int(params.get("limit"), 1, 100, 25))
    return out


# ── page ────────────────────────────────────────────────────────────────────

def _masthead(summary: Dict[str, Any]) -> str:
    counts = summary["counts"]
    cov_pct = float(summary["class_coverage"].get("coverage_pct", 0) or 0)
    meta = (f"{ck_fmt_number(counts.get('dim_rxnorm_concept', 0))} concepts "
            f"· {ck_fmt_number(counts.get('xwalk_ndc_rxcui', 0))} NDCs · "
            f"{cov_pct:.1f}% class coverage")
    return ck_editorial_head(
        "DRUGS · /RXNORM",
        "Drug reference &amp; NDC&rarr;RxCUI crosswalk",
        meta=meta,
        lede_italic_phrase="One molecule, one key —",
        lede_body="the NDC&rarr;RxCUI crosswalk ties recalls, adverse events "
                  "and drug spend back to a single concept; RxClass sizes "
                  "the competitive set; the retired/remapped audit keeps "
                  "stale codes from silently dropping joins.",
        source_note="NLM RxNorm / RxNav REST API (public) · offline seed "
                    "when the API is unreachable",
    ) + ck_source_purpose(
        purpose="Normalize drug names/NDCs to RxNorm concepts and resolve the "
                "NDC→RxCUI crosswalk other drug data joins to.",
        universe="research",
        source="NLM RxNorm / RxNav REST API (public). Offline seed when the "
               "API is unreachable.",
    )


def _kpi_strip(summary: Dict[str, Any]) -> str:
    counts = summary["counts"]
    cov = summary["class_coverage"]
    join = summary["openfda_join"]
    cov_pct = float(cov.get("coverage_pct", 0) or 0)
    cov_value = ck_provenance_tooltip(
        "Class coverage",
        f'<span class="mn">{cov_pct:.1f}%</span>',
        explainer="Share of RxNorm concepts carrying at least one RxClass "
                  "grouping (ATC, therapeutic or mechanism of action): "
                  "classified concepts ÷ concept universe.")
    join_rate = float(join.get("match_rate", 0) or 0)
    join_value = ck_provenance_tooltip(
        "openFDA join",
        f'<span class="mn">{join_rate * 100:.1f}%</span>',
        explainer="Share of normalizable openFDA drug-shortage NDCs that "
                  "resolve through the NDC→RxCUI crosswalk. The crosswalk-"
                  "coverage panel below lists an unmatched sample.",
        inject_css=False)
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Concepts",
            f'<span class="mn">'
            f'{ck_fmt_number(counts.get("dim_rxnorm_concept", 0))}</span>',
            "distinct RxNorm concepts")
        + ck_kpi_block(
            "NDC crosswalk",
            f'<span class="mn">'
            f'{ck_fmt_number(counts.get("xwalk_ndc_rxcui", 0))}</span>',
            f'{ck_fmt_number(summary["rxcui_with_ndc"])} molecules carry '
            f'an NDC')
        + ck_kpi_block(
            "Class coverage", cov_value,
            f'{ck_fmt_number(cov.get("classified_rxcui", 0))} classified '
            f'concepts')
        + ck_kpi_block(
            "Retired / remapped",
            f'<a class="rx-link mn" href="#rx-audit">'
            f'{ck_fmt_number(summary["retired_or_remapped"])}</a>',
            "stale codes that re-key to an active concept")
        + ck_kpi_block(
            "openFDA join", join_value,
            f'{ck_fmt_number(join.get("matched", 0))}/'
            f'{ck_fmt_number(join.get("normalizable", 0))} NDCs resolve')
        + '</div>'
    )


def render_rxnorm_page(store: Any, params: Optional[Dict[str, str]] = None
                       ) -> str:
    params = params or {}
    ndc = (params.get("ndc") or "").strip()
    rxcui = (params.get("rxcui") or "").strip()
    q = (params.get("q") or "").strip()
    class_type = (params.get("class_type") or "").strip()
    class_id = (params.get("class_id") or "").strip()
    dataset = (params.get("dataset") or "").strip()
    ds_sort = (params.get("sort") or "").strip()
    ds_desc = params.get("desc") == "1"
    ds_page = _clamp_int(params.get("ds_page"), 0, 100000, 0)

    summary = analytics.coverage_summary(store)
    counts = summary["counts"]
    populated = counts.get("dim_rxnorm_concept", 0) > 0
    reg_rows = registry.dataset_rows()
    registry_section = (
        _section("Datasets (registry)",
                 "every reference dataset behind this page — source "
                 "endpoint, refresh cadence and join keys",
                 count=len(reg_rows))
        + _registry_table(reg_rows)
    )

    if not populated:
        body = (
            _RX_CSS
            + _masthead(summary)
            + _seed_prompt()
            + registry_section
            + ck_page_actions()
        )
        return chartis_shell(body, "Drug reference & NDC crosswalk",
                             active_nav="/research",
                             subtitle="RxNorm concepts, NDC crosswalk, "
                                      "drug classes")

    audit_rows = analytics.retired_remapped_audit(store, limit=50)
    export_row = ('<p class="rx-export-row">'
                  '<span class="rx-export-label">Export CSV</span>'
                  + _export_pills() + '</p>')
    body = (
        _RX_CSS
        + _masthead(summary)
        + _kpi_strip(summary)
        + export_row
        + _section("NDC resolver",
                   "paste any NDC format → canonical 11-digit + RxCUI",
                   anchor="rx-ndc")
        + _ndc_tool(store, ndc, params)
        + _section("Concept search",
                   "find a molecule, then drill into its RxCUI",
                   anchor="rx-search")
        + _search_tool(store, q, params)
        + (_rxcui_detail(store, rxcui) if rxcui else "")
        + _section("Drug-class explorer",
                   "size the competitive set by therapeutic class or "
                   "mechanism", anchor="rx-classes")
        + _class_explorer(store, class_type, class_id, params)
        + _section("Retired / remapped audit",
                   "stale codes and the active concept they resolve to",
                   count=len(audit_rows) or None, anchor="rx-audit")
        + _audit_table(audit_rows)
        + _openfda_quality_panel(store)
        + _section("Dataset browser",
                   "uniform filter / sort / paginate over any registered "
                   "dataset", anchor="rx-datasets")
        + _dataset_browser(store, dataset or "rxnorm_concepts", ds_sort,
                           ds_desc, ds_page, params)
        + registry_section
        + ck_page_actions(extras_html=_export_pills())
    )
    return chartis_shell(body, "Drug reference & NDC crosswalk",
                         active_nav="/research",
                         subtitle="RxNorm concepts, NDC crosswalk, "
                                  "drug classes")
