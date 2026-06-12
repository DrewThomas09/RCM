"""CDD Scope — engagement levels for a commercial due diligence.

Renders the four standard depths (desktop screen → red-flag →
full-scope → confirmatory), a deterministic scoping recommender, the
workstream × level depth matrix with each workstream linked to the
platform surface that executes it, and a per-level task list with a
CSV export. Everything curated/methodology — durations are stated as
market convention, never a quote; nothing here is market data.

qs: ``stage`` / ``familiarity`` / ``type`` drive the recommender;
``level`` selects the task list. All GET — a scoped engagement is a
shareable URL.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.cdd_scope import (
    CDD_LEVELS, DEAL_TYPES, DEPTH_MATRIX, FAMILIARITY, STAGES,
    WORKSTREAMS, NONE, DESKTOP, TARGETED, FULL,
    depth_for, level, level_task_list, recommend_level,
)
from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

# Depth is intensity, not severity — a neutral ink ramp, not the
# semantic red/amber/green palette.
_DEPTH_STYLE = {
    NONE:     ("#a8a092", "·"),
    DESKTOP:  ("#7a8699", "DESKTOP"),
    TARGETED: ("#155752", "TARGETED"),
    FULL:     ("#0b2341", "FULL"),
}


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _depth_chip(depth: str) -> str:
    color, label = _DEPTH_STYLE.get(depth, _DEPTH_STYLE[NONE])
    if depth == NONE:
        return (f'<span style="color:{color};font-size:14px;">·</span>')
    return (f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:9.5px;font-weight:700;letter-spacing:0.05em;'
            f'color:{color};border:1px solid {color};border-radius:4px;'
            f'padding:1px 6px;">{label}</span>')


def _level_cards(selected: str) -> str:
    cards = ""
    for lv in CDD_LEVELS:
        sel = lv["key"] == selected
        cards += (
            f'<div id="{lv["key"]}" style="border:1px solid '
            f'{"#155752" if sel else "#d6cfc0"};border-radius:8px;'
            f'background:#fff;padding:16px 18px;">'
            f'<div style="font-family:{_SERIF};font-size:16px;'
            f'font-weight:700;color:#0b2341;">{html.escape(lv["label"])}'
            f'</div>'
            f'<div style="font-size:11.5px;color:#465366;margin:4px 0;">'
            f'{html.escape(lv["when"])}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:10px;color:#7a8699;margin:6px 0;">'
            f'{html.escape(lv["duration"]).upper()}</div>'
            f'<div style="font-size:12px;color:#1a2332;margin:6px 0;">'
            f'<b>Decision:</b> {html.escape(lv["decision"])}</div>'
            f'<div style="font-size:12px;color:#1a2332;margin:6px 0;">'
            f'<b>Deliverable:</b> {html.escape(lv["deliverable"])}</div>'
            f'<div style="font-size:11.5px;color:#7a4a1f;margin:6px 0;">'
            f'{html.escape(lv["note"])}</div>'
            f'<div style="margin-top:8px;display:flex;gap:12px;'
            f'flex-wrap:wrap;">'
            f'<a href="/diligence/expert-calls?n={lv["calls"]}" '
            f'style="font-size:11.5px;color:#1F7A75;font-weight:600;">'
            f'Call program (~{lv["calls"]} calls) →</a>'
            f'<a href="/api/diligence/cdd-scope.csv?level={lv["key"]}" '
            f'style="font-size:11.5px;color:#1F7A75;font-weight:600;">'
            f'Task list (CSV)</a>'
            f'<a href="/diligence/cdd-scope?level={lv["key"]}#tasks" '
            f'style="font-size:11.5px;color:#1F7A75;">View tasks</a>'
            f'</div></div>')
    return (f'<div style="display:grid;grid-template-columns:repeat(2,'
            f'1fr);gap:14px;margin-top:14px;">{cards}</div>')


def _matrix_table() -> str:
    head = ('<tr style="font-size:10px;letter-spacing:0.06em;'
            'color:#7a8699;text-transform:uppercase;text-align:left;">'
            '<th style="padding:6px 10px;">Workstream</th>'
            + "".join(f'<th style="padding:6px 8px;text-align:center;">'
                      f'{html.escape(lv["label"].split(" · ")[0])}</th>'
                      for lv in CDD_LEVELS)
            + '<th style="padding:6px 10px;">Executes on</th></tr>')
    rows = ""
    for ws in WORKSTREAMS:
        cells = "".join(
            f'<td style="padding:8px 8px;text-align:center;">'
            f'{_depth_chip(depth_for(ws["key"], lv["key"]))}</td>'
            for lv in CDD_LEVELS)
        rows += (
            f'<tr style="border-top:1px solid #e4ddcd;">'
            f'<td style="padding:8px 10px;font-weight:600;'
            f'color:#0b2341;">{html.escape(ws["label"])}</td>{cells}'
            f'<td style="padding:8px 10px;">'
            f'<a href="{html.escape(ws["surface"])}" '
            f'style="font-size:11.5px;color:#1F7A75;">'
            f'{html.escape(ws["surface_label"])}</a></td></tr>')
    return (
        f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
        f'background:#fff;padding:18px 20px;margin-top:18px;">'
        f'<div style="font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;">WORKSTREAM × LEVEL — WHAT '
        f'RUNS AT EACH DEPTH</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12.5px;margin-top:10px;">{head}{rows}</table>'
        f'<div style="font-size:11px;color:#7a8699;margin-top:8px;">'
        f'L1→L3 never does less of a workstream at a deeper level; '
        f'L4 narrows deliberately (confirmation, not discovery). '
        f'· = not run at this level.</div></div>')


def _task_panel(level_key: str) -> str:
    lv = level(level_key)
    tasks = level_task_list(level_key)
    rows = ""
    for t in tasks:
        rows += (
            f'<tr style="border-top:1px solid #e4ddcd;">'
            f'<td style="padding:8px 10px;font-weight:600;'
            f'color:#0b2341;white-space:nowrap;">'
            f'{html.escape(t["workstream"])}</td>'
            f'<td style="padding:8px 10px;">{_depth_chip(t["depth"])}'
            f'</td>'
            f'<td style="padding:8px 10px;font-size:12px;'
            f'color:#1a2332;">{html.escape(t["task"])}</td>'
            f'<td style="padding:8px 10px;white-space:nowrap;">'
            f'<a href="{html.escape(t["surface"])}" '
            f'style="font-size:11.5px;color:#1F7A75;">'
            f'{html.escape(t["surface_label"])}</a></td></tr>')
    return (
        f'<div id="tasks" style="border:1px solid #d6cfc0;'
        f'border-radius:8px;background:#fff;padding:18px 20px;'
        f'margin-top:18px;">'
        f'<div style="font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;">TASK LIST — '
        f'{html.escape(lv["label"].upper())}</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12.5px;margin-top:10px;">'
        f'<tr style="font-size:10px;letter-spacing:0.06em;'
        f'color:#7a8699;text-transform:uppercase;text-align:left;">'
        f'<th style="padding:5px 10px;">Workstream</th>'
        f'<th style="padding:5px 10px;">Depth</th>'
        f'<th style="padding:5px 10px;">Task</th>'
        f'<th style="padding:5px 10px;">Executes on</th></tr>{rows}'
        f'</table>'
        f'<div style="margin-top:10px;">'
        f'<a href="/api/diligence/cdd-scope.csv?level={lv["key"]}" '
        f'style="font-size:12px;color:#1F7A75;font-weight:600;">'
        f'Download this task list (CSV)</a></div></div>')


def cdd_scope_csv(qs: "Dict[str, Any] | None" = None) -> str:
    """The task list for one level as CSV (engagement-plan starter)."""
    import csv
    import io
    level_key = _qs1(qs, "level", "l3").lower()
    lv = level(level_key) or level("l3")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["CDD task list", lv["label"]])
    w.writerow(["Duration (market convention)", lv["duration"]])
    w.writerow(["Decision supported", lv["decision"]])
    w.writerow([])
    w.writerow(["Workstream", "Depth", "Task", "Platform surface",
                "Owner", "Status"])
    for t in level_task_list(lv["key"]):
        w.writerow([t["workstream"], t["depth"], t["task"],
                    t["surface"], "", ""])
    return buf.getvalue()


def render_cdd_scope_page(qs: "Dict[str, Any] | None" = None) -> str:
    qs = qs or {}
    stage = _qs1(qs, "stage", "")
    familiarity = _qs1(qs, "familiarity", "")
    deal_type = _qs1(qs, "type", "")
    rec = (recommend_level(stage, familiarity, deal_type)
           if stage or familiarity or deal_type else None)
    level_key = _qs1(qs, "level", "").lower()
    if level(level_key) is None:
        level_key = (rec["level"]["key"] if rec else "l3")

    def _sel(name, options, current, labels=None):
        labels = labels or {}
        opts = '<option value="">—</option>' + "".join(
            f'<option value="{o}"{" selected" if o == current else ""}>'
            f'{html.escape(labels.get(o, o.title()))}</option>'
            for o in options)
        return (f'<select name="{name}" style="height:32px;border:1px '
                f'solid #c9c1ac;border-radius:5px;min-width:150px;">'
                f'{opts}</select>')

    rec_html = ""
    if (stage or familiarity or deal_type) and rec is None:
        rec_html = (
            '<div style="margin-top:10px;font-size:12px;'
            'color:#b5321e;">Pick all three to get a recommendation — '
            'the scoping aid never guesses from a partial picture.'
            '</div>')
    elif rec:
        notes = "".join(
            f'<li style="margin-bottom:4px;">{html.escape(nt)}</li>'
            for nt in rec["notes"])
        rec_html = (
            f'<div style="margin-top:12px;border:1px solid #155752;'
            f'border-radius:6px;background:rgba(31,122,117,0.07);'
            f'padding:12px 14px;">'
            f'<div style="font-family:{_SERIF};font-size:15px;'
            f'font-weight:700;color:#0b2341;">Recommended: '
            f'<a href="#{rec["level"]["key"]}" style="color:#155752;">'
            f'{html.escape(rec["level"]["label"])}</a></div>'
            f'<div style="font-size:12.5px;color:#1a2332;'
            f'margin-top:4px;">{html.escape(rec["reason"])}</div>'
            + (f'<ul style="margin:8px 0 0;padding-left:20px;'
               f'font-size:12px;color:#7a4a1f;">{notes}</ul>'
               if notes else "")
            + '</div>')

    form = (
        f'<form method="get" action="/diligence/cdd-scope" '
        f'style="display:flex;gap:12px;align-items:end;flex-wrap:wrap;'
        f'margin-top:14px;">'
        f'<label style="font-size:11px;color:#465366;">Deal stage<br>'
        + _sel("stage", STAGES, stage,
               {"screen": "Pre-IOI screen", "bid": "Indicative bid",
                "exclusivity": "Exclusivity / LOI",
                "preclose": "Post-IC, pre-close"})
        + '</label>'
        f'<label style="font-size:11px;color:#465366;">Market '
        f'familiarity<br>'
        + _sel("familiarity", FAMILIARITY, familiarity,
               {"new": "New market", "adjacent": "Adjacent",
                "known": "Known (prior CDD)"})
        + '</label>'
        f'<label style="font-size:11px;color:#465366;">Deal type<br>'
        + _sel("type", DEAL_TYPES, deal_type,
               {"platform": "Platform", "addon": "Add-on"})
        + '</label>'
        f'<button type="submit" style="padding:8px 16px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
        f'font-weight:600;cursor:pointer;">Scope it</button></form>'
        + rec_html)

    body = (
        ck_page_title(
            "CDD Scope",
            eyebrow="DILIGENCE · ENGAGEMENT SCOPING",
            meta="The four depths of a commercial due diligence — "
                 "what runs at each level, and which level this deal "
                 "stage actually needs.",
        )
        + ck_source_purpose(
            purpose="Scope the CDD to the deal stage: a desktop screen, "
                    "a red-flag check, the full-scope build, or a "
                    "confirmatory bring-down — and hand each workstream "
                    "to the platform surface that executes it.",
            universe="research",
            source="Curated engagement methodology. Durations are "
                   "market convention, not a quote; the recommender is "
                   "a deterministic scoping aid, not a rule.",
            next_action="Plan the call program",
            next_href="/diligence/expert-calls",
        )
        + '<div class="ts-wrap" style="max-width:1100px;">'
        + form
        + _level_cards(level_key)
        + _matrix_table()
        + _task_panel(level_key)
        + '</div>')
    return chartis_shell(
        body, "CDD Scope", active_nav="/diligence",
        subtitle="Engagement depth scoping")
