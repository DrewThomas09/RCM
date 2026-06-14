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
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from rcm_mc.ui._chart_kit import ck_hbar_chart
from rcm_mc.data_public.rxnorm import (analytics, query as rxquery, registry,
                                       store as rxstore, validation)


def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))


_MONO = "font-family:var(--sc-mono,monospace);"


def _kpi(label: str, val: str, sub: str) -> str:
    return (
        '<div style="flex:1;min-width:130px;border:1px solid var(--sc-rule,#c9c1ac);'
        'background:var(--sc-paper,#faf6ec);padding:10px 14px;border-radius:3px;">'
        f'<div style="{_MONO}font-size:9.5px;letter-spacing:.1em;text-transform:'
        f'uppercase;color:#8b94a0;">{_html.escape(label)}</div>'
        f'<div style="font-family:var(--sc-serif,serif);font-size:24px;'
        f'color:var(--sc-navy,#0b2341);font-variant-numeric:tabular-nums;">{val}</div>'
        f'<div style="font-size:10.5px;color:#6a7480;margin-top:2px;">'
        f'{_html.escape(sub)}</div></div>'
    )


def _th(text: str, align: str = "left") -> str:
    return (f'<th style="padding:6px 10px;text-align:{align};font-size:10px;'
            f'text-transform:uppercase;letter-spacing:.05em;">{_html.escape(text)}</th>')


def _td(html_val: str, align: str = "left", mono: bool = False) -> str:
    m = _MONO if mono else ""
    return (f'<td style="padding:4px 10px;font-size:12px;text-align:{align};{m}">'
            f'{html_val}</td>')


