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
from typing import Any, Dict, Optional

from ..diligence.cdd_scope import (
    CDD_LEVELS, DEAL_TYPES, FAMILIARITY, STAGES,
    WORKSTREAMS, NONE, DESKTOP, TARGETED, FULL,
    depth_for, level, level_task_list, recommend_level,
)
from ._chartis_kit import (
    chartis_shell, ck_action_button, ck_arrow_link, ck_data_cell,
    ck_data_table, ck_editorial_head, ck_fmt_number, ck_help_tooltip,
    ck_next_section, ck_page_actions, ck_provenance_tooltip,
    ck_section_header, ck_signal_badge, ck_source_purpose,
)

# Depth is intensity, not severity — a neutral ink ramp (muted →
# deep teal → navy), never the semantic red/amber/green palette.
# Colors live in _CDD_CSS below as kit tokens with canonical
# fallbacks so the site-wide dark-mode CSS can retheme the chips.
_DEPTH_CHIP = {
    DESKTOP:  ("cdd-chip-desktop", "DESKTOP"),
    TARGETED: ("cdd-chip-targeted", "TARGETED"),
    FULL:     ("cdd-chip-full", "FULL"),
}

# Page-scoped classes (injected via chartis_shell's extra_css) —
# every color is a kit var with its canonical fallback; no new hexes.
_CDD_CSS = """
.cdd-wrap{max-width:1160px;}
.cdd-section{margin-top:var(--sc-s-4,14px);}
.cdd-intro{font-size:13px;color:var(--sc-text-dim,#465366);
  max-width:72ch;margin-top:6px;}
.cdd-form{display:flex;gap:14px;align-items:flex-end;flex-wrap:wrap;
  margin-top:var(--sc-s-4,14px);}
.cdd-field{display:flex;flex-direction:column;gap:4px;
  font-family:var(--sc-sans,sans-serif);font-size:10.5px;
  font-weight:600;letter-spacing:0.06em;text-transform:uppercase;
  color:var(--sc-text-dim,#465366);}
.cdd-select{height:34px;min-width:170px;padding:0 8px;
  font-family:var(--sc-sans,sans-serif);font-size:13px;
  color:var(--sc-text,#1a2332);background:var(--paper-card,#fefcf3);
  border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:var(--sc-r-1,2px);}
.cdd-select:hover{border-color:var(--sc-rule-2,#bfb6a2);}
.cdd-select:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:1px;}
.cdd-warn{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  margin-top:12px;padding:10px 14px;
  border:1px solid var(--sc-rule,#d6cfc0);
  border-left:3px solid var(--sc-warning,#b8732a);
  background:var(--paper-card,#fefcf3);
  border-radius:var(--sc-r-1,2px);
  font-size:12.5px;color:var(--sc-text,#1a2332);}
.cdd-rec{margin-top:14px;padding:14px 18px;
  border:1px solid var(--sc-teal,#155752);
  border-left:3px solid var(--green-deep,#154e36);
  background:var(--green-tint,#e6efe1);
  border-radius:var(--sc-r-2,4px);}
.cdd-rec-eyebrow{font-family:var(--sc-mono,monospace);font-size:10px;
  font-weight:700;letter-spacing:0.08em;
  color:var(--green-deep,#154e36);}
.cdd-rec-line{font-family:var(--sc-serif,Georgia),serif;font-size:16px;
  font-weight:600;color:var(--sc-navy,#0b2341);margin-top:4px;}
.cdd-rec-line a{color:var(--green-deep,#154e36);
  text-decoration:underline;
  text-decoration-color:var(--sc-rule-2,#bfb6a2);}
.cdd-rec-line a:hover{text-decoration-color:var(--green-deep,#154e36);}
.cdd-rec-reason{font-size:12.5px;color:var(--sc-text,#1a2332);
  margin-top:4px;max-width:78ch;}
.cdd-rec-notes{margin:8px 0 0;padding-left:20px;font-size:12px;
  color:var(--sc-text-dim,#465366);}
.cdd-rec-notes li{margin-bottom:4px;}
.cdd-rec-cta{margin-top:10px;}
.cdd-levels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:14px;margin-top:var(--sc-s-4,14px);}
@media(max-width:860px){.cdd-levels{grid-template-columns:1fr;}}
.cdd-card{position:relative;border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:17px 19px;}
.cdd-card.is-selected{border:2px solid var(--green-deep,#154e36);
  background:var(--paper-hi,#fbf6e8);padding:16px 18px;}
.cdd-card-tag{font-family:var(--sc-mono,monospace);font-size:10px;
  font-weight:700;letter-spacing:0.08em;
  color:var(--green-deep,#154e36);margin-bottom:6px;}
.cdd-card h3{font-family:var(--sc-serif,Georgia),serif;font-size:17px;
  font-weight:600;color:var(--sc-navy,#0b2341);margin:0;}
.cdd-when{font-size:12px;color:var(--sc-text-dim,#465366);
  margin:4px 0 0;}
.cdd-duration-row{margin:8px 0 0;}
.cdd-duration{font-family:var(--sc-mono,monospace);font-size:10px;
  letter-spacing:0.05em;color:var(--sc-text-dim,#465366);
  font-variant-numeric:tabular-nums;}
.cdd-fact{font-size:12.5px;color:var(--sc-text,#1a2332);
  margin:6px 0 0;}
.cdd-note{font-family:var(--sc-serif,Georgia),serif;font-style:italic;
  font-size:12.5px;color:var(--sc-text-dim,#465366);margin:8px 0 0;}
.cdd-card-links{margin-top:10px;display:flex;gap:14px;flex-wrap:wrap;}
.cdd-link{font-size:11.5px;font-weight:600;
  color:var(--sc-teal-ink,#155752);}
.cdd-link:hover{color:var(--sc-navy,#0b2341);text-decoration:underline;}
.cdd-link:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:1px;}
.cdd-chip{display:inline-block;font-family:var(--sc-mono,monospace);
  font-size:10px;font-weight:700;letter-spacing:0.05em;
  border:1px solid currentColor;border-radius:var(--sc-r-2,4px);
  padding:1px 6px;}
.cdd-chip-desktop{color:var(--sc-text-faint,#7a8699);}
.cdd-chip-targeted{color:var(--sc-teal-ink,#155752);}
.cdd-chip-full{color:var(--sc-navy,#0b2341);}
.cdd-none{color:var(--sc-text-faint,#7a8699);font-size:14px;
  line-height:1;}
.cdd-legend{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
  margin-top:10px;font-size:11px;color:var(--sc-text-dim,#465366);}
.cdd-legend > span:not(.cdd-chip){margin-right:8px;}
.cdd-footnote{font-size:11.5px;color:var(--sc-text-dim,#465366);
  margin-top:8px;max-width:78ch;}
.cdd-download{margin-top:10px;}
.cdd-wrap .ck-data-table tbody tr:hover{
  background:var(--paper-hi,#fbf6e8);}
.cdd-wrap .ck-data-table td.ck-cell{font-size:12px;padding:8px 10px;}
"""


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _depth_chip(depth: str) -> str:
    """Neutral intensity chip. NONE renders a quiet dot that carries an
    accessible name — a bare middot announces nothing to a screen
    reader, which made the depth matrix unreadable non-visually."""
    if depth not in _DEPTH_CHIP:
        return ('<span class="cdd-none" role="img" '
                'aria-label="Not run at this level">·</span>')
    cls, label = _DEPTH_CHIP[depth]
    return f'<span class="cdd-chip {cls}">{label}</span>'


