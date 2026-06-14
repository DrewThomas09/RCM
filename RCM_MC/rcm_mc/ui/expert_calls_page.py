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
    BANK_VINTAGE, LEDGER_TAG_ORDER, SECTOR_PACKS, STAKEHOLDER_TYPES,
    build_call_guide, call_sheet_rows, coverage_read, findings_ledger,
    logged_call_counts, program_plan, sector_pack, stakeholder,
    topic_coverage, weekly_cadence,
    COVERED, THIN, UNCOVERED, TRIANGULATED, SINGLE_LENS, DARK,
)
from ._chartis_kit import (
    ExhibitFactory, chartis_shell, ck_page_title, ck_source_purpose,
)

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

_STATUS_STYLE = {
    COVERED:      ("#0a8a5f", "rgba(10,138,95,0.10)"),
    THIN:         ("#b8732a", "rgba(184,115,42,0.12)"),
    UNCOVERED:    ("#b5321e", "rgba(181,50,30,0.10)"),
    TRIANGULATED: ("#0a8a5f", "rgba(10,138,95,0.10)"),
    SINGLE_LENS:  ("#b8732a", "rgba(184,115,42,0.12)"),
    DARK:         ("#b5321e", "rgba(181,50,30,0.10)"),
}

# Short lens labels for the topic-matrix column heads (full labels
# live in the plan table above it).
_SHORT_LENS = {
    "referring_physician": "Referrer",
    "payer_exec": "Payer",
    "competitor_exec": "Compet.",
    "former_employee": "Ex-emp",
    "site_administrator": "Site adm",
    "patient_advocate": "Patient",
    "industry_expert": "Expert",
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
            pack_tag = ""
            if q.get("pack"):
                pack_tag = (
                    f' <span style="font-family:\'JetBrains Mono\','
                    f'monospace;font-size:9px;font-weight:700;'
                    f'letter-spacing:0.05em;color:#7a4a1f;border:1px '
                    f'solid #7a4a1f;border-radius:4px;padding:0 5px;'
                    f'vertical-align:2px;">'
                    f'{html.escape(q["pack"].upper())} PACK</span>')
            qhtml += (
                f'<div style="margin:0 0 12px;">'
                f'<div style="font-family:{_SERIF};font-size:14px;'
                f'color:#1a2332;"><span style="font-family:\'JetBrains '
                f'Mono\',monospace;font-size:11px;color:#7a8699;">Q{qno}'
                f'</span> &nbsp;{html.escape(q["question"])}{pack_tag}'
                f'</div>'
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
    # No own border — the ExhibitFactory figure provides the frame.
    return (
        f'<div id="guide" style="padding:6px 4px;">'
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
            f'aria-label="{html.escape(s["label"], quote=True)} calls done" '
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


def _cadence_table(cad: Dict[str, Any]) -> str:
    head = ('<tr style="font-size:10px;letter-spacing:0.06em;'
            'color:#7a8699;text-transform:uppercase;text-align:left;">'
            '<th style="padding:6px 10px;">Lens</th>'
            + "".join(f'<th style="padding:6px 10px;text-align:right;">'
                      f'Wk {w["week"]} · {html.escape(w["focus"])}</th>'
                      for w in cad["weeks"])
            + '<th style="padding:6px 10px;text-align:right;">Total</th>'
            '</tr>')
    rows = ""
    for s in STAKEHOLDER_TYPES:
        per_week = cad["by_lens_weeks"].get(s["key"], [0, 0, 0, 0])
        cells = "".join(
            f'<td class="num" style="padding:7px 10px;text-align:right;'
            f'font-variant-numeric:tabular-nums;'
            f'{"color:#c9c1ac;" if not c else "font-weight:700;"}">'
            f'{c or "·"}</td>' for c in per_week)
        rows += (f'<tr style="border-top:1px solid #e4ddcd;">'
                 f'<td style="padding:7px 10px;font-weight:600;'
                 f'color:#0b2341;">{html.escape(s["label"])}</td>{cells}'
                 f'<td class="num" style="padding:7px 10px;'
                 f'text-align:right;font-variant-numeric:tabular-nums;'
                 f'color:#465366;">{sum(per_week)}</td></tr>')
    totals = ("".join(
        f'<td class="num" style="padding:7px 10px;text-align:right;'
        f'font-variant-numeric:tabular-nums;font-weight:700;">'
        f'{w["total"]}</td>' for w in cad["weeks"]))
    rows += (f'<tr style="border-top:2px solid #c9c1ac;">'
             f'<td style="padding:7px 10px;font-size:10px;'
             f'letter-spacing:0.06em;color:#7a8699;">WEEK TOTAL</td>'
             f'{totals}<td class="num" style="padding:7px 10px;'
             f'text-align:right;font-weight:700;">{cad["total"]}</td>'
             f'</tr>')
    focus = "".join(
        f'<li style="margin-bottom:5px;"><b>Week {w["week"]} — '
        f'{html.escape(w["focus"])}.</b> {html.escape(w["rationale"])}'
        f'</li>' for w in cad["weeks"])
    return (
        f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
        f'background:#fff;padding:18px 20px;margin-top:18px;">'
        f'<div style="font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;">CADENCE — THE STANDARD '
        f'4-WEEK SPRINT</div>'
        f'<div style="font-size:11.5px;color:#465366;margin:3px 0 10px;">'
        f'Same calls as the plan above, re-timed: fast-booking lenses '
        f'frame the hypotheses first; payer and competitor calls wait '
        f'for precise questions; week 4 chases contradictions.</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12.5px;">{head}{rows}</table>'
        f'<ul style="margin:12px 0 0;padding-left:20px;font-size:12px;'
        f'color:#1a2332;">{focus}</ul></div>')


def _topic_matrix(coverage: List[Dict[str, Any]],
                  any_done: bool) -> str:
    head = ('<tr style="font-size:10px;letter-spacing:0.06em;'
            'color:#7a8699;text-transform:uppercase;text-align:left;">'
            '<th style="padding:6px 10px;">CDD topic</th>'
            + "".join(f'<th style="padding:6px 6px;text-align:center;">'
                      f'{html.escape(_SHORT_LENS[s["key"]])}</th>'
                      for s in STAKEHOLDER_TYPES)
            + ('<th style="padding:6px 10px;">Triangulation</th>'
               if any_done else "")
            + '</tr>')
    rows = ""
    for row in coverage:
        cells = ""
        for s in STAKEHOLDER_TYPES:
            asked = s["key"] in row["lenses"]
            live = s["key"] in row["active_lenses"]
            mark = "●" if asked else "·"
            color = ("#0a8a5f" if live else
                     "#0b2341" if asked else "#c9c1ac")
            cells += (f'<td style="padding:7px 6px;text-align:center;'
                      f'color:{color};">{mark}</td>')
        chip = (f'<td style="padding:7px 10px;">'
                f'{_status_chip(row["status"])}</td>' if any_done else "")
        rows += (f'<tr style="border-top:1px solid #e4ddcd;">'
                 f'<td style="padding:7px 10px;font-weight:600;'
                 f'color:#0b2341;">{html.escape(row["label"])}</td>'
                 f'{cells}{chip}</tr>')
    legend = ('● asked by this lens'
              + (' (green = lens has a completed call) · a topic is '
                 'TRIANGULATED only when two ACTIVE lenses ask it — '
                 'two voices from one lens share its bias'
                 if any_done else
                 ' · log completed calls above to see which topics '
                 'are triangulated'))
    return (
        f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
        f'background:#fff;padding:18px 20px;margin-top:18px;">'
        f'<div style="font-size:10px;letter-spacing:0.07em;'
        f'font-weight:700;color:#7a8699;">TOPIC × LENS — WHO CAN '
        f'ANSWER WHAT</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12.5px;margin-top:10px;">{head}{rows}</table>'
        f'<div style="font-size:11px;color:#7a8699;margin-top:8px;">'
        f'{legend}</div></div>')


def _csv_defang(cell: str) -> str:
    """Excel formula-injection guard (house CSV convention)."""
    return "'" + cell if cell[:1] in ("=", "+", "-", "@") else cell


def expert_calls_csv(qs: "Dict[str, Any] | None" = None) -> str:
    """The call-sheet export: one row per planned call with the
    sourcing channel pre-filled and empty tracking columns (date /
    interviewee / status / finding / thesis tag) for the team to keep
    in the data room. Same qs contract as the page."""
    import csv
    import io
    n = _qsint(qs, "n", 20, 1, 200)
    deal = _qs1(qs, "deal", "")[:80]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Expert-call sheet",
                _csv_defang(deal) if deal else "(no deal set)"])
    w.writerow(["Program size", n])
    w.writerow(["Question bank vintage", BANK_VINTAGE])
    w.writerow([])
    w.writerow(["Call #", "Week", "Lens", "Sourcing channel",
                "Scheduled date", "Interviewee (role, vantage)",
                "Status", "Key finding",
                "Thesis tag (SUPPORTS / CONTRADICTS / NEW QUESTION)"])
    for r in call_sheet_rows(n):
        w.writerow([r["call_no"], r["week"], _csv_defang(r["lens"]),
                    _csv_defang(r["sourcing"]), "", "", "", "", ""])
    return buf.getvalue()


# Thesis-tag tones for the ledger: CONTRADICTS is the finding a memo
# reader needs first (negative), SUPPORTS is comfort (positive),
# NEW QUESTION is open work (navy).
_TAG_TONE = {
    "CONTRADICTS": "#b5321e",
    "NEW QUESTION": "#0b2341",
    "SUPPORTS": "#0a8a5f",
}


def _ledger_panel(ledger: Dict[str, Any], deal_label: str,
                  deal_id: str, xf) -> str:
    if not ledger["total"]:
        inner = (
            f'<div style="font-size:12.5px;color:#7a8699;'
            f'padding:8px 4px;">No findings logged yet — the ledger '
            f'builds itself from the "Log a completed call" form '
            f'above. Every logged call lands here under its thesis '
            f'tag.</div>')
    else:
        sections = ""
        for tag in LEDGER_TAG_ORDER:
            rows = ledger["by_tag"][tag]
            if not rows:
                continue
            tone = _TAG_TONE[tag]
            items = ""
            for f in rows:
                items += (
                    f'<div style="margin:0 0 10px;padding-left:10px;'
                    f'border-left:3px solid {tone};">'
                    f'<div style="font-size:13px;color:#1a2332;">'
                    f'{html.escape(f["finding"])}</div>'
                    f'<div style="font-size:11px;color:#7a8699;'
                    f'margin-top:2px;">'
                    f'{html.escape(f["lens_label"])} · '
                    f'{html.escape(f["vantage"])} · as of '
                    f'{html.escape(f["as_of"])}</div></div>')
            sections += (
                f'<div style="margin-top:12px;">'
                f'<div style="font-family:\'JetBrains Mono\',monospace;'
                f'font-size:10.5px;font-weight:700;letter-spacing:'
                f'0.06em;color:{tone};margin-bottom:8px;">{tag} '
                f'({len(rows)})</div>{items}</div>')
        warn = "".join(
            f'<div style="margin-top:10px;padding:8px 12px;border:1px '
            f'solid #b8732a;border-radius:6px;background:'
            f'rgba(184,115,42,0.08);font-size:12px;color:#7a4a1f;">'
            f'{html.escape(w)}</div>' for w in ledger["warnings"])
        counts = " · ".join(
            f'{t} {ledger["counts"][t]}' for t in LEDGER_TAG_ORDER)
        inner = (
            f'<div style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:10px;color:#7a8699;">{counts} · '
            f'{ledger["total"]} TOTAL</div>'
            + sections + warn
            + f'<div style="margin-top:12px;">'
              f'<a href="/api/expert-calls/findings.csv?deal_id='
              f'{html.escape(deal_id)}" style="font-size:12px;'
              f'color:#1F7A75;font-weight:600;">Download findings '
              f'(CSV)</a></div>')
    return (
        '<div style="margin-top:18px;">'
        + xf.wrap(
            f'<div style="padding:4px 2px;">{inner}</div>',
            title=f"Findings ledger — {deal_label}",
            units="logged call evidence, grouped by thesis tag — "
                  "contradictions first",
            vintage=f"bank {BANK_VINTAGE}")
        + '</div>')


def findings_csv(deal_label: str, note_bodies) -> str:
    """The findings ledger as CSV — the evidence appendix a memo
    drafter pastes from. Same strict parser as the page; free-text
    notes never appear."""
    import csv
    import io
    ledger = findings_ledger(note_bodies)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Expert-call findings ledger",
                _csv_defang(deal_label) if deal_label else
                "(no deal set)"])
    w.writerow(["Total findings", ledger["total"]])
    for t in LEDGER_TAG_ORDER:
        w.writerow([t, ledger["counts"][t]])
    for warn in ledger["warnings"]:
        w.writerow(["WARNING", _csv_defang(warn)])
    w.writerow([])
    w.writerow(["Thesis tag", "Finding", "Lens",
                "Interviewee vantage", "As of"])
    for tag in LEDGER_TAG_ORDER:
        for f in ledger["by_tag"][tag]:
            w.writerow([tag, _csv_defang(f["finding"]),
                        _csv_defang(f["lens_label"]),
                        _csv_defang(f["vantage"]),
                        _csv_defang(f["as_of"])])
    return buf.getvalue()