def _table(headers: List, rows_html: str, *, max_width: int = 760) -> str:
    head = "".join(_th(h[0], h[1] if len(h) > 1 else "left") for h in headers)
    return (
        f'<div style="border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        f'overflow:hidden;margin:6px 0 18px;max-width:{max_width}px;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:var(--sc-navy,#0b2341);color:#fff;">'
        f'{head}</tr></thead><tbody>{rows_html}</tbody></table></div>'
    )


def _section(title: str, sub: str = "") -> str:
    s = (f'<div style="font-size:11px;color:#6a7480;margin:2px 0 8px;">'
         f'{_html.escape(sub)}</div>') if sub else ""
    return (
        f'<h2 style="font-family:var(--sc-serif,serif);font-size:18px;'
        f'color:var(--sc-navy,#0b2341);margin:26px 0 2px;border-top:1px solid '
        f'var(--sc-rule,#c9c1ac);padding-top:16px;">{_html.escape(title)}</h2>{s}'
    )


_STATUS_TONE = {
    "active": ("#0a8a5f", "#e7f3ee"),
    "retired": ("#b5321e", "#f7e9e6"),
    "remapped": ("#b8732a", "#f6ede2"),
}


def _status_badge(status: str) -> str:
    fg, bg = _STATUS_TONE.get(status, ("#7a8699", "#eef0f3"))
    return (f'<span style="font-size:9.5px;font-weight:600;color:{fg};'
            f'background:{bg};border-radius:10px;padding:2px 8px;">'
            f'{_html.escape(status or "—")}</span>')


# ── tools ───────────────────────────────────────────────────────────────────

def _ndc_tool(store: Any, ndc: str) -> str:
    box = (
        '<form method="get" action="/rxnorm" style="margin:4px 0 10px;">'
        '<input type="text" name="ndc" placeholder="Paste any NDC '
        '(e.g. 0409-1896-20 or 00409189620)" '
        f'value="{_html.escape(ndc)}" '
        'style="width:340px;max-width:90%;padding:7px 10px;border:1px solid '
        '#c9c1ac;border-radius:3px;font-size:13px;" />'
        '<button type="submit" style="margin-left:8px;padding:7px 16px;'
        'background:#155752;color:#fff;border:none;border-radius:3px;'
        'font-size:12px;cursor:pointer;">Resolve</button></form>'
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
            f'Normalized to <code>{_html.escape(ndc_11)}</code> — no crosswalk '
            f'row. (Resolve live or populate the seed to extend coverage.)',
            tone="muted")
    rxcui = match.get("current_rxcui", match.get("rxcui", ""))
    return box + (
        '<div style="border:1px solid #b9cde6;background:#eef4fb;border-radius:4px;'
        'padding:12px 16px;max-width:560px;">'
        f'<div style="{_MONO}font-size:10px;letter-spacing:.08em;text-transform:'
        f'uppercase;color:#0b2341;margin-bottom:6px;">NDC resolved</div>'
        f'<div style="font-size:13px;">Canonical NDC-11: '
        f'<code style="{_MONO}">{_html.escape(ndc_11)}</code> '
        f'(raw <code style="{_MONO}">{_html.escape(match.get("ndc_raw",""))}</code>)</div>'
        f'<div style="font-size:13px;margin-top:4px;">RxCUI '
        f'<a href="/rxnorm?rxcui={_html.escape(rxcui)}" style="color:#155752;">'
        f'{_html.escape(rxcui)}</a> &middot; '
        f'<strong>{_html.escape(match.get("current_name",""))}</strong> '
        f'{_status_badge(match.get("status",""))}</div></div>'
    )


def _callout(html_msg: str, *, tone: str = "muted") -> str:
    colors = {"muted": ("#6a7480", "#f3eddb"), "warn": ("#b5321e", "#f7e9e6")}
    fg, bg = colors.get(tone, colors["muted"])
    return (f'<div style="border:1px solid {fg}33;background:{bg};border-radius:4px;'
            f'padding:10px 14px;max-width:560px;color:{fg};font-size:12.5px;'
            f'margin:4px 0;">{html_msg}</div>')


def _search_tool(store: Any, q: str) -> str:
    box = (
        '<form method="get" action="/rxnorm" style="margin:4px 0 10px;">'
        '<input type="text" name="q" placeholder="Search a drug name '
        '(e.g. atorvastatin)" '
        f'value="{_html.escape(q)}" '
        'style="width:340px;max-width:90%;padding:7px 10px;border:1px solid '
        '#c9c1ac;border-radius:3px;font-size:13px;" />'
        '<button type="submit" style="margin-left:8px;padding:7px 16px;'
        'background:#155752;color:#fff;border:none;border-radius:3px;'
        'font-size:12px;cursor:pointer;">Search</button></form>'
    )
    if not q:
        return box
    hits = analytics.search_concepts(store, q, limit=15)
    if not hits:
        return box + _callout(f'No concept matches “{_html.escape(q)}”.')
    rows = "".join(
        '<tr>'
        + _td(f'<a href="/rxnorm?rxcui={_html.escape(h["rxcui"])}" '
              f'style="color:#155752;">{_html.escape(h["rxcui"])}</a>', mono=True)
        + _td(_html.escape(h["name"]))
        + _td(_html.escape(h["tty"]), mono=True)
        + _td(_status_badge(h["status"]), "center")
        + '</tr>'
        for h in hits
    )
    return box + _table(
        [("RxCUI", "left"), ("Name", "left"), ("TTY", "left"),
         ("Status", "center")], rows, max_width=620)


def _rxcui_detail(store: Any, rxcui: str) -> str:
    detail = rxquery.lookup_rxcui(store, rxcui)
    resolved = detail.get("resolved")
    if not resolved:
        return _callout(f'RxCUI {_html.escape(rxcui)} not found in the concept '
                        f'universe.', tone="warn")
    comp = analytics.molecule_competitive_set(store, rxcui)
    header = (
        '<div style="border:1px solid #b9cde6;background:#eef4fb;border-radius:4px;'
        'padding:12px 16px;max-width:640px;margin-bottom:10px;">'
        f'<div style="font-family:var(--sc-serif,serif);font-size:18px;'
        f'color:#0b2341;">{_html.escape(resolved.get("name",""))} '
        f'{_status_badge(resolved.get("status",""))}</div>'
        f'<div style="{_MONO}font-size:11px;color:#465366;margin-top:2px;">'
        f'RxCUI {_html.escape(resolved.get("rxcui",""))} &middot; '
        f'TTY {_html.escape(resolved.get("tty",""))} &middot; '
        f'{comp["ndc_count"]} NDC(s) &middot; {comp["brand_count"]} brand(s) &middot; '
        f'{comp["branded_drug_count"]} branded / {comp["clinical_drug_count"]} '
        f'clinical drugs</div></div>'
    )
    # drug classes
    cls = detail.get("drug_classes", [])
    cls_rows = "".join(
        '<tr>' + _td(_html.escape(c["class_type"]), mono=True)
        + _td(_html.escape(c["class_name"] or c["class_id"]))
        + _td(_html.escape(c["class_id"]), mono=True) + '</tr>'
        for c in cls
    )
    cls_tbl = _table([("Type",), ("Class",), ("Class ID",)], cls_rows,
                     max_width=640) if cls else _callout("No drug-class grouping.")
    # related / competitive set
    rel_rows = ""
    for rel, members in sorted(comp["by_relationship"].items()):
        for m in members:
            rel_rows += (
                '<tr>' + _td(_html.escape(rel), mono=True)
                + _td(f'<a href="/rxnorm?rxcui={_html.escape(m["related_rxcui"])}" '
                      f'style="color:#155752;">{_html.escape(m.get("name") or m["related_rxcui"])}</a>')
                + _td(_html.escape(m.get("tty") or ""), mono=True) + '</tr>')
    rel_tbl = _table([("Relationship",), ("Concept",), ("TTY",)], rel_rows,
                     max_width=640) if rel_rows else _callout(
        "No related concepts recorded.")
    return (header
            + _section("Drug classes", "ATC / therapeutic / mechanism of action")
            + cls_tbl
            + _section("Competitive set", "concepts sharing this molecule")
            + rel_tbl)


def _class_explorer(store: Any, class_type: str, class_id: str) -> str:
    if class_id:
        members = analytics.class_members(store, class_id, limit=100)
        rows = "".join(
            '<tr>' + _td(f'<a href="/rxnorm?rxcui={_html.escape(m["rxcui"])}" '
                         f'style="color:#155752;">{_html.escape(m["rxcui"])}</a>', mono=True)
            + _td(_html.escape(m.get("name") or ""))
            + _td(_html.escape(m.get("tty") or ""), mono=True)
            + _td(_status_badge(m.get("status") or ""), "center") + '</tr>'
            for m in members
        )
        body = _table([("RxCUI",), ("Name",), ("TTY",), ("Status", "center")],
                      rows, max_width=640) if members else _callout(
            "No members for that class.")
        return (_callout(f'Class <code>{_html.escape(class_id)}</code> — '
                         f'{len(members)} molecule(s). '
                         f'<a href="/rxnorm" style="color:#155752;">clear</a>')
                + body)
    # ranked classes by competitive-set size
    classes = analytics.competitive_set_by_class(
        store, class_type=class_type, limit=25)
    rows = "".join(
        '<tr>'
        + _td(_html.escape(c["class_type"]), mono=True)
        + _td(f'<a href="/rxnorm?class_id={_html.escape(c["class_id"])}" '
              f'style="color:#155752;">{_html.escape(c["class_name"] or c["class_id"])}</a>')
        + _td(_html.escape(c["class_id"]), mono=True)
        + _td(str(c["n_rxcui"]), "right", mono=True) + '</tr>'
        for c in classes
    )
    filt = (
        '<form method="get" action="/rxnorm" style="margin:4px 0 8px;">'
        '<label style="font-size:11px;color:#6a7480;margin-right:6px;">Class type</label>'
        '<select name="class_type" onchange="this.form.submit()" '
        'style="padding:5px 8px;border:1px solid #c9c1ac;border-radius:3px;font-size:12px;">'
        + "".join(
            f'<option value="{v}"{" selected" if class_type == v else ""}>{lbl}</option>'
            for v, lbl in (("", "All"), ("ATC", "ATC"),
                           ("therapeutic", "Therapeutic"),
                           ("mechanism_of_action", "Mechanism of action")))
        + '</select></form>'
    )
    tbl = _table([("Type",), ("Class",), ("Class ID",), ("Molecules", "right")],
                 rows, max_width=720) if classes else _callout(
        "No drug-class rows yet.")
    return filt + tbl


def _audit_table(store: Any) -> str:
    audit = analytics.retired_remapped_audit(store, limit=50)
    if not audit:
        return _callout("No retired or remapped concepts — clean universe.")
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
         ("Resolves to (active)",)], rows, max_width=820)


