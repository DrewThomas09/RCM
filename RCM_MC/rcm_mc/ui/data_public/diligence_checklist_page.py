"""Diligence Checklist Generator page — /diligence-checklist.

Public-data sibling of the /diligence/checklist workspace. The rule
engine (``rcm_mc.data_public.diligence_checklist``) evaluates a
hypothetical deal profile (sector, EV, commercial payer share, AR
days) into a six-section, IC-ready checklist. Everything rendered
below the form — the CRITICAL/WARNING/PASS/MISSING verdicts, the
per-item findings and recommendations, and the open-questions list —
comes straight from the engine; nothing is hand-set.
"""
from __future__ import annotations

import html as _html
import re as _re
from datetime import datetime, timezone

from rcm_mc.data_public.diligence_checklist import compute_diligence_checklist
from rcm_mc.ui._chartis_kit import (
    P, SafeHtml, chartis_shell, ck_affirm_empty, ck_data_cell,
    ck_data_table, ck_editorial_head, ck_empty_state, ck_fmt_number,
    ck_fmt_percent, ck_help_tooltip, ck_kpi_block, ck_next_section,
    ck_page_actions, ck_panel, ck_provenance_tooltip, ck_signal_badge,
    ck_source_purpose,
)


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Laboratory", "Orthopedics", "Cardiology",
    "Gastroenterology", "Ophthalmology", "Physical Therapy",
    "Skilled Nursing", "Health IT", "Revenue Cycle Management",
    "Staffing", "Pediatric",
]

# Section order mirrors rcm_mc.data_public.diligence_checklist.
_CATEGORY_ORDER = [
    "1. Deal Overview", "2. Returns Analysis", "3. Capital Structure",
    "4. Payer Mix Risk", "5. PE Intelligence", "6. Data Quality",
]

# Kit-tone mapping for the engine's evaluated statuses. The data
# module's own priority_color carries a non-kit orange (#ea580c);
# the page maps status/priority onto canonical kit tones instead so
# the chart, chips, and text agree with every other surface.
_STATUS_TONE = {
    "CRITICAL": "critical",
    "WARNING": "warning",
    "MISSING": "neutral",
    "PASS": "positive",
}

_PRIORITY_CLASS = {
    "Critical": "tone-negative",
    "High": "tone-warning",
    "Medium": "tone-dim",
    "Low": "tone-faint",
}


