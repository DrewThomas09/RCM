"""Expert-Call Program — the CDD voice-of-customer workstream.

Renders the call-mix plan for a program size, a per-lens printable
call guide (compliance-safe opening, questions with "listen for"
scoring aids, closing asks), and an honest coverage tracker (a lens
with one call is single-source, zero is a blind spot — the read names
the worst lens, never an average).

qs: ``n`` program size, ``lens`` selected stakeholder key,
``done_<key>`` completed calls per lens, ``deal`` optional deal name
stamped onto the guide. All GET — the page is a shareable URL, and
the tracker state lives in it.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from ..diligence.expert_calls import (
    STAKEHOLDER_TYPES, build_call_guide, coverage_read, program_plan,
    stakeholder, COVERED, THIN, UNCOVERED,
)
from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

_STATUS_STYLE = {
    COVERED:   ("#0a8a5f", "rgba(10,138,95,0.10)"),
    THIN:      ("#b8732a", "rgba(184,115,42,0.12)"),
    UNCOVERED: ("#b5321e", "rgba(181,50,30,0.10)"),
}


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _qsint(qs, key, default, lo, hi):
    try:
        return max(lo, min(hi, int(_qs1(qs, key, str(default)))))
    except (TypeError, ValueError):
        return default


def _status_chip(status: str) -> str:
    color, bg = _STATUS_STYLE.get(status, ("#465366", "transparent"))
    return (f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:10px;font-weight:700;letter-spacing:0.05em;'
            f'color:{color};background:{bg};border:1px solid {color};'
            f'border-radius:4px;padding:1px 7px;">{html.escape(status)}'
            f'</span>')


def _plan_table(plan: List[Dict[str, Any]], lens_key: str,
                base_qs: str) -> str:
    rows = ""
    for p in plan:
        s = p["stakeholder"]
        sel = s["key"] == lens_key
        rows += (
            f'<tr style="border-top:1px solid #e4ddcd;'
            f'{"background:rgba(31,122,117,0.06);" if sel else ""}">'
            f'<td style="padding:9px 10px;vertical-align:top;">'
            f'<a href="/diligence/expert-calls?lens={s["key"]}{base_qs}'
            f'#guide" style="font-weight:700;color:#0b2341;">'
            f'{html.escape(s["label"])}</a>'
            f'<div style="font-size:11.5px;color:#465366;margin-top:2px;">'
            f'{html.escape(s["who"])}</div></td>'
            f'<td style="padding:9px 10px;vertical-align:top;font-size:12px;'
            f'color:#1a2332;">{html.escape(s["why"])}</td>'
            f'<td class="num" style="padding:9px 10px;text-align:right;'
            f'font-variant-numeric:tabular-nums;font-weight:700;">'
            f'{p["calls"]}</td>'
            f'<td class="num" style="padding:9px 10px;text-align:right;'
            f'font-variant-numeric:tabular-nums;color:#465366;">'
            f'{p["share_pct"]:.1f}%</td>'
            f'<td style="padding:9px 10px;vertical-align:top;font-size:11.5px;'
            f'color:#7a4a1f;">{html.escape(s["bias"])}</td></tr>')
    head = (
        '<tr style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
        'text-transform:uppercase;text-align:left;">'
        '<th style="padding:6px 10px;">Lens</th>'
        '<th style="padding:6px 10px;">What only they can tell you</th>'
        '<th style="padding:6px 10px;text-align:right;">Calls</th>'
        '<th style="padding:6px 10px;text-align:right;">Mix</th>'
        '<th style="padding:6px 10px;">Known bias of this lens</th></tr>')
    return (f'<table style="width:100%;border-collapse:collapse;'
            f'font-size:12.5px;">{head}{rows}</table>')


def _guide_html(guide: Dict[str, Any]) -> str:
    s = guide["stakeholder"]
    deal = guide["deal_name"]
    opening = "".join(
        f'<li style="margin-bottom:6px;">{html.escape(step)}</li>'
        for step in guide["opening"])
    closing = "".join(
        f'<li style="margin-bottom:6px;">{html.escape(step)}</li>'
        for step in guide["closing"])
    sections = ""
    qno = 0
    for sec in guide["sections"]:
        qhtml = ""
        for q in sec["questions"]:
            qno += 1
            qhtml += (
                f'<div style="margin:0 0 12px;">'
                f'<div style="font-family:{_SERIF};font-size:14px;'
                f'color:#1a2332;"><span style="font-family:\'JetBrains '
                f'Mono\',monospace;font-size:11px;color:#7a8699;">Q{qno}'
                f'</span> &nbsp;{html.escape(q["question"])}</div>'
                f'<div style="font-size:11.5px;color:#155752;'
                f'margin:3px 0 0 26px;">Listen for: '
                f'{html.escape(q["listen_for"])}</div></div>')
        sections += (
            f'<div style="margin-top:14px;">'
            f'<div style="font-size:10px;letter-spacing:0.07em;'
            f'font-weight:700;color:#7a8699;text-transform:uppercase;'
            f'border-bottom:1px solid #e4ddcd;padding-bottom:3px;'
            f'margin-bottom:8px;">{html.escape(sec["label"])}</div>'
            f'{qhtml}</div>')
    return (
        f'<div id="guide" style="border:1px solid #d6cfc0;border-radius:8px;'
        f'background:#fff;padding:20px 22px;margin-top:18px;">'
        f'<div style="font-size:10px;letter-spacing:0.07em;font-weight:700;'
        f'color:#7a8699;">CALL GUIDE'
        f'{" · " + html.escape(deal.upper()) if deal else ""}</div>'
        f'<div style="font-family:{_SERIF};font-size:20px;font-weight:700;'
        f'color:#0b2341;margin:2px 0 4px;">{html.escape(s["label"])}</div>'
        f'<div style="font-size:12px;color:#465366;">'
        f'Sourcing: {html.escape(s["sourcing"])}</div>'
        f'<div style="font-size:12px;color:#7a4a1f;margin-top:3px;">'
        f'Lens bias: {html.escape(s["bias"])}</div>'
        f'<div style="margin-top:14px;font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;text-transform:uppercase;'
        f'border-bottom:1px solid #e4ddcd;padding-bottom:3px;'
        f'margin-bottom:8px;">Opening — compliance &amp; vantage point</div>'
        f'<ol style="margin:0;padding-left:20px;font-size:12.5px;'
        f'color:#1a2332;">{opening}</ol>'
        f'{sections}'
        f'<div style="margin-top:14px;font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;text-transform:uppercase;'
        f'border-bottom:1px solid #e4ddcd;padding-bottom:3px;'
        f'margin-bottom:8px;">Closing — every call, no exceptions</div>'
        f'<ol style="margin:0;padding-left:20px;font-size:12.5px;'
        f'color:#1a2332;">{closing}</ol>'
        f'<div style="margin-top:12px;font-size:11px;color:#7a8699;">'
        f'This bank is a curated starting point — tailor to the '
        f'engagement, and fold in the suggested expert-call questions '
        f'from the <a href="/diligence/cim-crosscheck" '
        f'style="color:#1F7A75;">CIM Cross-Check</a> variance memo '
        f'(each red/yellow claim generates one).</div>'
        f'</div>')


def _coverage_block(read: Dict[str, Any], qs: Dict[str, Any],
                    n: int, lens_key: str, deal: str) -> str:
    rows = ""
    for r in read["rows"]:
        s = r["stakeholder"]
        rows += (
            f'<tr style="border-top:1px solid #e4ddcd;">'
            f'<td style="padding:7px 10px;font-weight:600;color:#0b2341;">'
            f'{html.escape(s["label"])}</td>'
            f'<td style="padding:7px 10px;text-align:right;">'
            f'<input type="number" name="done_{s["key"]}" min="0" max="99" '
            f'value="{r["done"]}" style="width:58px;height:28px;'
            f'border:1px solid #c9c1ac;border-radius:5px;text-align:right;'
            f'padding:0 6px;"></td>'
            f'<td class="num" style="padding:7px 10px;text-align:right;'
            f'font-variant-numeric:tabular-nums;color:#465366;">'
            f'{r["target"]}</td>'
            f'<td style="padding:7px 10px;">{_status_chip(r["status"])}'
            f'</td></tr>')
    findings = "".join(
        f'<li style="margin-bottom:5px;">{html.escape(f)}</li>'
        for f in read["findings"])
    hidden = ""
    if lens_key:
        hidden += f'<input type="hidden" name="lens" value="{html.escape(lens_key)}">'
    if deal:
        hidden += f'<input type="hidden" name="deal" value="{html.escape(deal)}">'
    return (
        f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
        f'background:#fff;padding:18px 20px;margin-top:18px;">'
        f'<div style="font-size:10px;letter-spacing:0.07em;font-weight:700;'
        f'color:#7a8699;">COVERAGE — CALLS COMPLETED PER LENS</div>'
        f'<div style="font-size:11.5px;color:#465366;margin:3px 0 10px;">'
        f'A lens needs two voices before it counts as covered — one call '
        f'is an anecdote, zero is a blind spot. The read names the worst '
        f'lens; it never averages.</div>'
        f'<form method="get" action="/diligence/expert-calls">{hidden}'
        f'<input type="hidden" name="n" value="{n}">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12.5px;max-width:560px;">'
        f'<tr style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
        f'text-transform:uppercase;text-align:left;">'
        f'<th style="padding:5px 10px;">Lens</th>'
        f'<th style="padding:5px 10px;text-align:right;">Done</th>'
        f'<th style="padding:5px 10px;text-align:right;">Plan</th>'
        f'<th style="padding:5px 10px;">Status</th></tr>{rows}</table>'
        f'<button type="submit" style="margin-top:10px;padding:8px 16px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
        f'font-weight:600;cursor:pointer;">Update coverage</button></form>'
        f'<div style="margin-top:12px;font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;">READ '
        f'({read["total_done"]}/{read["total_target"]} CALLS)</div>'
        f'<ul style="margin:6px 0 0;padding-left:20px;font-size:12.5px;'
        f'color:#1a2332;">{findings}</ul></div>')


def render_expert_calls_page(qs: "Dict[str, Any] | None" = None) -> str:
    qs = qs or {}
    n = _qsint(qs, "n", 20, 1, 200)
    deal = _qs1(qs, "deal", "")[:80]
    lens_key = _qs1(qs, "lens", "referring_physician")
    if stakeholder(lens_key) is None:
        lens_key = "referring_physician"

    plan = program_plan(n)
    completed = {s["key"]: _qsint(qs, f"done_{s['key']}", 0, 0, 99)
                 for s in STAKEHOLDER_TYPES}
    read = coverage_read(completed, n)
    guide = build_call_guide(lens_key, deal_name=deal)

    base_qs = "".join(
        f"&done_{k}={v}" for k, v in completed.items() if v) + f"&n={n}"
    if deal:
        base_qs += "&deal=" + quote_plus(deal)

    size_form = (
        f'<form method="get" action="/diligence/expert-calls" '
        f'style="display:flex;gap:10px;align-items:center;margin:14px 0 8px;">'
        f'<label style="font-size:12px;color:#465366;">Program size '
        f'<input type="number" name="n" value="{n}" min="1" max="200" '
        f'style="width:64px;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;text-align:right;padding:0 6px;margin-left:4px;">'
        f' calls</label>'
        f'<label style="font-size:12px;color:#465366;">Deal '
        f'<input type="text" name="deal" value="{html.escape(deal)}" '
        f'placeholder="optional — stamps the guide" style="width:200px;'
        f'height:30px;border:1px solid #c9c1ac;border-radius:5px;'
        f'padding:0 8px;margin-left:4px;font-family:{_SERIF};"></label>'
        f'<input type="hidden" name="lens" value="{html.escape(lens_key)}">'
        f'<button type="submit" style="padding:7px 14px;background:#0b2341;'
        f'color:#fff;border:none;border-radius:5px;font-weight:600;'
        f'cursor:pointer;">Rebuild plan</button></form>')

    chips = "".join(
        f'<a href="/diligence/expert-calls?lens={s["key"]}{base_qs}#guide" '
        f'style="display:inline-block;padding:5px 12px;margin:0 6px 6px 0;'
        f'border-radius:14px;font-size:12px;text-decoration:none;'
        + (f'background:#0b2341;color:#fff;border:1px solid #0b2341;'
           if s["key"] == lens_key else
           f'background:#fff;color:#0b2341;border:1px solid #c9c1ac;')
        + f'">{html.escape(s["label"])}</a>'
        for s in STAKEHOLDER_TYPES)

    body = (
        ck_page_title(
            "Expert-Call Program",
            eyebrow="DILIGENCE · VOICE OF CUSTOMER",
            meta="Plan the call mix, run each call from a structured "
                 "guide, and track coverage honestly — the CDD "
                 "workstream public data cannot do.",
        )
        + ck_source_purpose(
            purpose="Design and track the primary-research program of a "
                    "commercial due diligence: which humans to call, what "
                    "to ask each lens, and whether the evidence is "
                    "triangulated or single-source.",
            universe="research",
            source="Curated question bank + program methodology (a "
                   "starting point — tailor to the engagement). Coverage "
                   "counts are your entries; nothing here is market data.",
            next_action="Cross-check management claims first",
            next_href="/diligence/cim-crosscheck",
        )
        + '<div class="ts-wrap" style="max-width:1080px;">'
        + size_form
        + f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
          f'background:#fff;padding:18px 20px;">'
          f'<div style="font-size:10px;letter-spacing:0.07em;'
          f'font-weight:700;color:#7a8699;">CALL MIX — {n}-CALL PROGRAM '
          f'ACROSS THE SEVEN LENSES</div>'
          f'<div style="margin-top:10px;">'
        + _plan_table(plan, lens_key, base_qs)
        + '</div></div>'
        + _coverage_block(read, qs, n, lens_key, deal)
        + f'<div style="margin-top:18px;">'
          f'<div style="font-size:10px;letter-spacing:0.07em;'
          f'font-weight:700;color:#7a8699;margin-bottom:8px;">'
          f'CALL GUIDE — PICK A LENS</div>{chips}</div>'
        + (_guide_html(guide) if guide else "")
        + '</div>')
    return chartis_shell(
        body, "Expert-Call Program", active_nav="/diligence",
        subtitle="CDD voice-of-customer planner")
