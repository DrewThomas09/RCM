"""Research Library page — /research.

Curated listing of partner-facing research surfaces — methodology
hubs, frameworks, healthcare-PE deep-dives, and conference roadmaps
that already live elsewhere in the platform but didn't have a single
landing page indexing them.

Renders the chartis Insights triplet (search hero + filter sidebar +
results header) so it sits visually alongside `/library` and `/notes`
as a sibling content-listing surface. The catalog is curated in code
for now (small list, evolves slowly); a future iteration can move it
to a SQLite table once the editorial team needs to publish without
shipping a deploy.
"""
from __future__ import annotations

import html as _html
import urllib.parse
from typing import Any, Dict, List, Optional


# Curated research catalog. Order = featured / most-recent first.
# `topic` and `kind` populate the filter sidebar facets. Adding a
# new entry here is the supported way to publish research before
# the catalog moves to a DB-backed table.
RESEARCH_ENTRIES: List[Dict[str, str]] = [
    {
        "title": "Methodology Hub",
        "summary": (
            "How the platform decides — every model, calibration, "
            "and scoring rubric in one navigable index."
        ),
        "href": "/methodology",
        "topic": "Methodology",
        "kind": "Reference",
    },
    {
        "title": "Conference Roadmap",
        "summary": (
            "Healthcare-PE conferences, partner attendance plan, "
            "and the deal-flow they tend to surface."
        ),
        "href": "/conferences",
        "topic": "Industry",
        "kind": "Field Notes",
    },
    {
        "title": "PE Intelligence Hub",
        "summary": (
            "278 partner-reflex modules — how the platform codifies "
            "judgment from screening through exit."
        ),
        "href": "/pe-intelligence",
        "topic": "Frameworks",
        "kind": "Reference",
    },
    {
        "title": "Bear Cases",
        "summary": (
            "Anti-thesis catalog — why a deal might not work, sliced "
            "by sector and exit regime."
        ),
        "href": "/bear-cases",
        "topic": "Frameworks",
        "kind": "Case Studies",
    },
    {
        "title": "Comparable Outcomes",
        "summary": (
            "Realized-outcome distributions on the deal corpus, "
            "filtered to comparables of the focused deal."
        ),
        "href": "/comparable-outcomes",
        "topic": "Benchmarks",
        "kind": "Case Studies",
    },
    {
        "title": "Regulatory Calendar",
        "summary": (
            "Upcoming healthcare-policy windows that move PE thesis "
            "value — by sector and quarter."
        ),
        "href": "/regulatory-calendar",
        "topic": "Industry",
        "kind": "Reference",
    },
    {
        "title": "Market Intelligence",
        "summary": (
            "Sector concentration, payer dynamics, and competitive "
            "intel pulled from the live corpus."
        ),
        "href": "/market-intel",
        "topic": "Benchmarks",
        "kind": "Field Notes",
    },
    {
        "title": "Causal & Counterfactual",
        "summary": (
            "Treatment-effect frameworks for "
            "asking what-if on portfolio interventions."
        ),
        "href": "/benchmarks",
        "topic": "Methodology",
        "kind": "Frameworks",
    },
    {
        "title": "Notes",
        "summary": (
            "Analyst voice — running working notes, hypotheses, and "
            "open questions across the portfolio."
        ),
        "href": "/notes",
        "topic": "Field Notes",
        "kind": "Field Notes",
    },
    {
        "title": "Sector Momentum",
        "summary": (
            "Rolling sector velocity — which healthcare verticals are "
            "accelerating, plateauing, or rolling over."
        ),
        "href": "/sector-momentum",
        "topic": "Benchmarks",
        "kind": "Reference",
    },
    {
        "title": "IRR Dispersion",
        "summary": (
            "Distribution of realized IRRs across the corpus, sliced "
            "by vintage, sector, and exit regime."
        ),
        "href": "/irr-dispersion",
        "topic": "Benchmarks",
        "kind": "Reference",
    },
    {
        "title": "Hold Analysis",
        "summary": (
            "How long a deal should run — hold-period distributions "
            "and exit-window readouts across the corpus."
        ),
        "href": "/hold-analysis",
        "topic": "Benchmarks",
        "kind": "Reference",
    },
    {
        "title": "Corpus Backtest",
        "summary": (
            "Replay screening rules against the real-deal corpus to "
            "see what the platform would have surfaced."
        ),
        "href": "/corpus-backtest",
        "topic": "Methodology",
        "kind": "Frameworks",
    },
    {
        "title": "Backtest",
        "summary": (
            "Single-thesis backtest — apply one rule across the "
            "deal universe and inspect the cohort it picks."
        ),
        "href": "/backtest",
        "topic": "Methodology",
        "kind": "Frameworks",
    },
]