def _scoped_styles() -> str:
    """Page-scoped classes — kit CSS vars with canonical fallbacks
    only; no inline style attributes anywhere on the page."""
    css = """
/* ── Deal-profile form ───────────────────────────────────────── */
.dpc-form{background:#fff;border:1px solid var(--sc-rule,#d6cfc0);
border-radius:2px;padding:12px 16px 16px;margin:0 0 var(--sc-s-5,16px);}
.dpc-fieldset{border:0;margin:0;padding:0;min-width:0;}
.dpc-form-legend{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:10px;font-weight:700;letter-spacing:0.14em;
text-transform:uppercase;color:var(--sc-text-faint,#7a8699);
padding:0;margin-bottom:8px;}
.dpc-form-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;
gap:12px;align-items:end;}
@media (max-width:860px){.dpc-form-grid{grid-template-columns:1fr 1fr;}}
.dpc-label{display:block;font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:10px;color:var(--sc-text-dim,#465366);text-transform:uppercase;
letter-spacing:0.07em;margin-bottom:4px;}
.dpc-input{background:var(--sc-bone,#ece5d6);color:var(--sc-text,#1a2332);
border:1px solid var(--sc-rule,#d6cfc0);padding:6px 8px;
font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:12px;
border-radius:2px;width:100%;box-sizing:border-box;}
.dpc-input:focus-visible{outline:2px solid var(--sc-teal,#155752);
outline-offset:1px;}
.dpc-submit{background:var(--sc-teal,#155752);color:var(--sc-on-navy,#e9eef5);
border:1px solid var(--sc-teal,#155752);padding:8px 20px;
font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:11px;
letter-spacing:0.06em;text-transform:uppercase;font-weight:600;
cursor:pointer;border-radius:2px;white-space:nowrap;}
.dpc-submit:hover{background:var(--sc-navy,#0b2341);
border-color:var(--sc-navy,#0b2341);}
.dpc-submit:focus-visible{outline:2px solid var(--sc-teal,#155752);
outline-offset:2px;}

/* ── KPI strip tone helper ───────────────────────────────────── */
.dpc-neg{color:var(--sc-negative,#b5321e);}
.dpc-kpis{margin:0 0 var(--sc-s-5,16px);}

/* ── Category chart ──────────────────────────────────────────── */
.dpc-catsvg{width:100%;max-width:660px;height:auto;display:block;}
.dpc-chartlegend{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px;}
.dpc-chartlegend__key{display:inline-flex;align-items:center;gap:5px;
font-size:10.5px;color:var(--sc-text-dim,#465366);}
.dpc-chartlegend__swatch{width:9px;height:9px;display:inline-block;}
.dpc-chartlegend__swatch.s-crit{background:var(--sc-negative,#b5321e);}
.dpc-chartlegend__swatch.s-high{background:var(--sc-warning,#b8732a);}
.dpc-chartlegend__swatch.s-med{background:var(--sc-text-faint,#7a8699);}
.dpc-caption{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:9.5px;letter-spacing:0.05em;text-transform:uppercase;
color:var(--sc-text-faint,#7a8699);margin-top:6px;}

/* ── Section jump rail ───────────────────────────────────────── */
.dpc-anchors{display:flex;flex-wrap:wrap;gap:6px 14px;
margin:0 0 var(--sc-s-4,12px);
font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:10px;
letter-spacing:0.06em;text-transform:uppercase;}
.dpc-anchors a{color:var(--sc-teal-ink,#155752);text-decoration:none;}
.dpc-anchors a:hover{text-decoration:underline;}
.dpc-anchors a:focus-visible{outline:2px solid var(--sc-teal,#155752);
outline-offset:2px;}

/* ── Checklist tables ────────────────────────────────────────── */
.dpc-item-title{font-size:12.5px;color:var(--sc-text,#1a2332);
font-weight:600;line-height:1.45;}
.dpc-item-title .ck-badge{margin-left:6px;vertical-align:1px;}
.dpc-item-desc{font-size:11px;color:var(--sc-text-faint,#7a8699);
line-height:1.5;margin-top:2px;font-weight:400;}
.dpc-finding{font-size:12px;color:var(--sc-text-dim,#465366);
line-height:1.5;}
.dpc-rec{display:block;font-size:11px;color:var(--sc-text-dim,#465366);
font-style:italic;line-height:1.5;margin-top:2px;}
.dpc-prio{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:10px;letter-spacing:0.08em;text-transform:uppercase;
font-weight:600;white-space:nowrap;}
.dpc-prio.tone-negative{color:var(--sc-negative,#b5321e);}
.dpc-prio.tone-warning{color:var(--sc-warning,#b8732a);}
.dpc-prio.tone-dim{color:var(--sc-text-dim,#465366);}
.dpc-prio.tone-faint{color:var(--sc-text-faint,#7a8699);}
.dpc-sections .ck-data-table tbody tr:hover{
background:var(--bg-tint,#e8e0d0);}
.dpc-sections .ck-cell{vertical-align:top;padding:7px 10px;}
.dpc-sections .ck-badge{font-size:9px;padding:2px 6px;white-space:nowrap;}

/* ── Open questions ──────────────────────────────────────────── */
.dpc-oq-row{padding:8px 0;border-bottom:1px solid var(--sc-rule,#d6cfc0);
display:grid;grid-template-columns:32px 84px 1fr;gap:12px;
align-items:baseline;font-size:12.5px;color:var(--sc-text-dim,#465366);
line-height:1.5;}
.dpc-oq-row:last-child{border-bottom:0;}
.dpc-oq-row .ck-badge{font-size:9px;padding:2px 6px;white-space:nowrap;}
.dpc-oq-idx{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:10.5px;color:var(--sc-text-faint,#7a8699);
font-variant-numeric:tabular-nums;}

/* ── Footnote ────────────────────────────────────────────────── */
.dpc-footnote{margin:0 2px var(--sc-s-5,16px);
font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:10px;
color:var(--sc-text-dim,#465366);line-height:1.6;max-width:92ch;}
"""
    return f"<style>{css}</style>"


