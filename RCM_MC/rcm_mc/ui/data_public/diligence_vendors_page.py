"""Diligence Vendor Directory — /diligence-vendors."""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_bar_row, ck_data_cell, ck_data_table,
    ck_empty_state, ck_fmt_number, ck_fmt_percent, ck_illustrative_note,
    ck_kpi_block, ck_narrative_band, ck_page_title, ck_provenance_tooltip,
    ck_scatter, ck_section_header, ck_signal_badge, ck_value_anchor,
)
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

# Page-scoped chrome — chart captions only; everything else is kit classes.
# 11px + --sc-text-dim (not 10px faint) so the caption clears AA contrast,
# matching the kit's .ck-illus-note-body treatment.
_EXTRA_CSS = (
    ".dv-chart-caption{font-family:var(--sc-mono,'JetBrains Mono',monospace);"
    "font-size:11px;color:var(--sc-text-dim,#465366);margin:6px 0 18px;}"
)


# ── Shared tone helpers ──────────────────────────────────────────────
# ONE threshold pair per metric, mapped once to cell tones and once to
# chart tones, so the scatter and the tables can never pass two
# contradictory judgments on the same number (the pre-redesign page
# toned quality >=80 amber in the chart but >=82 neutral in the table).

def _quality_band(score: float) -> str:
    if score >= 88:
        return "strong"
    if score >= 82:
        return "solid"
    return "flat"


def _nps_band(nps: float) -> str:
    if nps >= 82:
        return "strong"
    if nps >= 75:
        return "solid"
    return "flat"


_CELL_TONE = {"strong": "pos", "solid": "acc", "flat": "dim"}
_CHART_TONE = {"strong": "positive", "solid": "teal", "flat": "navy"}


def _grade_tone(rating: str) -> str:
    """Overall letter grade → cell tone (A tier green, A- teal, below dim)."""
    grade = rating.strip()
    if grade.startswith("A-"):
        return "acc"
    if grade.startswith("A"):
        return "pos"
    return "dim"


def _scorecards_scatter(items) -> str:
    """Quadrant — value-for-money vs quality-of-insights, so the best
    vendors (upper-right) and weak ones (lower-left) separate visually."""
    if not items:
        return ""
    import statistics
    pts, xs, ys = [], [], []
    for s in items:
        tone = _CHART_TONE[_quality_band(s.quality_of_insights)]
        pts.append((s.value_for_money, s.quality_of_insights, s.firm, tone))
        xs.append(s.value_for_money)
        ys.append(s.quality_of_insights)
    return ck_scatter(
        pts, x_label='Value for money', y_label='Quality of insights',
        x_ref=(statistics.median(xs) if xs else None),
        y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a vendor · upper-right = high quality + high value '
                '· tone = quality of insights (≥88 green, ≥82 teal)',
    )


def _vendors_chart(items) -> str:
    """Lead chart — panel vendors ranked by 24-month deal engagements.

    Tone encodes the deal-team NPS band rather than tier: 25 of the 30
    panel vendors are Tier 1, so a tier tone rendered a near-monochrome
    chart. The share denominator is the FULL panel (not the top-14
    slice) so this chart and the category chart read as one statistic.
    """
    if not items:
        return ""
    top = sorted(items, key=lambda v: v.deals_last_24mo, reverse=True)[:14]
    total = sum(v.deals_last_24mo for v in items) or 1
    rows = "".join(
        ck_bar_row(
            f"{v.firm} · {v.category}", f"{v.deals_last_24mo} deals",
            v.deals_last_24mo / total * 100.0,
            tone=_CHART_TONE[_nps_band(v.nps_from_deal_teams)],
        )
        for v in top
    )
    return (rows + '<p class="dv-chart-caption">Bar = share of panel '
            'engagements (24 mo) · top 14 shown · tone = deal-team NPS '
            '(≥82 green, ≥75 teal)</p>')