def _level_cards(selected: str) -> str:
    cards = ""
    for i, lv in enumerate(CDD_LEVELS):
        sel = lv["key"] == selected
        # Duration is a calibrated claim — say where it comes from
        # (and surface the team shape, which the card otherwise drops).
        duration = ck_provenance_tooltip(
            "Duration",
            f'<span class="cdd-duration">'
            f'{html.escape(lv["duration"]).upper()}</span>',
            explainer=("Market-convention range for this depth — not "
                       f"a quote. Typical team: {lv['team']}"),
            inject_css=(i == 0),
        )
        tag = ('<p class="cdd-card-tag">SELECTED LEVEL</p>' if sel else "")
        aria = ' aria-current="true"' if sel else ""
        cards += (
            f'<article id="{lv["key"]}" '
            f'class="cdd-card{" is-selected" if sel else ""}"{aria}>'
            f'{tag}'
            f'<h3>{html.escape(lv["label"])}</h3>'
            f'<p class="cdd-when">{html.escape(lv["when"])}</p>'
            f'<div class="cdd-duration-row">{duration}</div>'
            f'<p class="cdd-fact"><b>Decision:</b> '
            f'{html.escape(lv["decision"])}</p>'
            f'<p class="cdd-fact"><b>Deliverable:</b> '
            f'{html.escape(lv["deliverable"])}</p>'
            f'<p class="cdd-note">{html.escape(lv["note"])}</p>'
            f'<div class="cdd-card-links">'
            f'<a class="cdd-link" '
            f'href="/diligence/expert-calls?n={lv["calls"]}">'
            f'Call program (~{ck_fmt_number(lv["calls"])} calls) →</a>'
            f'<a class="cdd-link" '
            f'href="/api/diligence/cdd-scope.csv?level={lv["key"]}">'
            f'Task list (CSV)</a>'
            f'<a class="cdd-link" '
            f'href="/diligence/cdd-scope?level={lv["key"]}#tasks">'
            f'View tasks</a>'
            f'</div></article>')
    return f'<div class="cdd-levels">{cards}</div>'