def render_expert_calls_page(
        qs: "Dict[str, Any] | None" = None, *,
        active_deal: "Dict[str, str] | None" = None,
        logged_counts: "Dict[str, int] | None" = None,
        logged_notes: "list | None" = None) -> str:
    qs = qs or {}
    n = _qsint(qs, "n", 20, 1, 200)
    deal = _qs1(qs, "deal", "")[:80]
    lens_key = _qs1(qs, "lens", "referring_physician")
    if stakeholder(lens_key) is None:
        lens_key = "referring_physician"
    sector = _qs1(qs, "sector", "").strip().lower()
    if sector_pack(sector) is None:
        sector = ""

    plan = program_plan(n)
    # The notes list (when the server passes it) is the single source:
    # counts derive from it unless explicitly provided.
    if logged_notes is not None and logged_counts is None:
        logged_counts = logged_call_counts(logged_notes)
    # Coverage source of truth: explicit done_* params win; with none
    # entered, the counts come from the structured EXPERT CALL notes
    # already logged on the active deal (the evidence trail), and the
    # page says so — never a silent substitution.
    any_done_params = any(_qs1(qs, f"done_{s['key']}")
                          for s in STAKEHOLDER_TYPES)
    counts_from_notes = (not any_done_params
                         and bool(logged_counts))
    if counts_from_notes:
        completed = {s["key"]: min(99, max(0, int(
            logged_counts.get(s["key"], 0))))
            for s in STAKEHOLDER_TYPES}
    else:
        completed = {s["key"]: _qsint(qs, f"done_{s['key']}", 0, 0, 99)
                     for s in STAKEHOLDER_TYPES}
    read = coverage_read(completed, n)
    guide = build_call_guide(lens_key, deal_name=deal, sector=sector)

    # Lens-chip links carry the tracker state — but when the counts
    # come from logged notes, baking them into done_* params would
    # freeze a live count into an explicit override. Leave them out so
    # navigation keeps deriving from the notes.
    base_qs = ("" if counts_from_notes else "".join(
        f"&done_{k}={v}" for k, v in completed.items() if v)) + f"&n={n}"
    if deal:
        base_qs += "&deal=" + quote_plus(deal)
    if sector:
        base_qs += "&sector=" + quote_plus(sector)

    cadence = weekly_cadence(n)
    topics = topic_coverage(completed)
    any_done = read["total_done"] > 0

    # The call-sheet export carries the same program scope; the
    # internal _prefill_deal key never leaks into the export URL.
    csv_href = f"/api/diligence/expert-calls.csv?n={n}"
    if deal:
        csv_href += "&deal=" + quote_plus(deal)

    # Active-deal prefill is visible, never silent (house pattern).
    prefill_src = _qs1(qs, "_prefill_deal", "")
    prefill_note = ""
    if prefill_src and deal:
        prefill_note = (
            f'<div style="margin:12px 0 0;padding:8px 12px;border:1px '
            f'solid #1F7A75;border-radius:6px;background:'
            f'rgba(31,122,117,0.07);font-size:12px;color:#155752;">'
            f'Pre-scoped to your active deal '
            f'<b>{html.escape(deal)}</b> — the guide stamp and call '
            f'sheet carry its name. Type a different deal to '
            f'override.</div>')

    # Log-a-call: only offered with a deal context — a call note has
    # to live on a deal record, there is nothing honest to attach it
    # to otherwise (same rule as the roll-up save).
    log_block = ""
    deal_id = (active_deal or {}).get("id", "")
    if deal_id:
        deal_label = (active_deal.get("name") or deal_id)
        if _qs1(qs, "logged") == "1":
            confirm = (
                f'<p style="font-size:12px;color:#0a8a5f;margin:0 0 10px;">'
                f'Call logged to <a href="/deal/{html.escape(deal_id)}" '
                f'style="color:#0a8a5f;font-weight:700;">'
                f'{html.escape(deal_label)}</a> as a structured note — '
                f'the coverage tracker below counts it.</p>')
        else:
            confirm = ""
        lens_opts = "".join(
            f'<option value="{s["key"]}"'
            f'{" selected" if s["key"] == lens_key else ""}>'
            f'{html.escape(s["label"])}</option>'
            for s in STAKEHOLDER_TYPES)
        tag_opts = "".join(
            f'<option value="{t}">{t}</option>'
            for t in ("SUPPORTS", "CONTRADICTS", "NEW QUESTION"))
        _in = (f'height:30px;border:1px solid #c9c1ac;border-radius:5px;'
               f'padding:0 8px;font-family:{_SERIF};')
        log_block = (
            f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
            f'background:#fff;padding:18px 20px;margin-top:18px;">'
            f'<div style="font-size:10px;letter-spacing:0.07em;'
            f'font-weight:700;color:#7a8699;margin-bottom:8px;">'
            f'LOG A COMPLETED CALL — {html.escape(deal_label.upper())}'
            f'</div>{confirm}'
            f'<form method="post" action="/api/expert-calls/log">'
            f'<input type="hidden" name="deal_id" '
            f'value="{html.escape(deal_id)}">'
            f'<div style="display:grid;grid-template-columns:1.1fr 1.4fr '
            f'0.7fr;gap:10px;">'
            f'<label style="font-size:11px;color:#465366;">Lens'
            f'<select name="lens" style="width:100%;{_in}">{lens_opts}'
            f'</select></label>'
            f'<label style="font-size:11px;color:#465366;">Interviewee '
            f'vantage (role, geography)'
            f'<input type="text" name="vantage" maxlength="200" '
            f'placeholder="e.g. former contracting VP, TX Blues" '
            f'style="width:100%;{_in}"></label>'
            f'<label style="font-size:11px;color:#465366;">As of'
            f'<input type="text" name="as_of" maxlength="40" '
            f'placeholder="2026-06" style="width:100%;{_in}"></label>'
            f'</div>'
            f'<label style="font-size:11px;color:#465366;display:block;'
            f'margin-top:10px;">Key finding (one finding per note)'
            f'<textarea name="finding" required maxlength="2000" rows="2" '
            f'style="width:100%;border:1px solid #c9c1ac;border-radius:5px;'
            f'padding:6px 8px;font-family:{_SERIF};"></textarea></label>'
            f'<div style="display:flex;gap:12px;align-items:center;'
            f'margin-top:10px;">'
            f'<label style="font-size:11px;color:#465366;">Thesis tag'
            f'<select name="tag" style="{_in}margin-left:6px;">{tag_opts}'
            f'</select></label>'
            f'<button type="submit" style="padding:8px 16px;'
            f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
            f'font-weight:600;cursor:pointer;">Log call</button>'
            f'<span style="font-size:11px;color:#7a8699;">records a '
            f'structured note on the deal — an untagged call is color, '
            f'not evidence</span></div></form></div>')

    # Visible-source note when the tracker is fed by logged notes.
    counts_note = ""
    if counts_from_notes:
        counts_note = (
            f'<div style="font-size:11.5px;color:#155752;'
            f'margin:0 0 8px;">Counts below come from '
            f'<b>{read["total_done"]}</b> logged EXPERT CALL note'
            f'{"s" if read["total_done"] != 1 else ""} on '
            f'<b>{html.escape((active_deal or {}).get("name") or deal_id)}'
            f'</b> — enter numbers to override.</div>')

    # One exhibit factory per render pass so the ledger + guide share
    # the page's numbering (house P5 discipline).
    xf = ExhibitFactory(
        deal_label=deal or "Expert-call program",
        source_default="PEdesk curated question bank")

    # Findings ledger — only with a deal context AND the server-passed
    # notes (the ledger is the deal's evidence, not URL state).
    ledger_html = ""
    if deal_id and logged_notes is not None:
        ledger_html = _ledger_panel(
            findings_ledger(logged_notes),
            (active_deal or {}).get("name") or deal_id, deal_id, xf)

    # Exhibit chrome on the guide: a printed guide is the deliverable
    # an associate takes into the call, so it gets the numbered,
    # vintage-stamped treatment (Cmd+P → clean PDF).
    guide_html = ""
    if guide:
        guide_html = (
            '<div style="margin-top:18px;">'
            + xf.wrap(
                _guide_html(guide),
                title=("Call guide — "
                       + guide["stakeholder"]["label"]),
                units=(f'{guide["question_count"]} questions · '
                       f'topic-ordered · print for the call'),
                vintage=f"bank {BANK_VINTAGE}")
            + '</div>')

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
        f'<label style="font-size:12px;color:#465366;">Sector pack '
        f'<select name="sector" style="height:30px;border:1px solid '
        f'#c9c1ac;border-radius:5px;margin-left:4px;">'
        f'<option value="">None (generic bank)</option>'
        + "".join(
            f'<option value="{k}"{" selected" if k == sector else ""}>'
            f'{k.title()}</option>' for k in sorted(SECTOR_PACKS))
        + '</select></label>'
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
        + prefill_note
        + size_form
        + f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
          f'background:#fff;padding:18px 20px;">'
          f'<div style="font-size:10px;letter-spacing:0.07em;'
          f'font-weight:700;color:#7a8699;">CALL MIX — {n}-CALL PROGRAM '
          f'ACROSS THE SEVEN LENSES</div>'
          f'<div style="margin-top:10px;">'
        + _plan_table(plan, lens_key, base_qs)
        + '</div>'
        + f'<div style="margin-top:10px;"><a href="{csv_href}" '
          f'style="font-size:12px;color:#1F7A75;font-weight:600;">'
          f'Download call sheet (CSV)</a>'
          f'<span style="font-size:11px;color:#7a8699;"> — one row per '
          f'planned call with the sourcing channel pre-filled and '
          f'date / interviewee / finding columns to keep in the data '
          f'room.</span></div></div>'
        + _cadence_table(cadence)
        + log_block
        + (f'<div style="margin-top:18px;">{counts_note}</div>'
           if counts_note else "")
        + _coverage_block(read, qs, n, lens_key, deal)
        + _topic_matrix(topics, any_done)
        + ledger_html
        + f'<div style="margin-top:18px;">'
          f'<div style="font-size:10px;letter-spacing:0.07em;'
          f'font-weight:700;color:#7a8699;margin-bottom:8px;">'
          f'CALL GUIDE — PICK A LENS</div>{chips}</div>'
        + guide_html
        + '</div>')
    return chartis_shell(
        body, "Expert-Call Program", active_nav="/diligence",
        subtitle="CDD voice-of-customer planner")
