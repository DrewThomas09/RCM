"""Diligence section landing page.

Route: ``GET /diligence``. Was 404 before — the top-nav DILIGENCE
button pointed at a path with no handler, so partners hit a dead end.

Now renders an editorial section index that groups the 25 RCM
diligence surfaces into four pillars that match how a partner
mentally segments diligence work:

  1. Profile & Health     — start-of-diligence reads
  2. Thesis & Playbook    — value-creation framework
  3. Audit & Stress       — pressure-test the assumptions
  4. Exit & Synthesis     — convert the diligence into IC output

Each surface lists its label + one-line explainer so partners scan
purpose, not just name. Spec mirrors chartis.com section landings.
"""
from __future__ import annotations

import html as _html
from typing import List, Mapping

from ._chartis_kit import (
    chartis_shell, ck_next_section, ck_page_title, ck_panel,
    ck_section_intro,
)


_PILLARS: List[Mapping[str, object]] = [
    {
        "title": "Profile & Health",
        "eyebrow": "START OF DILIGENCE",
        "body": (
            "First-pass reads on a target — financials, claims, "
            "physician footprint, payer mix. Open these to build "
            "the baseline picture before forming a thesis."
        ),
        "links": [
            {"href": "/diligence/deal",
             "label": "Deal Profile",
             "blurb": "Unified per-deal source of truth."},
            {"href": "/diligence/hcris-xray",
             "label": "HCRIS X-Ray",
             "blurb": "Full filing-level cost-report drill-down."},
            {"href": "/diligence/benchmarks",
             "label": "Benchmarks",
             "blurb": "Target vs vintage / sector / size cohort."},
            {"href": "/diligence/physician-attrition",
             "label": "Physician Attrition",
             "blurb": "MD-Compass turnover risk by specialty."},
            {"href": "/diligence/physician-eu",
             "label": "Provider Economics",
             "blurb": "Encounter mix + per-physician profitability."},
            {"href": "/diligence/management",
             "label": "Management",
             "blurb": "Leadership tenure, comp, change history."},
        ],
    },
    {
        "title": "Thesis & Playbook",
        "eyebrow": "VALUE-CREATION FRAMEWORK",
        "body": (
            "Where the deal makes money. Each surface ladders the "
            "RCM levers (denial reduction, AR compression, payer "
            "negotiation, capacity) into bridge dollars and tests "
            "the assumptions the IC will challenge."
        ),
        "links": [
            {"href": "/diligence/thesis-pipeline",
             "label": "Thesis Pipeline",
             "blurb": "One-button full diligence chain."},
            {"href": "/diligence/checklist",
             "label": "Checklist",
             "blurb": "Track open questions through to resolution."},
            {"href": "/diligence/ingest",
             "label": "Ingestion",
             "blurb": "Upload data-room files, parse to fixtures."},
            {"href": "/diligence/value",
             "label": "Value Creation",
             "blurb": "RCM-lever EBITDA bridge per initiative."},
            {"href": "/diligence/root-cause",
             "label": "Root Cause",
             "blurb": "Why is the metric off — denial reasons drilled."},
            {"href": "/diligence/denial-prediction",
             "label": "Denial Predict",
             "blurb": "ML scores future denials by claim line."},
        ],
    },
    {
        "title": "Audit & Stress",
        "eyebrow": "PRESSURE-TEST THE ASSUMPTIONS",
        "body": (
            "Before IC, hammer the model. Counterfactuals, "
            "covenant stress, payer concentration, bankruptcy "
            "exposure. Anything that reveals downside that the "
            "base case quietly assumed away."
        ),
        "links": [
            {"href": "/diligence/risk-workbench?demo=steward",
             "label": "Risk Workbench",
             "blurb": "Multi-axis sensitivity scenarios."},
            {"href": "/diligence/counterfactual",
             "label": "Counterfactual",
             "blurb": "What if the lever didn't work?"},
            {"href": "/diligence/compare",
             "label": "Compare",
             "blurb": "Two deals side-by-side on every metric."},
            {"href": "/screening/bankruptcy-survivor",
             "label": "Bankruptcy Scan",
             "blurb": "Distress signals across your watchlist."},
            {"href": "/diligence/payer-stress",
             "label": "Payer Stress",
             "blurb": "Top-payer concentration → revenue at risk."},
            {"href": "/diligence/covenant-stress",
             "label": "Covenant Stress",
             "blurb": "EBITDA cushion before leverage covenant trips."},
            {"href": "/diligence/bridge-audit",
             "label": "Bridge Audit",
             "blurb": "Tie every bridge lever to a source row."},
            {"href": "/diligence/deal-mc",
             "label": "Deal MC",
             "blurb": "Per-deal Monte Carlo with overlay shocks."},
            {"href": "/diligence/deal-autopsy",
             "label": "Deal Autopsy",
             "blurb": "Decompose realized return vs underwriting."},
        ],
    },
    {
        "title": "Exit & Synthesis",
        "eyebrow": "CONVERT TO IC OUTPUT",
        "body": (
            "Diligence ends when it lands on a partner's desk. "
            "QoE memo, IC packet, exit-timing read, regulatory "
            "calendar. These are the deliverables the rest of the "
            "platform feeds."
        ),
        "links": [
            {"href": "/diligence/qoe-memo",
             "label": "QoE Memo",
             "blurb": "Quality-of-earnings narrative + drivers."},
            {"href": "/diligence/ic-packet",
             "label": "IC Packet",
             "blurb": "Partner-ready memo + exhibits in one click."},
            {"href": "/diligence/exit-timing",
             "label": "Exit Timing",
             "blurb": "Hold-period optimal exit window."},
            {"href": "/diligence/regulatory-calendar",
             "label": "Reg Calendar",
             "blurb": "CMS rule cycles overlaid on hold."},
            {"href": "/engagements",
             "label": "Engagements",
             "blurb": "Track active diligence engagements."},
        ],
    },
]