def _depth_legend() -> str:
    """One legend row serving both the matrix and the task panel."""
    return (
        '<div class="cdd-legend" role="note">'
        + _depth_chip(DESKTOP) + '<span>desk-only pass</span>'
        + _depth_chip(TARGETED)
        + '<span>targeted on thesis-critical claims</span>'
        + _depth_chip(FULL) + '<span>full build</span>'
        + '<span>· = not run at this level</span>'
        + '</div>')


def _matrix_table() -> str:
    headers = (
        [{"label": "Workstream"}]
        + [{"label": lv["label"], "align": "center"} for lv in CDD_LEVELS]
        + [{"label": "Executes on"}])
    rows = ""
    for ws in WORKSTREAMS:
        cells = "".join(
            ck_data_cell(_depth_chip(depth_for(ws["key"], lv["key"])),
                         align="center")
            for lv in CDD_LEVELS)
        surface = (f'<a class="cdd-link" href="{html.escape(ws["surface"])}">'
                   f'{html.escape(ws["surface_label"])}</a>')
        rows += ("<tr>"
                 + ck_data_cell(html.escape(ws["label"]), weight=600)
                 + cells
                 + ck_data_cell(surface)
                 + "</tr>")
    return (
        '<section class="cdd-section">'
        + ck_section_header(
            "Depth by workstream",
            eyebrow="WORKSTREAM × LEVEL — WHAT RUNS AT EACH DEPTH")
        + _depth_legend()
        + ck_data_table(headers=headers, rows_html=rows)
        + '<p class="cdd-footnote">L1→L3 never does less of a '
          'workstream at a deeper level; L4 narrows deliberately '
          '(confirmation, not discovery).</p>'
        + '</section>')


def _task_panel(level_key: str) -> str:
    lv = level(level_key)
    tasks = level_task_list(level_key)
    rows = ""
    for t in tasks:
        surface = (f'<a class="cdd-link" href="{html.escape(t["surface"])}">'
                   f'{html.escape(t["surface_label"])}</a>')
        rows += ("<tr>"
                 + ck_data_cell(html.escape(t["workstream"]), weight=600)
                 + ck_data_cell(_depth_chip(t["depth"]), align="center")
                 + ck_data_cell(html.escape(t["task"]))
                 + ck_data_cell(surface)
                 + "</tr>")
    headers = [{"label": "Workstream"},
               {"label": "Depth", "align": "center"},
               {"label": "Task"},
               {"label": "Executes on"}]
    return (
        '<section id="tasks" class="cdd-section">'
        + ck_section_header(
            "The engagement plan, task by task",
            eyebrow=f"TASK LIST — {lv['label'].upper()}")
        + ck_data_table(headers=headers, rows_html=rows)
        + '<p class="cdd-download">'
        + ck_arrow_link("Download this task list (CSV)",
                        f"/api/diligence/cdd-scope.csv?level={lv['key']}")
        + '</p></section>')


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