def _vendors_table(items) -> str:
    headers = [
        {"label": "Firm", "align": "left"},
        {"label": "Category", "align": "left"},
        {"label": "Tier", "align": "center"},
        {"label": "Deals (24 mo)", "align": "right"},
        {"label": "Median Spend ($K)", "align": "right"},
        {"label": "Turnaround (days)", "align": "right"},
        {"label": "NPS", "align": "right"},
        {"label": "Quality", "align": "right"},
        {"label": "Partner Contact", "align": "left"},
    ]
    rows = []
    for v in items:
        nps_band = _nps_band(v.nps_from_deal_teams)
        q_band = _quality_band(v.quality_score)
        cells = [
            ck_data_cell(_html.escape(v.firm), mono=True, weight=600),
            ck_data_cell(_html.escape(v.category), mono=True, tone="dim"),
            ck_data_cell(
                ck_signal_badge(v.tier, tone=("positive" if v.tier == "Tier 1" else "neutral")),
                align="center",
            ),
            ck_data_cell(str(v.deals_last_24mo), align="right", mono=True, weight=600),
            # Spend is a cost, not a breach — neutral mono, never alarm red.
            ck_data_cell(f"${v.median_spend_per_deal_k:,.2f}", align="right", mono=True),
            ck_data_cell(str(v.turnaround_days), align="right", mono=True, tone="dim"),
            # Weight doubles as the non-color cue for the strongest band.
            ck_data_cell(str(v.nps_from_deal_teams), align="right", mono=True,
                         tone=_CELL_TONE[nps_band],
                         weight=(700 if nps_band == "strong" else None)),
            ck_data_cell(str(v.quality_score), align="right", mono=True,
                         tone=_CELL_TONE[q_band],
                         weight=(700 if q_band == "strong" else None)),
            ck_data_cell(_html.escape(v.partner_contact), tone="dim"),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return ck_data_table(headers=headers, rows_html="".join(rows))


def _categories_chart(items) -> str:
    """Summary chart — vendor categories ranked by spend (tone flags
    single-vendor concentration above 50% of a category's deals)."""
    if not items:
        return ""

    def _tone(c):
        if c.concentration_pct > 0.50:
            return "warning"
        if c.concentration_pct > 0.35:
            return "teal"
        return "navy"

    ordered = sorted(items, key=lambda c: c.total_spend_mm, reverse=True)
    total = sum(c.total_spend_mm for c in ordered) or 1.0
    rows = "".join(
        ck_bar_row(
            f"{c.category} ({c.total_deals} deals)", f"${c.total_spend_mm:,.2f}M",
            c.total_spend_mm / total * 100.0, tone=_tone(c),
        )
        for c in ordered
    )
    return (rows + '<p class="dv-chart-caption">Bar = share of panel spend '
            'by category (24 mo) · value = spend ($M) · tone = top-vendor '
            'concentration (&gt;50% amber)</p>')


def _categories_table(items) -> str:
    headers = [
        {"label": "Category", "align": "left"},
        {"label": "Total Deals", "align": "right"},
        {"label": "Total Spend ($M)", "align": "right"},
        {"label": "Median Spend ($K)", "align": "right"},
        {"label": "Top Vendor", "align": "left"},
        {"label": "Concentration", "align": "right"},
    ]
    bar_max = max((c.total_spend_mm for c in items), default=1.0) or 1.0
    rows = []
    for c in items:
        cells = [
            ck_data_cell(_html.escape(c.category), mono=True, weight=600),
            ck_data_cell(str(c.total_deals), align="right", mono=True),
            ck_data_cell(f"${c.total_spend_mm:,.2f}", align="right", mono=True,
                         weight=600, bar=c.total_spend_mm / bar_max * 100),
            ck_data_cell(f"${c.median_spend_k:,.2f}", align="right", mono=True, tone="dim"),
            ck_data_cell(_html.escape(c.top_vendor), mono=True),
            # 13 of 19 categories are single-vendor (trivially 100%), so a
            # threshold color here would read as a column of alarms — the
            # category chart's tone already flags true concentration risk.
            ck_data_cell(ck_fmt_percent(c.concentration_pct), align="right", mono=True),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return ck_data_table(headers=headers, rows_html="".join(rows))


def _scorecards_table(items) -> str:
    headers = [
        {"label": "Firm", "align": "left"},
        {"label": "On-Time", "align": "right"},
        {"label": "Insights", "align": "right"},
        {"label": "Responsiveness", "align": "right"},
        {"label": "Value", "align": "right"},
        {"label": "Overall", "align": "center"},
    ]
    rows = []
    for s in items:
        q_band = _quality_band(s.quality_of_insights)
        cells = [
            ck_data_cell(_html.escape(s.firm), mono=True, weight=600),
            ck_data_cell(ck_fmt_percent(s.on_time_delivery_pct), align="right", mono=True,
                         tone=("pos" if s.on_time_delivery_pct >= 0.92 else "dim"),
                         weight=(600 if s.on_time_delivery_pct >= 0.92 else None)),
            # Same metric as the scatter above — same tone helper, so one
            # number never gets two judgments on the same page.
            ck_data_cell(str(s.quality_of_insights), align="right", mono=True,
                         tone=_CELL_TONE[q_band],
                         weight=(700 if q_band == "strong" else None)),
            ck_data_cell(str(s.responsiveness), align="right", mono=True),
            ck_data_cell(str(s.value_for_money), align="right", mono=True),
            ck_data_cell(_html.escape(s.overall_rating), align="center", mono=True,
                         tone=_grade_tone(s.overall_rating), weight=600),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return ck_data_table(headers=headers, rows_html="".join(rows))


def _pipeline_table(items) -> str:
    headers = [
        {"label": "Firm", "align": "left"},
        {"label": "Category", "align": "left"},
        {"label": "Referred By", "align": "left"},
        # "Meeting date", not "Meeting" — the fixture dates are historical
        # first-contact dates, not upcoming appointments.
        {"label": "Meeting date", "align": "left"},
        {"label": "Stage", "align": "left"},
        {"label": "Likelihood", "align": "right"},
    ]
    rows = []
    for p in items:
        l_band = ("strong" if p.likelihood_engage_pct >= 0.60
                  else "solid" if p.likelihood_engage_pct >= 0.45 else "flat")
        cells = [
            ck_data_cell(_html.escape(p.firm), mono=True, weight=600),
            ck_data_cell(_html.escape(p.category), mono=True, tone="dim"),
            ck_data_cell(_html.escape(p.referred_by), tone="dim"),
            # Plain mono — teal on a date reads as a link in this design
            # language, and these are records, not actions.
            ck_data_cell(_html.escape(p.meeting_scheduled), mono=True),
            ck_data_cell(_html.escape(p.stage), tone="dim"),
            ck_data_cell(ck_fmt_percent(p.likelihood_engage_pct), align="right", mono=True,
                         tone=_CELL_TONE[l_band],
                         weight=(700 if l_band == "strong" else None)),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return ck_data_table(headers=headers, rows_html="".join(rows))


def _phases_table(items) -> str:
    headers = [
        {"label": "Deal Phase", "align": "left"},
        {"label": "Categories", "align": "left"},
        {"label": "Typical Spend ($M)", "align": "right"},
        {"label": "Timeline (weeks)", "align": "right"},
        {"label": "Notes", "align": "left"},
    ]
    rows = []
    for p in items:
        cells = [
            ck_data_cell(_html.escape(p.phase), mono=True, weight=600),
            ck_data_cell(_html.escape(p.categories), tone="dim"),
            ck_data_cell(f"${p.typical_spend_mm:,.2f}", align="right", mono=True, weight=600),
            ck_data_cell(str(p.timeline_weeks), align="right", mono=True, tone="dim"),
            ck_data_cell(_html.escape(p.notes), tone="dim"),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return ck_data_table(headers=headers, rows_html="".join(rows))


def _panel_read(r, tier_1_count: int) -> str:
    """Closing memo paragraph, derived ENTIRELY from the live result.

    The pre-redesign thesis hardcoded "14 categories" two inches under a
    KPI showing 19, named five "Tier 1 partners" when 25 of 30 vendors
    were Tier 1, and quoted pipeline percentages that could drift from
    the table above. Every figure here is computed from ``r``; claims
    with no backing field were cut.
    """
    if not r.vendors:
        return ""
    parts = [
        f"{r.total_vendors} active vendors across {len(r.categories)} categories; "
        f"${r.total_spend_ltm_mm:,.2f}M spend over 24 months at an average "
        f"deal-team NPS of {r.avg_nps}. {tier_1_count} of {r.total_vendors} "
        f"panel vendors are Tier 1."
    ]
    if r.pipeline:
        top = sorted(r.pipeline, key=lambda p: p.likelihood_engage_pct, reverse=True)[:3]
        named = ", ".join(
            f"{p.firm} ({p.category}) at {ck_fmt_percent(p.likelihood_engage_pct)}"
            for p in top
        )
        parts.append(
            f" Pipeline of {len(r.pipeline)} new vendors in vetting; "
            f"highest-likelihood adds: {named}."
        )
    # Look the phase up by name — a positional index silently quotes the
    # wrong phase's spend if the data module reorders its list.
    deep = next((p for p in r.phase_spend if "Deep Diligence" in p.phase), None)
    if deep is not None:
        parts.append(
            f" Spend concentrates in the {deep.phase} phase at "
            f"${deep.typical_spend_mm:,.2f}M typical over {deep.timeline_weeks} weeks."
        )
    return ck_section_header("Panel read") + ck_narrative_band("".join(parts))


def render_diligence_vendors(params: dict = None) -> str:
    from rcm_mc.data_public.diligence_vendors import compute_diligence_vendors
    r = compute_diligence_vendors()

    tier_1_count = sum(1 for v in r.vendors if v.tier == "Tier 1")

    spend_value = ck_provenance_tooltip(
        "Total spend (24 mo)",
        f"${r.total_spend_ltm_mm:,.2f}M",
        explainer=(
            "Sum across the panel of each vendor's 24-month deal "
            "engagements times its median spend per deal. Curated panel "
            "figures, not invoiced actuals."
        ),
    )
    nps_value = ck_provenance_tooltip(
        "Avg NPS",
        str(r.avg_nps),
        explainer=(
            "Mean net promoter score from post-engagement deal-team "
            "surveys, on the standard -100 to +100 scale, averaged across "
            "all panel vendors."
        ),
        inject_css=False,
    )
    corpus_value = ck_provenance_tooltip(
        "Corpus deals",
        ck_fmt_number(r.corpus_deal_count),
        explainer=(
            "Size of the realized-deal corpus the platform calibrates "
            "against — shown for scale next to the panel's engagement "
            "counts, not a count of deals this panel served."
        ),
        inject_css=False,
    )

    # Labels are kept to one line at the 8-up strip's tile width — a
    # wrapped label pushes its value below the siblings' baseline and
    # the whole number row reads ragged ("Vendors on Panel" and
    # "Pipeline Vendors" both wrapped at 1440).
    kpi_strip = (
        ck_kpi_block("Panel Vendors", str(r.total_vendors), "active across the firm", "") +
        ck_kpi_block("Deals Covered", str(r.total_deals_covered), "engagements over 24 mo", "") +
        ck_kpi_block("Total Spend", spend_value, "over 24 mo", "") +
        ck_kpi_block("Avg NPS", nps_value, "deal-team surveys", "") +
        ck_kpi_block("Tier 1", str(tier_1_count), f"of {r.total_vendors} on panel", "") +
        ck_kpi_block("Categories", str(len(r.categories)), "diligence workstreams", "") +
        ck_kpi_block("In Pipeline", str(len(r.pipeline)), "vendors in vetting", "") +
        ck_kpi_block("Corpus Deals", corpus_value, "calibration corpus", "")
    )

    # No delta/opportunity/target facts: those slots render under fixed
    # "vs benchmark" / "opportunity" labels, and panel composition is
    # neither — the KPI subs above carry the composition honestly.
    value_anchor = ck_value_anchor(
        "Diligence Panel Spend",
        f"${r.total_spend_ltm_mm:,.2f}M over 24 mo",
        tone="teal",
    )

    # Section h2s are sentence-case — the diligence-family convention
    # ("Items by phase", "Transformation log", "Diligence memo"); Title
    # Case stays reserved for pinned product terms (e.g. the QoE memo's
    # "Quality of Revenue" sections on /diligence/benchmarks).
    if r.vendors:
        vendors_section = (
            ck_section_header("Active vendor panel",
                              "Ranked by 24-month deal engagements", len(r.vendors))
            + _vendors_chart(r.vendors) + _vendors_table(r.vendors)
        )
    else:
        vendors_section = ck_empty_state(
            "No vendors on the panel yet.",
            "Import vendor engagement data to populate the panel, "
            "category spend, and scorecards.",
            eyebrow="VENDOR PANEL",
            cta_label="Import vendor data", cta_href="/import",
        )

    if r.categories:
        categories_section = (
            ck_section_header("Category spend analysis",
                              "Panel spend by diligence workstream", len(r.categories))
            + _categories_chart(r.categories) + _categories_table(r.categories)
        )
    else:
        categories_section = ck_empty_state(
            "No category spend yet.",
            "Category rollups appear once vendors are on the panel.",
        )

    if r.scorecards:
        scorecards_section = (
            ck_section_header("Top vendor scorecards",
                              "Post-engagement survey scores", len(r.scorecards))
            + _scorecards_scatter(r.scorecards) + _scorecards_table(r.scorecards)
        )
    else:
        scorecards_section = ck_empty_state(
            "No scorecards yet.",
            "Scorecards appear after the first post-engagement deal-team survey.",
        )

    if r.pipeline:
        pipeline_section = (
            ck_section_header("New vendor pipeline",
                              "Prospects in vetting", len(r.pipeline))
            + _pipeline_table(r.pipeline)
        )
    else:
        pipeline_section = ck_empty_state(
            "No vendors in the pipeline.",
            "Prospects appear here once a first meeting is logged.",
        )

    if r.phase_spend:
        phases_section = (
            ck_section_header("Spend by deal phase",
                              "Typical diligence budget through the deal lifecycle")
            + _phases_table(r.phase_spend)
        )
    else:
        phases_section = ck_empty_state(
            "No phase spend profile yet.",
            "Phase-level budgets appear once engagement data is imported.",
        )

    page_title = ck_page_title(
        "Diligence Vendor Directory",
        # "DILIGENCE · X" eyebrow taxonomy — matches the data_public
        # diligence siblings (/diligence-checklist "DILIGENCE · CHECKLIST
        # GENERATOR", antitrust screener, board governance).
        eyebrow="DILIGENCE · VENDOR PANEL",
        # Short scannable fragments — the meta row is CSS-uppercased mono,
        # so a full sentence renders as a dense all-caps block.
        meta=(f"{r.total_vendors} vendors · {len(r.categories)} categories · "
              f"${r.total_spend_ltm_mm:,.2f}M spend (24 mo) · "
              f"{len(r.pipeline)} in pipeline"),
    )

    # Title → illustrative note adjacency is load-bearing for the kit's
    # masthead rhythm (the gap only collapses when the note directly
    # follows the title), so the data-required panel renders after it.
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("vendor panel figures")}
  {data_required_panel(P, title="Diligence Vendors", needed=[("firm", "vendor firm name"), ("category", "diligence workstream / category"), ("tier", "panel tier (Tier 1-3)"), ("spend_per_deal", "median spend per deal ($K)"), ("turnaround_days", "typical turnaround (days)"), ("nps", "deal-team NPS (-100 to +100)"), ("quality_score", "quality score (0-100)")], template="diligence_vendors_template.csv", request_from="Deal team / deal lead", activates="the live vendor panel, category spend rollups, and post-engagement scorecards", guide_hint="What diligence-vendor data do I need to upload?")}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  {value_anchor}
  {vendors_section}
  {categories_section}
  {scorecards_section}
  {pipeline_section}
  {phases_section}
  {_panel_read(r, tier_1_count)}
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_next_section, ck_page_actions
    # "Up next" chapter footer — every diligence-family page chains to
    # the next logical surface; the vendor panel hands off to the
    # public checklist generator (its /diligence-checklist sibling).
    body = body + ck_next_section(
        "Generate a diligence checklist",
        "/diligence-checklist",
        eyebrow="Up next",
        italic_word="checklist",
    )
    body = body + ck_page_actions()
    # NOTE for the kit owner: "/diligence-vendors" is not in
    # _SUB_SECTION_MAP, so no breadcrumbs / sub-nav rail resolve for this
    # route. Registering it under the Diligence section is a kit change
    # (out of scope for this page file).
    return chartis_shell(body, "Diligence Vendors", active_nav="/diligence-vendors",
        extra_css=_EXTRA_CSS,
        editorial_intro={
            "eyebrow": "VENDOR PANEL",
            "headline": "Which diligence vendors earn the next engagement.",
            "italic_word": "earn",
            "body": (
                "Two years of panel spend, deal-team NPS, and turnaround "
                "across every diligence workstream — with the vetting "
                "pipeline for the next engagement underneath."
            ),
        })
