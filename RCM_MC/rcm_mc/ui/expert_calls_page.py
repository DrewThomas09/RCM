"""Expert-Call Program — the CDD voice-of-customer workstream.

Renders the call-mix plan for a program size, a per-lens printable
call guide (compliance-safe opening, questions with "listen for"
scoring aids, closing asks), and an honest coverage tracker (a lens
with one call is single-source, zero is a blind spot — the read names
the worst lens, never an average).

The page reads as three workflow phases — PLAN (call mix + cadence),
RUN (lens picker + printable guide + log-a-call), TRACK (coverage +
topic triangulation + findings ledger) — with the analytical tables
wrapped as numbered exhibits (house P5 discipline) so Cmd+P yields
deck-insertable pages.

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
    ExhibitFactory, chartis_shell, ck_action_button, ck_data_cell,
    ck_data_table, ck_editorial_head, ck_empty_state, ck_fmt_number,
    ck_page_actions, ck_provenance_tooltip, ck_section_header,
    ck_signal_badge, ck_source_purpose,
)

# Coverage / triangulation statuses → kit badge tones. The tone map IS
# the module's coverage doctrine: two voices is evidence (positive),
# one voice is an anecdote (warning), zero is a designed-in blind spot
# (negative).
_STATUS_TONE = {
    COVERED:      "positive",
    TRIANGULATED: "positive",
    THIN:         "warning",
    SINGLE_LENS:  "warning",
    UNCOVERED:    "negative",
    DARK:         "negative",
}

# Thesis-tag tone classes for the ledger: CONTRADICTS is the finding a
# memo reader needs first (negative), SUPPORTS is comfort (positive),
# NEW QUESTION is open work (navy).
_TAG_CLASS = {
    "CONTRADICTS": "neg",
    "NEW QUESTION": "new",
    "SUPPORTS": "pos",
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

# Page-scoped editorial styles (xc- namespace). Every color is a kit
# token with its canonical fallback — no ad-hoc hexes — so the page
# rethemes with the design system and every interactive element gets
# hover / focus-visible affordances the old inline styles could not.
_XC_CSS = """
.xc-wrap{max-width:1080px;margin:0 auto;}
.xc-card{border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;
  background:var(--paper-card,#fefcf3);padding:18px 20px;margin:0 0 18px;}
.xc-kicker{font-family:var(--sc-mono,monospace);font-size:10px;
  font-weight:600;letter-spacing:0.08em;color:var(--sc-text-dim,#6a7480);}
.xc-lede{font-size:12px;color:var(--sc-text-dim,#6a7480);
  margin:4px 0 12px;max-width:72ch;}
.xc-lede em{color:var(--green-deep,#154e36);}
.xc-hint{font-size:11px;color:var(--sc-text-dim,#6a7480);}
.xc-sub{font-size:11.5px;color:var(--sc-text-dim,#6a7480);margin-top:2px;}
.xc-legend{font-size:11px;color:var(--sc-text-dim,#6a7480);margin-top:8px;}
.xc-dl{margin-top:12px;}
.xc-note{margin:0 0 14px;padding:9px 13px;
  border:1px solid var(--sc-rule,#d6cfc0);
  border-left:3px solid var(--green-deep,#154e36);border-radius:2px;
  background:var(--paper-card,#fefcf3);font-size:12px;
  color:var(--sc-text,#1a2332);}
.xc-note a{color:var(--sc-teal,#155752);font-weight:600;}
.xc-note-pos{border-left-color:var(--sc-positive,#0a8a5f);}
.xc-note-warn{border-left-color:var(--sc-warning,#b8732a);}
.xc-controls{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;
  margin:0 0 18px;}
.xc-field{display:flex;flex-direction:column;gap:4px;
  font-family:var(--sc-mono,monospace);font-size:10px;font-weight:600;
  letter-spacing:0.07em;text-transform:uppercase;
  color:var(--sc-text-dim,#6a7480);}
.xc-input{height:30px;border:1px solid var(--sc-rule,#c9c1ac);
  border-radius:2px;padding:0 8px;background:#fff;
  color:var(--sc-text,#1a2332);font-family:var(--sc-sans,sans-serif);
  font-size:13px;}
.xc-input:hover{border-color:var(--sc-teal,#155752);}
.xc-input:focus-visible{outline:2px solid var(--sc-teal,#155752);
  outline-offset:1px;}
textarea.xc-input{height:auto;padding:6px 8px;
  font-family:var(--sc-serif,Georgia,serif);font-size:13.5px;}
.xc-w100{width:100%;}
.xc-mt10{margin-top:10px;}
.xc-input-n{width:72px;text-align:right;
  font-family:var(--sc-mono,monospace);font-variant-numeric:tabular-nums;}
.xc-input-deal{width:220px;}
.xc-done-input{width:60px;height:26px;text-align:right;padding:0 6px;
  font-family:var(--sc-mono,monospace);font-variant-numeric:tabular-nums;}
.xc-label{font-size:11px;color:var(--sc-text-dim,#6a7480);display:block;}
.xc-label .xc-input{margin-top:3px;}
.xc-label-inline{font-size:11px;color:var(--sc-text-dim,#6a7480);
  display:inline-flex;align-items:center;gap:6px;}
.xc-form-grid{display:grid;grid-template-columns:1.1fr 1.4fr 0.7fr;
  gap:10px;}
@media (max-width:720px){.xc-form-grid{grid-template-columns:1fr;}}
.xc-form-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;
  margin-top:12px;}
.xc-lens-nav{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 16px;}
.xc-lens-chip{display:inline-block;padding:5px 13px;border-radius:14px;
  font-size:12px;text-decoration:none;color:var(--green-deep,#154e36);
  background:var(--paper-card,#fefcf3);
  border:1px solid var(--sc-rule,#c9c1ac);
  transition:border-color .12s,color .12s;}
.xc-lens-chip:hover{border-color:var(--green-deep,#154e36);}
.xc-lens-chip:focus-visible{outline:2px solid var(--sc-teal,#155752);
  outline-offset:1px;}
.xc-lens-chip[aria-current="true"]{background:var(--green-deep,#154e36);
  color:var(--paper-card,#fefcf3);border-color:var(--green-deep,#154e36);}
.xc-row-sel td{background:var(--green-tint,#e6efe1);}
.xc-lens-link{font-weight:600;color:var(--sc-navy,#0b2341);
  text-decoration:none;}
.xc-lens-link:hover{color:var(--sc-teal,#155752);}
.xc-lens-link:focus-visible{outline:2px solid var(--sc-teal,#155752);
  outline-offset:1px;}
.xc-bias{font-style:italic;color:var(--sc-text-dim,#6a7480);}
.xc-bias-tag{font-weight:600;color:var(--sc-warning,#b8732a);}
.xc-dot-off{color:var(--sc-rule,#c9c1ac);}
.xc-total-row td{border-top:2px solid var(--sc-rule-2,#bfb6a2);}
.xc-cov{max-width:680px;}
.xc-cov-actions{margin-top:10px;}
.xc-read-head{margin-top:14px;}
.xc-list{margin:6px 0 0;padding-left:20px;font-size:12.5px;
  color:var(--sc-text,#1a2332);}
.xc-list li{margin-bottom:6px;}
.xc-focus{margin-top:12px;font-size:12px;}
.xc-guide{padding:6px 4px;}
.xc-guide-h{font-family:var(--sc-serif,Georgia,serif);font-size:21px;
  font-weight:600;color:var(--sc-navy,#0b2341);margin:2px 0 4px;}
.xc-guide-sec{font-family:var(--sc-mono,monospace);font-size:10px;
  font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
  color:var(--sc-text-dim,#6a7480);
  border-bottom:1px solid var(--sc-rule,#d6cfc0);
  padding-bottom:3px;margin:16px 0 8px;}
.xc-q{margin:0 0 12px;}
.xc-q-text{font-family:var(--sc-serif,Georgia,serif);font-size:14px;
  line-height:1.5;color:var(--sc-text,#1a2332);}
.xc-qno{font-family:var(--sc-mono,monospace);font-size:11px;
  color:var(--sc-text-dim,#6a7480);}
.xc-listen{font-size:11.5px;color:var(--green-deep,#154e36);
  margin:3px 0 0 26px;}
.xc-pack{font-family:var(--sc-mono,monospace);font-size:9px;
  font-weight:700;letter-spacing:0.05em;color:var(--sc-warning,#b8732a);
  border:1px solid var(--sc-warning,#b8732a);border-radius:2px;
  padding:0 5px;vertical-align:2px;}
.xc-footnote{margin-top:12px;font-size:11px;
  color:var(--sc-text-dim,#6a7480);}
.xc-link{color:var(--sc-teal,#155752);font-weight:600;
  text-decoration:none;}
.xc-link:hover{text-decoration:underline;}
.xc-tag-head{font-family:var(--sc-mono,monospace);font-size:10.5px;
  font-weight:700;letter-spacing:0.06em;margin:14px 0 8px;}
.xc-tag-neg{color:var(--sc-negative,#b5321e);}
.xc-tag-new{color:var(--sc-navy,#0b2341);}
.xc-tag-pos{color:var(--sc-positive,#0a8a5f);}
.xc-quote{margin:0 0 12px;padding:2px 0 2px 12px;
  border-left:3px solid var(--sc-rule,#d6cfc0);}
.xc-quote-neg{border-left-color:var(--sc-negative,#b5321e);}
.xc-quote-new{border-left-color:var(--sc-navy,#0b2341);}
.xc-quote-pos{border-left-color:var(--sc-positive,#0a8a5f);}
.xc-quote-text{font-family:var(--sc-serif,Georgia,serif);
  font-size:14.5px;line-height:1.5;color:var(--sc-text,#1a2332);
  margin:0;}
.xc-quote-meta{font-family:var(--sc-mono,monospace);font-size:10.5px;
  color:var(--sc-text-dim,#6a7480);margin-top:3px;}
"""


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
    return ck_signal_badge(
        status, tone=_STATUS_TONE.get(status, "neutral"))


def _plan_table(plan: List[Dict[str, Any]], lens_key: str,
                base_qs: str) -> str:
    rows = ""
    for p in plan:
        s = p["stakeholder"]
        sel = ' class="xc-row-sel"' if s["key"] == lens_key else ""
        lens_cell = (
            f'<a class="xc-lens-link" href="/diligence/expert-calls?'
            f'lens={s["key"]}{base_qs}#guide">{html.escape(s["label"])}'
            f'</a><div class="xc-sub">{html.escape(s["who"])}</div>')
        rows += (
            f"<tr{sel}>"
            + ck_data_cell(lens_cell)
            + ck_data_cell(html.escape(s["why"]))
            + ck_data_cell(str(p["calls"]), align="right", mono=True,
                           weight=700)
            + ck_data_cell(f'{p["share_pct"]:.1f}%', align="right",
                           mono=True, tone="dim", bar=p["share_pct"])
            + ck_data_cell(
                f'<span class="xc-bias">{html.escape(s["bias"])}</span>')
            + "</tr>")
    return ck_data_table(
        headers=[
            {"label": "Lens"},
            {"label": "What only they can tell you"},
            {"label": "Calls", "align": "right"},
            {"label": "Mix", "align": "right"},
            {"label": "Known bias of this lens"},
        ],
        rows_html=rows)


def _guide_html(guide: Dict[str, Any]) -> str:
    s = guide["stakeholder"]
    deal = guide["deal_name"]
    opening = "".join(
        f'<li>{html.escape(step)}</li>' for step in guide["opening"])
    closing = "".join(
        f'<li>{html.escape(step)}</li>' for step in guide["closing"])
    sections = ""
    qno = 0
    for sec in guide["sections"]:
        qhtml = ""
        for q in sec["questions"]:
            qno += 1
            pack_tag = ""
            if q.get("pack"):
                pack_tag = (
                    f' <span class="xc-pack">'
                    f'{html.escape(q["pack"].upper())} PACK</span>')
            qhtml += (
                f'<div class="xc-q">'
                f'<div class="xc-q-text"><span class="xc-qno">Q{qno}'
                f'</span> &nbsp;{html.escape(q["question"])}{pack_tag}'
                f'</div>'
                f'<div class="xc-listen">Listen for: '
                f'{html.escape(q["listen_for"])}</div></div>')
        sections += (
            f'<div class="xc-guide-sec">{html.escape(sec["label"])}</div>'
            f'{qhtml}')
    # No own border — the ExhibitFactory figure provides the frame.
    return (
        f'<div id="guide" class="xc-guide">'
        f'<div class="xc-kicker">CALL GUIDE'
        f'{" · " + html.escape(deal.upper()) if deal else ""}</div>'
        f'<div class="xc-guide-h">{html.escape(s["label"])}</div>'
        f'<div class="xc-sub">Sourcing: {html.escape(s["sourcing"])}</div>'
        f'<div class="xc-sub"><span class="xc-bias-tag">Lens bias:</span> '
        f'<span class="xc-bias">{html.escape(s["bias"])}</span></div>'
        f'<div class="xc-guide-sec">Opening — compliance &amp; vantage '
        f'point</div>'
        f'<ol class="xc-list">{opening}</ol>'
        f'{sections}'
        f'<div class="xc-guide-sec">Closing — every call, no exceptions'
        f'</div>'
        f'<ol class="xc-list">{closing}</ol>'
        f'<div class="xc-footnote">This bank is a curated starting point '
        f'— tailor to the engagement, and fold in the suggested '
        f'expert-call questions from the <a class="xc-link" '
        f'href="/diligence/cim-crosscheck">CIM Cross-Check</a> variance '
        f'memo (each red/yellow claim generates one).</div>'
        f'</div>')


def _coverage_block(read: Dict[str, Any], qs: Dict[str, Any],
                    n: int, lens_key: str, deal: str) -> str:
    rows = ""
    for r in read["rows"]:
        s = r["stakeholder"]
        done_input = (
            f'<input type="number" class="xc-input xc-done-input" '
            f'name="done_{s["key"]}" min="0" max="99" '
            f'form="xc-cov-form" '
            f'aria-label="{html.escape(s["label"], quote=True)} calls '
            f'done" value="{r["done"]}">')
        rows += (
            "<tr>"
            + ck_data_cell(html.escape(s["label"]), weight=600)
            + ck_data_cell(done_input, align="right")
            + ck_data_cell(str(r["target"]), align="right", mono=True,
                           tone="dim")
            + ck_data_cell(_status_chip(r["status"]))
            + "</tr>")
    findings = "".join(
        f'<li>{html.escape(f)}</li>' for f in read["findings"])
    # HTML5 form-association: the form element holds only the hidden
    # scope fields; the Done inputs + submit button associate via the
    # form attribute. Keeps the table OUT of the <form> so the print
    # stylesheet (which hides forms) still prints the coverage table.
    hidden = f'<input type="hidden" name="n" value="{n}">'
    if lens_key:
        hidden += (f'<input type="hidden" name="lens" '
                   f'value="{html.escape(lens_key)}">')
    if deal:
        hidden += (f'<input type="hidden" name="deal" '
                   f'value="{html.escape(deal)}">')
    table = ck_data_table(
        headers=[
            {"label": "Lens"},
            {"label": "Done", "align": "right"},
            {"label": "Plan", "align": "right"},
            {"label": "Status"},
        ],
        rows_html=rows)
    read_line = ck_provenance_tooltip(
        "Calls completed",
        (f'READ ({ck_fmt_number(read["total_done"])}/'
         f'{ck_fmt_number(read["total_target"])} CALLS)'),
        explainer=("Counts come from your entries or from structured "
                   "EXPERT CALL notes on the active deal — never both; "
                   "explicit entries always win."))
    return (
        f'<div class="xc-lede">A lens needs <em>two voices</em> before '
        f'it counts as covered — one call is an anecdote, zero is a '
        f'blind spot. The read names the worst lens; it never averages.'
        f'</div>'
        f'<form id="xc-cov-form" method="get" '
        f'action="/diligence/expert-calls">{hidden}</form>'
        f'<div class="xc-cov">{table}</div>'
        f'<div class="xc-cov-actions">'
        + ck_action_button("Update coverage", form_target="xc-cov-form")
        + '</div>'
        f'<div class="xc-kicker xc-read-head">{read_line}</div>'
        f'<ul class="xc-list">{findings}</ul>')


def _cadence_table(cad: Dict[str, Any]) -> str:
    headers = (
        [{"label": "Lens"}]
        + [{"label": f'Wk {w["week"]} · {w["focus"]}', "align": "right"}
           for w in cad["weeks"]]
        + [{"label": "Total", "align": "right"}])
    rows = ""
    for s in STAKEHOLDER_TYPES:
        per_week = cad["by_lens_weeks"].get(s["key"], [0, 0, 0, 0])
        cells = "".join(
            ck_data_cell(str(c), align="right", mono=True, weight=700)
            if c else
            ck_data_cell('<span class="xc-dot-off">·</span>',
                         align="right", mono=True)
            for c in per_week)
        rows += (
            "<tr>"
            + ck_data_cell(html.escape(s["label"]), weight=600)
            + cells
            + ck_data_cell(str(sum(per_week)), align="right", mono=True,
                           tone="dim")
            + "</tr>")
    totals = "".join(
        ck_data_cell(str(w["total"]), align="right", mono=True,
                     weight=700) for w in cad["weeks"])
    rows += (
        '<tr class="xc-total-row">'
        + ck_data_cell("WEEK TOTAL", mono=True, tone="dim")
        + totals
        + ck_data_cell(ck_fmt_number(cad["total"]), align="right",
                       mono=True, weight=700)
        + "</tr>")
    focus = "".join(
        f'<li><b>Week {w["week"]} — {html.escape(w["focus"])}.</b> '
        f'{html.escape(w["rationale"])}</li>' for w in cad["weeks"])
    return (
        ck_data_table(headers=headers, rows_html=rows)
        + f'<ul class="xc-list xc-focus">{focus}</ul>')


def _topic_matrix(coverage: List[Dict[str, Any]],
                  any_done: bool) -> str:
    headers = (
        [{"label": "CDD topic"}]
        + [{"label": _SHORT_LENS[s["key"]], "align": "center"}
           for s in STAKEHOLDER_TYPES]
        + ([{"label": "Triangulation"}] if any_done else []))
    rows = ""
    for row in coverage:
        cells = ""
        for s in STAKEHOLDER_TYPES:
            asked = s["key"] in row["lenses"]
            live = s["key"] in row["active_lenses"]
            if live:
                cells += ck_data_cell("●", align="center", tone="pos")
            elif asked:
                cells += ck_data_cell("●", align="center")
            else:
                cells += ck_data_cell(
                    '<span class="xc-dot-off">·</span>', align="center")
        chip = (ck_data_cell(_status_chip(row["status"]))
                if any_done else "")
        rows += (
            "<tr>"
            + ck_data_cell(html.escape(row["label"]), weight=600)
            + cells + chip + "</tr>")
    legend = ('● asked by this lens'
              + (' (green = lens has a completed call) · a topic is '
                 'TRIANGULATED only when two ACTIVE lenses ask it — '
                 'two voices from one lens share its bias'
                 if any_done else
                 ' · log completed calls above to see which topics '
                 'are triangulated'))
    return (
        ck_data_table(headers=headers, rows_html=rows)
        + f'<div class="xc-legend">{legend}</div>')


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


def _ledger_panel(ledger: Dict[str, Any], deal_label: str,
                  deal_id: str, xf) -> str:
    if not ledger["total"]:
        inner = ck_empty_state(
            "No findings logged yet",
            "Every call logged in the form above lands here under its "
            "thesis tag — contradictions first.",
            icon="❝",
            cta_label="Log the first call", cta_href="#log")
    else:
        sections = ""
        for tag in LEDGER_TAG_ORDER:
            rows = ledger["by_tag"][tag]
            if not rows:
                continue
            cls = _TAG_CLASS.get(tag, "new")
            items = "".join(
                f'<figure class="xc-quote xc-quote-{cls}">'
                f'<blockquote class="xc-quote-text">'
                f'{html.escape(f["finding"])}</blockquote>'
                f'<figcaption class="xc-quote-meta">'
                f'{html.escape(f["lens_label"])} · '
                f'{html.escape(f["vantage"])} · as of '
                f'{html.escape(f["as_of"])}</figcaption></figure>'
                for f in rows)
            sections += (
                f'<div class="xc-tag-head xc-tag-{cls}">{tag} '
                f'({len(rows)})</div>{items}')
        warn = "".join(
            f'<div class="xc-note xc-note-warn">{html.escape(w)}</div>'
            for w in ledger["warnings"])
        counts = " · ".join(
            f'{t} {ck_fmt_number(ledger["counts"][t])}'
            for t in LEDGER_TAG_ORDER)
        inner = (
            f'<div class="xc-kicker">{counts} · '
            f'{ck_fmt_number(ledger["total"])} TOTAL</div>'
            + sections + warn
            + f'<div class="xc-dl"><a class="ck-arrow" '
              f'href="/api/expert-calls/findings.csv?deal_id='
              f'{html.escape(deal_id)}">Download findings (CSV)</a>'
              f'</div>')
    return xf.wrap(
        inner,
        title=f"Findings ledger — {deal_label}",
        units="logged call evidence, grouped by thesis tag — "
              "contradictions first",
        vintage=f"bank {BANK_VINTAGE}")


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
            f'<div class="xc-note">Pre-scoped to your active deal '
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
                f'<div class="xc-note xc-note-pos">'
                f'Call logged to <a href="/deal/{html.escape(deal_id)}">'
                f'{html.escape(deal_label)}</a> as a structured note — '
                f'the coverage tracker below counts it.</div>')
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
        log_block = (
            f'<div class="xc-card" id="log">'
            f'<div class="xc-kicker">LOG A COMPLETED CALL — '
            f'{html.escape(deal_label.upper())}</div>'
            f'<div class="xc-lede">A logged call becomes a structured '
            f'note on the deal record — the coverage tracker and '
            f'findings ledger below derive from it.</div>'
            f'{confirm}'
            f'<form method="post" action="/api/expert-calls/log">'
            f'<input type="hidden" name="deal_id" '
            f'value="{html.escape(deal_id)}">'
            f'<div class="xc-form-grid">'
            f'<label class="xc-label">Lens'
            f'<select name="lens" class="xc-input xc-w100">{lens_opts}'
            f'</select></label>'
            f'<label class="xc-label">Interviewee vantage '
            f'(role, geography)'
            f'<input type="text" name="vantage" maxlength="200" '
            f'placeholder="e.g. former contracting VP, TX Blues" '
            f'class="xc-input xc-w100"></label>'
            f'<label class="xc-label">As of'
            f'<input type="text" name="as_of" maxlength="40" '
            f'placeholder="2026-06" class="xc-input xc-w100"></label>'
            f'</div>'
            f'<label class="xc-label xc-mt10">Key finding '
            f'(one finding per note)'
            f'<textarea name="finding" required maxlength="2000" '
            f'rows="2" class="xc-input xc-w100"></textarea></label>'
            f'<div class="xc-form-row">'
            f'<label class="xc-label-inline">Thesis tag'
            f'<select name="tag" class="xc-input">{tag_opts}</select>'
            f'</label>'
            + ck_action_button("Log call")
            + f'<span class="xc-hint">records a structured note on the '
            f'deal — an untagged call is color, not evidence</span>'
            f'</div></form></div>')

    # Visible-source note when the tracker is fed by logged notes.
    counts_note = ""
    if counts_from_notes:
        counts_note = (
            f'<div class="xc-note">Counts below come from '
            f'<b>{read["total_done"]}</b> logged EXPERT CALL note'
            f'{"s" if read["total_done"] != 1 else ""} on '
            f'<b>{html.escape((active_deal or {}).get("name") or deal_id)}'
            f'</b> — enter numbers to override.</div>')

    # One exhibit factory per render pass so every numbered exhibit on
    # the page shares one sequence (house P5 discipline). Wrap calls
    # happen in display order: mix → cadence → guide → coverage →
    # topics → ledger.
    xf = ExhibitFactory(
        deal_label=deal or "Expert-call program",
        source_default="PEdesk curated question bank")

    mix_exhibit = xf.wrap(
        _plan_table(plan, lens_key, base_qs)
        + f'<div class="xc-dl"><a class="ck-arrow" href="{csv_href}">'
          f'Download call sheet (CSV)</a>'
          f'<div class="xc-hint">One row per planned call with the '
          f'sourcing channel pre-filled and date / interviewee / '
          f'finding columns to keep in the data room.</div></div>',
        title="The call mix — who to call, and what only they can "
              "tell you",
        units=f"CALL MIX — {n}-CALL PROGRAM ACROSS THE SEVEN LENSES · "
              f"mix in % of program",
        vintage=f"bank {BANK_VINTAGE}")

    cadence_exhibit = xf.wrap(
        f'<div class="xc-lede">Same calls as the plan above, re-timed: '
        f'fast-booking lenses frame the hypotheses first; payer and '
        f'competitor calls wait for precise questions; week 4 chases '
        f'contradictions.</div>'
        + _cadence_table(cadence),
        title="Week-by-week cadence",
        units="CADENCE — THE STANDARD 4-WEEK SPRINT · calls per week",
        vintage=f"bank {BANK_VINTAGE}")

    # Exhibit chrome on the guide: a printed guide is the deliverable
    # an associate takes into the call, so it gets the numbered,
    # vintage-stamped treatment (Cmd+P → clean PDF).
    guide_exhibit = ""
    if guide:
        guide_exhibit = xf.wrap(
            _guide_html(guide),
            title=("Call guide — "
                   + guide["stakeholder"]["label"]),
            units=(f'{guide["question_count"]} questions · '
                   f'topic-ordered · print for the call'),
            vintage=f"bank {BANK_VINTAGE}")

    coverage_exhibit = xf.wrap(
        _coverage_block(read, qs, n, lens_key, deal),
        title="Coverage tracker",
        units="COVERAGE — CALLS COMPLETED PER LENS · covered ≥ 2 "
              "voices · thin = 1 · uncovered = 0",
        vintage=f"bank {BANK_VINTAGE}")

    topic_exhibit = xf.wrap(
        _topic_matrix(topics, any_done),
        title="Topic triangulation",
        units="TOPIC × LENS — WHO CAN ANSWER WHAT · ● asked by this "
              "lens",
        vintage=f"bank {BANK_VINTAGE}")

    # Findings ledger — only with a deal context AND the server-passed
    # notes (the ledger is the deal's evidence, not URL state).
    ledger_exhibit = ""
    if deal_id and logged_notes is not None:
        ledger_exhibit = _ledger_panel(
            findings_ledger(logged_notes),
            (active_deal or {}).get("name") or deal_id, deal_id, xf)

    sector_opts = (
        '<option value="">None (generic bank)</option>'
        + "".join(
            f'<option value="{k}"{" selected" if k == sector else ""}>'
            f'{k.title()}</option>' for k in sorted(SECTOR_PACKS)))
    size_form = (
        f'<form method="get" action="/diligence/expert-calls" '
        f'class="xc-controls">'
        f'<label class="xc-field">Program size (calls)'
        f'<input type="number" name="n" value="{n}" min="1" max="200" '
        f'class="xc-input xc-input-n"></label>'
        f'<label class="xc-field">Deal'
        f'<input type="text" name="deal" value="{html.escape(deal)}" '
        f'placeholder="optional — stamps the guide" '
        f'class="xc-input xc-input-deal"></label>'
        f'<label class="xc-field">Sector pack'
        f'<select name="sector" class="xc-input">{sector_opts}</select>'
        f'</label>'
        f'<input type="hidden" name="lens" value="{html.escape(lens_key)}">'
        + ck_action_button("Rebuild plan")
        + '</form>')

    chips = "".join(
        f'<a class="xc-lens-chip" href="/diligence/expert-calls?'
        f'lens={s["key"]}{base_qs}#guide"'
        + (' aria-current="true"' if s["key"] == lens_key else "")
        + f'>{html.escape(s["label"])}</a>'
        for s in STAKEHOLDER_TYPES)
    lens_nav = (
        f'<div class="xc-kicker">CALL GUIDE — PICK A LENS</div>'
        f'<nav class="xc-lens-nav" role="navigation" '
        f'aria-label="Call-guide lens picker">{chips}</nav>')

    head = ck_editorial_head(
        "DILIGENCE · VOICE OF CUSTOMER",
        "Expert-Call Program",
        meta=(f"{n} CALLS · {len(STAKEHOLDER_TYPES)} LENSES · "
              f"{len(cadence['weeks'])}-WEEK SPRINT · "
              f"QUESTION BANK {BANK_VINTAGE}"),
        lede_italic_phrase=("Voice-of-customer is the diligence "
                            "workstream public data cannot do —"),
        lede_body=("plan the call mix across seven stakeholder lenses, "
                   "run each call from a structured, printable guide, "
                   "and track coverage honestly: two voices cover a "
                   "lens, one is an anecdote, zero is a blind spot."),
    )

    body = (
        head
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
        + ck_page_actions()
        + '<div class="xc-wrap">'
        + prefill_note
        + ck_section_header("Plan the program", eyebrow="PHASE 1 · PLAN")
        + size_form
        + mix_exhibit
        + cadence_exhibit
        + ck_section_header("Run the calls", eyebrow="PHASE 2 · RUN")
        + lens_nav
        + guide_exhibit
        + log_block
        + ck_section_header("Track the evidence",
                            eyebrow="PHASE 3 · TRACK")
        + counts_note
        + coverage_exhibit
        + topic_exhibit
        + ledger_exhibit
        + '</div>')
    return chartis_shell(
        body, "Expert-Call Program", active_nav="/diligence",
        subtitle="CDD voice-of-customer planner",
        extra_css=_XC_CSS)