def _slug(category: str) -> str:
    return "sec-" + _re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")


def _category_bar_svg(by_category: dict) -> str:
    """Stacked bar per section, colored by evaluated priority —
    Critical (kit negative), High (kit warning), Medium/Low (faint).
    Returns '' when there is nothing to chart (house convention)."""
    cats = [c for c in _CATEGORY_ORDER if c in by_category]
    if not cats:
        return ""
    W, bar_h, row_h = 660, 14, 26
    pad_l, pad_r, pad_t = 170, 84, 8
    total_h = pad_t + len(cats) * row_h + 4
    max_count = max(len(items) for items in by_category.values()) or 1
    chart_w = W - pad_l - pad_r

    parts = [
        f'<svg viewBox="0 0 {W} {total_h}" '
        'preserveAspectRatio="xMidYMid meet" class="dpc-catsvg" '
        'role="img" aria-label="Checklist items by category and priority" '
        'font-family="JetBrains Mono,monospace" font-size="10" '
        'xmlns="http://www.w3.org/2000/svg">'
    ]
    for i, cat in enumerate(cats):
        items = by_category[cat]
        y = pad_t + i * row_h
        critical_n = sum(1 for x in items if x.priority == "Critical")
        high_n = sum(1 for x in items if x.priority == "High")
        other_n = len(items) - critical_n - high_n

        x_off = float(pad_l)
        for n, color in ((critical_n, P["negative"]),
                         (high_n, P["warning"]),
                         (other_n, P["text_faint"])):
            if n > 0:
                bw = (n / max_count) * chart_w
                parts.append(
                    f'<rect x="{x_off:.1f}" y="{y}" width="{bw:.1f}" '
                    f'height="{bar_h}" fill="{color}" opacity="0.85"/>')
                x_off += bw

        parts.append(
            f'<text x="{pad_l - 8}" y="{y + bar_h - 3}" text-anchor="end" '
            f'fill="{P["text_dim"]}">{_html.escape(cat)}</text>')
        parts.append(
            f'<text x="{x_off + 6:.1f}" y="{y + bar_h - 3}" '
            f'fill="{P["text_dim"]}">{len(items)} items</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _chart_legend() -> str:
    """Swatch legend + mono caption so the color encoding is decodable
    without hovering the tables below."""
    return (
        '<div class="dpc-chartlegend">'
        '<span class="dpc-chartlegend__key">'
        '<span class="dpc-chartlegend__swatch s-crit"></span>Critical</span>'
        '<span class="dpc-chartlegend__key">'
        '<span class="dpc-chartlegend__swatch s-high"></span>High</span>'
        '<span class="dpc-chartlegend__key">'
        '<span class="dpc-chartlegend__swatch s-med"></span>Medium / Low</span>'
        '</div>'
        '<div class="dpc-caption">Items per section · segment color = '
        'evaluated priority · widths scaled to the largest section</div>'
    )


def _checklist_section(category: str, items: list) -> str:
    """One section panel: kit data table with the engine's evaluated
    verdict (status badge), finding, and recommendation per item."""
    rows = []
    for item in items:
        status = str(item.status)
        tone = _STATUS_TONE.get(status, "neutral")
        flag = (
            " " + ck_signal_badge("Red flag", tone="critical")
            if item.is_red_flag else ""
        )
        title_html = (
            f'<div class="dpc-item-title">{_html.escape(item.title)}{flag}</div>'
            f'<div class="dpc-item-desc">{_html.escape(item.description)}</div>'
        )
        finding = (
            f'<span class="dpc-finding">{_html.escape(item.detail)}</span>'
            if item.detail else
            '<span class="dpc-finding">—</span>'
        )
        if status != "PASS" and item.recommendation:
            finding += (
                f'<span class="dpc-rec">Action — '
                f'{_html.escape(item.recommendation)}</span>'
            )
        prio_cls = _PRIORITY_CLASS.get(item.priority, "tone-dim")
        prio_html = (
            f'<span class="dpc-prio {prio_cls}">'
            f'{_html.escape(item.priority)}</span>'
        )
        # Heuristic risk weight derived from the item's status
        # (CRITICAL/WARNING/MISSING/PASS) — NOT a measured corpus
        # failure frequency. Labeled honestly in the column-header
        # tooltip + the footnote under the tables.
        risk_html = ck_fmt_percent(item.corpus_fail_rate)
        rows.append(
            "<tr>"
            + ck_data_cell(title_html)
            + ck_data_cell(finding)
            + ck_data_cell(prio_html)
            + ck_data_cell(risk_html, align="right", mono=True, tone="dim")
            + ck_data_cell(ck_signal_badge(status, tone=tone))
            + "</tr>"
        )

    table = ck_data_table(
        headers=[
            {"label": "Item"},
            {"label": "Finding"},
            {"label": "Priority"},
            # SafeHtml so the kit renders the tooltip markup instead of
            # escaping it; the literal "Risk Wt." header string is
            # pinned by tests/test_diligence_checklist_honesty.py.
            {"label": SafeHtml(ck_help_tooltip(
                "Risk Wt.",
                "Heuristic risk weight derived from the item's evaluated "
                "status (CRITICAL 40% / MISSING 25% / WARNING 20% / "
                "PASS 5%) — not a measured dataset failure rate.",
            )), "align": "right"},
            {"label": "Status"},
        ],
        rows_html="".join(rows),
    )
    return ck_panel(
        table,
        title=f"{category} · {len(items)} items",
        anchor_id=_slug(category),
    )


def _open_questions_panel(questions: list) -> str:
    """The engine's drafted follow-up list — the same centerpiece the
    /diligence/checklist workspace prints into the IC packet."""
    if not questions:
        return ck_affirm_empty(
            headline="No open questions for IC.",
            body=(
                "Every rule the engine can evaluate on this profile "
                "passes — nothing to chase before the memo."
            ),
            cta_text="Open the live checklist workspace",
            cta_href="/diligence/checklist",
        )
    rows = []
    for i, q in enumerate(questions, 1):
        text = q
        badge = ""
        if q.startswith("[CRITICAL] "):
            text = q[len("[CRITICAL] "):]
            badge = ck_signal_badge("Critical", tone="critical")
        elif q.startswith("[MISSING] "):
            text = q[len("[MISSING] "):]
            badge = ck_signal_badge("Missing", tone="neutral")
        rows.append(
            '<div class="dpc-oq-row">'
            f'<span class="dpc-oq-idx">{i:02d}</span>'
            f'<span>{badge}</span>'
            f'<span>{_html.escape(text)}</span>'
            '</div>'
        )
    intro = (
        '<p class="ck-section-body">Every CRITICAL or MISSING verdict '
        'generates one question — this is what the IC packet’s '
        '“Open questions” section prints for a deal of this '
        'profile.</p>'
    )
    return ck_panel(
        intro + "".join(rows),
        title=f"Open questions for IC · {len(questions)}",
        anchor_id="sec-open-questions",
    )


def _input_form(params: dict, sector: str) -> str:
    """Deal-profile GET form. Field names / action / method are the
    page contract — unchanged. Labels are bound to inputs (for/id)."""
    ev = _html.escape(str(params.get("ev", "200.0")), quote=True)
    comm = _html.escape(str(params.get("comm", "0.55")), quote=True)
    ar = _html.escape(str(params.get("ar", "45.0")), quote=True)

    options = "".join(
        f'<option value="{_html.escape(s, quote=True)}"'
        f'{" selected" if s == sector else ""}>{_html.escape(s)}</option>'
        for s in _SECTORS
    )
    return f'''<form method="get" action="/diligence-checklist" class="dpc-form">
  <fieldset class="dpc-fieldset">
    <legend class="dpc-form-legend">Deal profile</legend>
    <div class="dpc-form-grid">
      <div><label class="dpc-label" for="dpc-sector">Sector</label>
        <select id="dpc-sector" name="sector" class="dpc-input">{options}</select></div>
      <div><label class="dpc-label" for="dpc-ev">EV ($M)</label>
        <input id="dpc-ev" name="ev" type="number" step="10" value="{ev}" class="dpc-input"></div>
      <div><label class="dpc-label" for="dpc-comm">Commercial share (0–1)</label>
        <input id="dpc-comm" name="comm" type="number" step="0.01" min="0" max="1" value="{comm}" class="dpc-input"></div>
      <div><label class="dpc-label" for="dpc-ar">AR days (DSO)</label>
        <input id="dpc-ar" name="ar" type="number" step="1" min="0" value="{ar}" class="dpc-input"></div>
      <div><button type="submit" class="dpc-submit">Generate checklist</button></div>
    </div>
  </fieldset>
</form>'''


def _editorial_head(sector: str, r, ev_mm: float, comm_pct: float,
                    ar_days: float, real_corpus: bool) -> str:
    """Kicker → serif H1 → mono meta → italic-first-phrase lede →
    source note. The one masthead; the shell's auto-title backstop
    stays quiet because this block carries the page's <h1>."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = (
        f"{r.total_items} items · {len(r.by_category)} sections · "
        f"EV ${ev_mm:,.2f}M · commercial {ck_fmt_percent(comm_pct)} · "
        f"AR {ar_days:.0f}d · generated {today} UTC"
    )
    lede_body = (
        "the rule engine evaluates a hypothetical "
        f"{_html.escape(sector)} profile into six diligence sections — "
        "every verdict, finding, and open question below is computed "
        "from the profile above. This is the sector-template generator "
        "on public data; the "
        '<a href="/diligence/checklist">live checklist workspace</a> '
        "tracks evidence for a named deal."
    )
    source_note = (
        f"Diligence rule engine · corpus n={r.corpus_deal_count}"
        if real_corpus else
        "Diligence rule engine · no corpus deals loaded"
    )
    return ck_editorial_head(
        eyebrow="PUBLIC DATA · DILIGENCE",
        title=_html.escape(f"Diligence Checklist — {sector}"),
        meta=meta,
        lede_italic_phrase="A checklist generated, not tracked:",
        lede_body=lede_body,
        source_note=source_note,
    )


def _kpi_strip(r, real_corpus: bool) -> str:
    """Six KPI tiles in the kit's responsive strip. Alarm red only
    when a count is actually non-zero; key values carry provenance."""
    total_v = ck_provenance_tooltip(
        "Total items",
        ck_fmt_number(r.total_items),
        explainer=(
            "Count of rule-engine checks evaluated across the six "
            "sections for this deal profile. Each check lands "
            "CRITICAL, WARNING, PASS, or MISSING at generation time."
        ),
    )
    crit_n = r.critical_items
    crit_v = (
        f'<span class="dpc-neg">{ck_fmt_number(crit_n)}</span>'
        if crit_n else ck_fmt_number(crit_n)
    )
    flags_n = r.red_flags_triggered
    flags_fmt = ck_fmt_number(flags_n)
    if flags_n:
        flags_fmt = f'<span class="dpc-neg">{flags_fmt}</span>'
    flags_v = ck_provenance_tooltip(
        "Red flags",
        flags_fmt,
        explainer=(
            "Items whose evaluated status is CRITICAL — material "
            "adverse signals from the rule engine. Zero means no "
            "rule tripped on this profile."
        ),
        inject_css=False,
    )
    corpus_v = ck_provenance_tooltip(
        "Corpus deals",
        ck_fmt_number(r.corpus_deal_count),
        explainer=(
            "Deals in the loaded corpus used for the returns "
            "benchmarks (MOIC/IRR/leverage). At zero, benchmarks "
            "degrade to fixed rule thresholds."
        ),
        inject_css=False,
    )
    medium = r.total_items - r.critical_items - r.high_items
    corpus_sub = (
        "realized-returns benchmark set" if real_corpus else
        '<a href="/data/refresh">none loaded — refresh public data</a>'
    )
    return (
        '<div class="ck-kpi-strip dpc-kpis">'
        + ck_kpi_block("Total Items", total_v,
                       sub="evaluated by the rule engine")
        + ck_kpi_block("Critical", crit_v,
                       sub=("require immediate attention" if crit_n
                            else "no hard stops on this profile"))
        + ck_kpi_block("High", ck_fmt_number(r.high_items),
                       sub="review at next IC")
        + ck_kpi_block("Red Flags", flags_v,
                       sub=("triggered by deal profile" if flags_n
                            else "none triggered"))
        + ck_kpi_block("Medium / Low", ck_fmt_number(medium),
                       sub="monitor + data gaps")
        + ck_kpi_block("Corpus Deals", corpus_v, sub=corpus_sub)
        + '</div>'
    )


def _footnote(real_corpus: bool) -> str:
    corpus_sentence = (
        "Returns benchmarks (MOIC/IRR/leverage vs corpus) and the "
        "corpus-deal count are computed against the deal corpus "
        "(real deals; financials modeled where not publicly disclosed)."
        if real_corpus else
        "No corpus deals are loaded on this deployment — returns "
        "benchmarks degrade to fixed rule thresholds until public "
        "data is refreshed."
    )
    return (
        '<p class="dpc-footnote">'
        '<b>Risk Wt.</b> is a heuristic weight derived from each '
        'item’s evaluated status (CRITICAL/WARNING/MISSING/PASS) '
        '— not a measured corpus failure frequency. '
        f'{corpus_sentence}'
        '</p>'
    )


def render_diligence_checklist(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    if sector not in _SECTORS:
        # Unknown ?sector= values silently rendered a headline claiming
        # a checklist for a sector the engine has no template for; fall
        # back to the default rather than mislabel the output.
        sector = "Physician Group"
    try:
        ev_mm = float(params.get("ev", "200.0"))
    except (ValueError, TypeError):
        ev_mm = 200.0
    try:
        comm_pct = float(params.get("comm", "0.55"))
    except (ValueError, TypeError):
        comm_pct = 0.55
    try:
        ar_days = float(params.get("ar", "45.0"))
    except (ValueError, TypeError):
        ar_days = 45.0

    r = compute_diligence_checklist(sector, ev_mm, comm_pct=comm_pct,
                                    ar_days=ar_days)

    # Honest provenance: returns benchmarks and the corpus-deal count
    # are real-corpus figures when a corpus is loaded; the rule
    # thresholds and per-item "Risk Wt." are heuristic, not measured.
    real_corpus = r.corpus_deal_count > 0
    source_band = ck_source_purpose(
        purpose=("Generate an IC-ready diligence checklist for a "
                 f"{sector} target — flag red flags and open questions "
                 "before the investment committee."),
        universe="corpus" if real_corpus else "derived",
        confidence="derived",
        source=(f"Deals corpus (n={r.corpus_deal_count}; realized MOIC/IRR/"
                "leverage benchmarks) + diligence rule engine"
                if real_corpus else
                "Diligence rule engine (no corpus deals loaded yet)"),
    )

    by_category = r.by_category
    if by_category:
        cats = [c for c in _CATEGORY_ORDER if c in by_category]
        chart = ck_panel(
            _category_bar_svg(by_category) + _chart_legend(),
            title="Items by category",
        )
        anchors = (
            '<nav class="dpc-anchors" aria-label="Checklist sections">'
            + "".join(
                f'<a href="#{_slug(c)}">{_html.escape(c)}</a>'
                for c in cats)
            + '<a href="#sec-open-questions">Open questions</a>'
            + '</nav>'
        )
        sections = "".join(
            _checklist_section(c, by_category[c]) for c in cats)
        main = (
            chart
            + anchors
            + f'<div class="dpc-sections">{sections}</div>'
            + _footnote(real_corpus)
            + _open_questions_panel(r.open_questions)
        )
    else:
        main = ck_empty_state(
            "No checklist items generated.",
            (
                "The rule engine returned no evaluable items for this "
                "profile. Adjust the deal profile above and regenerate."
            ),
            eyebrow="EMPTY RESULT",
            cta_label="Reset to defaults",
            cta_href="/diligence-checklist",
        )

    content = (
        _scoped_styles()
        + _editorial_head(sector, r, ev_mm, comm_pct, ar_days, real_corpus)
        + source_band
        + _input_form(params, sector)
        + _kpi_strip(r, real_corpus)
        + main
        + ck_next_section(
            "Open the live checklist workspace",
            "/diligence/checklist",
            eyebrow="Up next",
            italic_word="workspace",
        )
        + ck_page_actions()
    )

    return chartis_shell(
        content,
        title=f"Diligence Checklist — {sector}",
        active_nav="/diligence-checklist",
    )