def render_diligence_index() -> str:
    """Render the /diligence section landing page.

    Spec: replicate chartis.com /insights triplet (eyebrow + serif
    title + body) but for an internal navigation index. Eight visible
    pillars on chartis.com → four here, sized to one screen-fold so
    the partner reads "what's in this section" without scrolling.
    """
    pillars_html: List[str] = []
    for p in _PILLARS:
        link_rows: List[str] = []
        for link in p["links"]:
            link_rows.append(
                '<a class="ck-dil-link" '
                f'href="{_html.escape(link["href"], quote=True)}">'
                '<div class="ck-dil-link-row">'
                f'<span class="ck-dil-link-label">'
                f'{_html.escape(link["label"])}</span>'
                '<span class="ck-dil-link-arrow" aria-hidden="true">'
                '&rarr;</span>'
                '</div>'
                f'<div class="ck-dil-link-blurb">'
                f'{_html.escape(link["blurb"])}</div>'
                '</a>'
            )
        pillar_inner = (
            '<header class="ck-dil-pillar-head">'
            f'<div class="ck-eyebrow">{_html.escape(p["eyebrow"])}</div>'
            f'<h2 class="ck-dil-pillar-title">{_html.escape(p["title"])}</h2>'
            f'<p class="ck-dil-pillar-body">{_html.escape(p["body"])}</p>'
            '</header>'
            '<div class="ck-dil-link-list">'
            + "".join(link_rows)
            + '</div>'
        )
        pillars_html.append(
            ck_panel(pillar_inner)
        )

    title = ck_page_title(
        "Diligence",
        eyebrow="RCM PLAYBOOK",
        meta=(
            f"{sum(len(p['links']) for p in _PILLARS)} surfaces · "
            "grouped into four pillars"
        ),
    )
    intro = ck_section_intro(
        eyebrow="RCM DILIGENCE PLAYBOOK",
        headline=(
            "Where the diligence work actually lives."
        ),
        italic_word="lives",
        body=(
            "Twenty-four diligence surfaces grouped into the four "
            "pillars a partner mentally walks: profile the target, "
            "frame the thesis, stress the assumptions, then "
            "synthesize for IC. Each tile names the surface and the "
            "one-line job it does."
        ),
    )

    css = (
        '<style>'
        '.ck-dil-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));'
        'gap:24px;margin:0 0 24px;}'
        '@media (max-width:1100px){.ck-dil-grid{grid-template-columns:1fr;}}'
        '.ck-dil-pillar{background:#fff;border:1px solid var(--sc-rule,#d6cfc0);'
        'border-radius:2px;padding:24px 26px;display:flex;flex-direction:column;'
        'gap:18px;box-shadow:var(--sc-shadow-1,0 1px 2px rgba(11,32,55,0.04));}'
        '.ck-dil-pillar-head{display:flex;flex-direction:column;gap:8px;'
        'border-bottom:1px solid var(--sc-rule,#d6cfc0);padding-bottom:16px;}'
        '.ck-dil-pillar-title{font-family:var(--sc-serif,Georgia,serif);'
        'font-weight:500;font-size:22px;color:var(--sc-navy,#0b2341);'
        'margin:4px 0 0;letter-spacing:-0.01em;}'
        '.ck-dil-pillar-body{font-family:var(--sc-serif,Georgia,serif);'
        'font-size:13.5px;line-height:1.6;color:var(--sc-text-dim,#465366);'
        'margin:0;max-width:48ch;}'
        '.ck-dil-link-list{display:flex;flex-direction:column;}'
        '.ck-dil-link{display:block;text-decoration:none;color:inherit;'
        'padding:12px 0;border-bottom:1px solid var(--sc-rule,#d6cfc0);'
        'transition:padding-left 0.12s,background 0.12s;'
        'margin:0 -12px;padding-left:12px;padding-right:12px;border-radius:2px;}'
        '.ck-dil-link:last-child{border-bottom:0;}'
        '.ck-dil-link:hover{background:var(--sc-bone,#ece5d6);'
        'padding-left:16px;}'
        '.ck-dil-link:hover .ck-dil-link-arrow{color:var(--sc-teal,#155752);'
        'transform:translateX(2px);}'
        '.ck-dil-link-row{display:flex;align-items:baseline;'
        'justify-content:space-between;gap:12px;}'
        '.ck-dil-link-label{font-family:var(--sc-sans,Inter,sans-serif);'
        'font-weight:600;font-size:14px;color:var(--sc-navy,#0b2341);}'
        '.ck-dil-link-arrow{font-family:var(--sc-sans);font-size:14px;'
        'color:var(--sc-text-faint,#7a8699);'
        'transition:color 0.12s,transform 0.12s;}'
        '.ck-dil-link-blurb{font-family:var(--sc-serif,Georgia,serif);'
        'font-size:12.5px;color:var(--sc-text-dim,#465366);'
        'line-height:1.45;margin-top:4px;}'
        '</style>'
    )

    next_up = ck_next_section(
        "Open the portfolio-wide question ledger",
        "/diligence/questions",
        eyebrow="Continue —",
        italic_word="question",
    )
    body = (
        f"{css}"
        f"{title}"
        f"{intro}"
        '<div class="ck-dil-grid">'
        + "".join(pillars_html)
        + '</div>'
        + next_up
    )

    return chartis_shell(
        body, "Diligence",
        active_nav="/diligence",
        subtitle="RCM diligence playbook · 24 surfaces grouped into 4 pillars",
    )