def _registry_table() -> str:
    rows = "".join(
        '<tr>' + _td(_html.escape(r["dataset_id"]), mono=True)
        + _td(_html.escape(r["endpoint"]), mono=True)
        + _td(_html.escape(r["target_table"]), mono=True)
        + _td(_html.escape(r["refresh_cadence"]))
        + _td(_html.escape(", ".join(r["join_keys"])), mono=True) + '</tr>'
        for r in registry.dataset_rows()
    )
    return _table(
        [("Dataset",), ("Endpoint",), ("Target table",), ("Cadence",),
         ("Join keys",)], rows, max_width=820)


def _seed_prompt(csrf_hint: bool = True) -> str:
    return (
        '<div style="border:1px dashed #c9a14a;background:#fbf5e6;border-radius:4px;'
        'padding:16px 20px;max-width:620px;margin:10px 0;">'
        '<div style="font-family:var(--sc-serif,serif);font-size:16px;color:#0b2341;">'
        'No RxNorm data loaded yet</div>'
        '<div style="font-size:12.5px;color:#6a7480;margin:6px 0 12px;">'
        'Populate the crosswalk, concepts, relationships and drug classes from '
        'the committed offline seed (no network) to explore the surface.</div>'
        '<form method="post" action="/rxnorm/seed">'
        '<button type="submit" style="padding:8px 18px;background:#155752;'
        'color:#fff;border:none;border-radius:3px;font-size:13px;cursor:pointer;">'
        'Populate from offline seed</button></form></div>'
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


def _openfda_coverage_panel(store: Any) -> str:
    """Crosswalk-quality panel: how well the crosswalk joins to openFDA NDCs."""
    rep = validation.openfda_ndc_match_rate(store)
    pct = rep.get("match_rate", 0) * 100
    sample = ", ".join(_html.escape(s) for s in rep.get("unmatched_sample", [])[:6])
    return (
        '<div style="border:1px solid #b9cde6;background:#eef4fb;border-radius:4px;'
        'padding:12px 16px;max-width:760px;margin:6px 0 18px;">'
        f'<div style="{_MONO}font-size:10px;letter-spacing:.08em;text-transform:'
        f'uppercase;color:#0b2341;margin-bottom:6px;">Crosswalk coverage vs openFDA</div>'
        f'<div style="font-size:13px;">Of <strong>{rep.get("normalizable",0)}</strong> '
        f'openFDA drug-shortage NDCs, <strong>{rep.get("matched",0)}</strong> '
        f'resolve through the crosswalk '
        f'(<strong>{pct:.1f}%</strong> match rate). '
        f'{rep.get("unnormalizable",0)} were unnormalizable.</div>'
        + (f'<div style="font-size:11px;color:#6a7480;margin-top:4px;">'
           f'Unmatched sample (extend coverage via a live pull): '
           f'<code style="{_MONO}">{sample}</code></div>' if sample else "")
        + '<div style="font-size:10.5px;color:#8b94a0;margin-top:6px;">'
        'Read-only join against openFDA’s vendored drug-shortage snapshot '
        '(package_ndc). Match rate scales with crosswalk breadth.</div></div>'
    )


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


def _export_links() -> str:
    links = " &middot; ".join(
        f'<a href="/rxnorm/export.csv?table={t}" style="color:#155752;">{t}.csv</a>'
        for t in ("crosswalk", "concepts", "classes", "audit"))
    return (f'<div style="font-size:11px;color:#6a7480;margin:0 0 10px;">'
            f'Export: {links}</div>')


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

def render_rxnorm_page(store: Any, params: Optional[Dict[str, str]] = None) -> str:
    params = params or {}
    ndc = (params.get("ndc") or "").strip()
    rxcui = (params.get("rxcui") or "").strip()
    q = (params.get("q") or "").strip()
    class_type = (params.get("class_type") or "").strip()
    class_id = (params.get("class_id") or "").strip()

    summary = analytics.coverage_summary(store)
    counts = summary["counts"]
    cov = summary["class_coverage"]
    join = summary["openfda_join"]
    populated = counts.get("dim_rxnorm_concept", 0) > 0

    title = ck_page_title(
        "Drug reference & NDC→RxCUI crosswalk",
        eyebrow="DRUGS · /rxnorm",
        meta=(f"{counts.get('dim_rxnorm_concept',0)} concepts · "
              f"{counts.get('xwalk_ndc_rxcui',0)} NDCs · "
              f"{cov.get('coverage_pct',0)}% class coverage"),
    ) + ck_source_purpose(
        purpose="Normalize drug names/NDCs to RxNorm concepts and resolve the "
                "NDC→RxCUI crosswalk other drug data joins to.",
        universe="research",
        source="NLM RxNorm / RxNav REST API (public). Offline seed when the API "
               "is unreachable.",
    )

    kpis = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 18px;'
        'max-width:900px;">'
        + _kpi("Concepts", str(counts.get("dim_rxnorm_concept", 0)),
               "in the universe")
        + _kpi("NDC crosswalk", str(counts.get("xwalk_ndc_rxcui", 0)),
               f'{summary["rxcui_with_ndc"]} molecules')
        + _kpi("Class coverage", f'{cov.get("coverage_pct", 0)}%',
               f'{cov.get("classified_rxcui", 0)} classified')
        + _kpi("Retired/remapped", str(summary["retired_or_remapped"]),
               "resolve forward")
        + _kpi("openFDA join", f'{join.get("match_rate", 0)*100:.1f}%',
               f'{join.get("matched", 0)}/{join.get("normalizable", 0)} NDCs')
        + '</div>'
    )

    if not populated:
        body = ('<div class="ck-page-wrap" style="max-width:1040px;margin:0 auto;">'
                + title + kpis + _seed_prompt()
                + _section("Datasets (registry)",
                           "declarative rows — adding a dataset is a row, not code")
                + _registry_table() + '</div>')
        return chartis_shell(body, "Drug reference & NDC crosswalk",
                             active_nav="/research",
                             subtitle="RxNorm concepts, NDC crosswalk, drug classes")

    body = (
        '<div class="ck-page-wrap" style="max-width:1040px;margin:0 auto;">'
        + title + kpis + _export_links()
        + _openfda_coverage_panel(store)
        + _section("NDC resolver", "paste any NDC format → canonical 11-digit + RxCUI")
        + _ndc_tool(store, ndc)
        + _section("Concept search", "find a molecule, then drill into its RxCUI")
        + _search_tool(store, q)
        + (_rxcui_detail(store, rxcui) if rxcui else "")
        + _section("Drug-class explorer",
                   "size the competitive set by therapeutic class or mechanism")
        + _top_class_chart(store, class_type)
        + _class_explorer(store, class_type, class_id)
        + _section("Retired / remapped audit",
                   "stale codes and the active concept they resolve to")
        + _audit_table(store)
        + _section("Datasets (registry)",
                   "declarative rows — adding a dataset is a row, not code")
        + _registry_table()
        + '</div>'
    )
    return chartis_shell(body, "Drug reference & NDC crosswalk",
                         active_nav="/research",
                         subtitle="RxNorm concepts, NDC crosswalk, drug classes")