def _recommender(stage: str, familiarity: str, deal_type: str,
                 rec: Optional[Dict[str, Any]]) -> str:
    def _sel(name, options, current, labels=None):
        labels = labels or {}
        opts = '<option value="">—</option>' + "".join(
            f'<option value="{o}"{" selected" if o == current else ""}>'
            f'{html.escape(labels.get(o, o.title()))}</option>'
            for o in options)
        return f'<select name="{name}" class="cdd-select">{opts}</select>'

    rec_html = ""
    if (stage or familiarity or deal_type) and rec is None:
        rec_html = (
            '<div class="cdd-warn">'
            + ck_signal_badge("Incomplete", tone="warning")
            + '<span>Pick all three to get a recommendation — '
              'the scoping aid never guesses from a partial picture.'
              '</span></div>')
    elif rec:
        notes = "".join(f'<li>{html.escape(nt)}</li>'
                        for nt in rec["notes"])
        rec_html = (
            '<div class="cdd-rec">'
            '<p class="cdd-rec-eyebrow">SCOPING RECOMMENDATION</p>'
            f'<p class="cdd-rec-line">Recommended: '
            f'<a href="#{rec["level"]["key"]}">'
            f'{html.escape(rec["level"]["label"])}</a></p>'
            f'<p class="cdd-rec-reason">{html.escape(rec["reason"])}</p>'
            + (f'<ul class="cdd-rec-notes">{notes}</ul>' if notes else "")
            + '<p class="cdd-rec-cta">'
            + ck_arrow_link("Open the scoped task list", "#tasks")
            + '</p></div>')

    intro = (
        '<p class="cdd-intro">Pick the deal stage, market familiarity '
        'and deal type — the aid maps them to an engagement depth via '
        'a '
        + ck_help_tooltip(
            "deterministic rule",
            "Deal stage anchors the level (pre-IOI screen → L1, "
            "indicative bid → L2, exclusivity → L3, post-IC → L4); "
            "market familiarity and platform-vs-add-on adjust within "
            "it. The same inputs always return the same scope — a "
            "scoping aid, never a guessed scope.")
        + '. Same inputs, same scope — and the scoped URL is '
          'shareable as the engagement plan.</p>')

    form = (
        '<form method="get" action="/diligence/cdd-scope" '
        'class="cdd-form">'
        '<label class="cdd-field">Deal stage'
        + _sel("stage", STAGES, stage,
               {"screen": "Pre-IOI screen", "bid": "Indicative bid",
                "exclusivity": "Exclusivity / LOI",
                "preclose": "Post-IC, pre-close"})
        + '</label>'
        '<label class="cdd-field">Market familiarity'
        + _sel("familiarity", FAMILIARITY, familiarity,
               {"new": "New market", "adjacent": "Adjacent",
                "known": "Known (prior CDD)"})
        + '</label>'
        '<label class="cdd-field">Deal type'
        + _sel("type", DEAL_TYPES, deal_type,
               {"platform": "Platform", "addon": "Add-on"})
        + '</label>'
        + ck_action_button("Scope it")
        + '</form>')

    return (
        '<section class="cdd-section">'
        + ck_section_header("Scope this deal",
                            eyebrow="SCOPING RECOMMENDER")
        + intro + form + rec_html
        + '</section>')


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

    head = ck_editorial_head(
        "DILIGENCE · ENGAGEMENT SCOPING",
        "CDD Scope",
        meta=(f"{ck_fmt_number(len(CDD_LEVELS))} LEVELS · "
              f"{ck_fmt_number(len(WORKSTREAMS))} WORKSTREAMS · "
              "CURATED METHODOLOGY"),
        lede_italic_phrase="Four depths of one commercial due diligence,",
        lede_body=(
            "from the desktop screen to the confirmatory bring-down — "
            "what runs at each level, and which level this deal stage "
            "actually needs. Scope it once and the URL is the "
            "engagement plan: every workstream hands off to the "
            "platform surface that executes it."),
        source_note=(
            "Curated engagement methodology — durations are market "
            "convention, not a quote; the recommender is a "
            "deterministic scoping aid, not a rule"),
        actions_html=ck_arrow_link("Plan the call program",
                                   "/diligence/expert-calls"),
    )

    body = (
        head
        + ck_source_purpose(
            purpose="Scope the CDD to the deal stage and hand each "
                    "workstream to the platform surface that "
                    "executes it.",
            universe="research",
            source="Curated engagement methodology — not market data.",
        )
        + '<div class="cdd-wrap">'
        + _recommender(stage, familiarity, deal_type, rec)
        + '<section class="cdd-section">'
        + ck_section_header("The four levels", eyebrow="ENGAGEMENT DEPTHS")
        + _level_cards(level_key)
        + '</section>'
        + _matrix_table()
        + _task_panel(level_key)
        + '</div>'
        + ck_next_section("Plan the call program",
                          "/diligence/expert-calls",
                          italic_word="call")
        + ck_page_actions()
    )
    return chartis_shell(
        body, "CDD Scope", active_nav="/diligence",
        subtitle="Engagement depth scoping",
        extra_css=_CDD_CSS)