def _build_url(
    *,
    base: str = "/research",
    q: str = "",
    topic: str = "",
    kind: str = "",
) -> str:
    pairs = [(k, v) for k, v in (("q", q), ("topic", topic), ("kind", kind)) if v]
    if not pairs:
        return base
    return base + "?" + urllib.parse.urlencode(pairs)


def render_research(
    *,
    q: str = "",
    topic: str = "",
    kind: str = "",
) -> str:
    """Render /research via the cycle-18 Insights-triplet helper.

    The page-specific work is just (1) filtering the catalog and
    (2) rendering the cards; the chrome (search hero + filter
    sidebar + results header + chips + Clear all + intro)
    is composed by ``render_insights_page``.
    """
    from rcm_mc.ui._chartis_kit import (
        render_insights_page, ck_arrow_link, ck_next_section,
        ck_provenance_tooltip,
    )

    def _matches(entry: Dict[str, str]) -> bool:
        if topic and entry["topic"] != topic:
            return False
        if kind and entry["kind"] != kind:
            return False
        if q and q.lower() not in (
            entry["title"] + " " + entry["summary"]
        ).lower():
            return False
        return True

    filtered = [e for e in RESEARCH_ENTRIES if _matches(e)]

    # Facet options derive from the full catalog (not the filtered
    # subset) so partner can navigate back to a topic that's been
    # filtered out.
    all_topics = sorted({e["topic"] for e in RESEARCH_ENTRIES})
    all_kinds = sorted({e["kind"] for e in RESEARCH_ENTRIES})
    facets = [
        {
            "title": "By topic",
            "name": "topic",
            "input_type": "radio",
            "options": [
                {"label": "All topics", "value": "", "checked": not topic},
                *[
                    {"label": t, "value": t, "checked": t == topic}
                    for t in all_topics
                ],
            ],
        },
        {
            "title": "By format",
            "name": "kind",
            "input_type": "radio",
            "options": [
                {"label": "All formats", "value": "", "checked": not kind},
                *[
                    {"label": k, "value": k, "checked": k == kind}
                    for k in all_kinds
                ],
            ],
        },
    ]

    if not filtered:
        body_html = (
            '<div class="ck-affirm-empty">'
            '<h3>No research matches that filter.</h3>'
            '<p>Drop a chip from the row above, or broaden the keyword '
            'and try again. The catalog covers methodology, frameworks, '
            'industry notes, and case studies.</p>'
            '</div>'
        )
    else:
        cards = []
        for entry in filtered:
            cards.append(
                '<article class="ck-research-card">'
                f'<div class="ck-eyebrow">{_html.escape(entry["topic"])} '
                f'· {_html.escape(entry["kind"])}</div>'
                f'<h3 class="ck-research-card-title">'
                f'<a href="{_html.escape(entry["href"])}">'
                f'{_html.escape(entry["title"])}</a></h3>'
                f'<p class="ck-research-card-body">'
                f'{_html.escape(entry["summary"])}</p>'
                + ck_arrow_link("Read more", entry["href"])
                + '</article>'
            )
        body_html = (
            '<div class="ck-research-grid">'
            + "".join(cards)
            + '</div>'
        )

    # Cycle 35 — wrap the count with the catalog provenance so
    # partners see where the research surface lives + how the
    # facets are derived.
    count_display = ck_provenance_tooltip(
        "Research catalog",
        f"{len(filtered):,}",
        explainer=(
            f"Curated index of {len(RESEARCH_ENTRIES)} research "
            f"notes (methodology, frameworks, deep-dives, field "
            f"notes). Topic and format facets derive from the full "
            f"catalog, not the current filter, so partner can "
            f"navigate back into a topic that's been filtered out."
        ),
    )
    return render_insights_page(
        action="/research",
        state={"q": q, "topic": topic, "kind": kind},
        facets=facets,
        count=count_display,
        count_label="Note" if len(filtered) == 1 else "Notes",
        body_html=body_html,
        title="Research",
        active_nav="research",
        keyword_placeholder="Topic, framework, sector…",
        intro={
            "eyebrow": "RESEARCH",
            "headline": "Where the platform thinks out loud.",
            "italic_word": "thinks",
            "body": (
                "Methodology, frameworks, deep-dives, and field notes — "
                "everything the analyst voice has published since the "
                "last fund raise. Filter by topic or format to narrow."
            ),
        },
        subtitle=f"{len(filtered)} of {len(RESEARCH_ENTRIES)} research notes",
        next_section_html=ck_next_section(
            "Open the metric glossary",
            "/metric-glossary",
            eyebrow="Continue —",
            italic_word="metric",
        ),
    )
