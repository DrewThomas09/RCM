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
    """Render /research with the chartis Insights triplet chrome."""
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_search_hero, ck_filter_sidebar,
        ck_results_header, ck_section_header, ck_arrow_link,
    )

    # Apply server-side filtering. Keyword match runs against the
    # title + summary so a partner searching for "covenant" surfaces
    # any entry whose copy mentions covenants.
    def _matches(entry: Dict[str, str]) -> bool:
        if topic and entry["topic"] != topic:
            return False
        if kind and entry["kind"] != kind:
            return False
        if q:
            haystack = (entry["title"] + " " + entry["summary"]).lower()
            if q.lower() not in haystack:
                return False
        return True

    filtered = [e for e in RESEARCH_ENTRIES if _matches(e)]

    # Filter sidebar facets — derive topic + kind options from the
    # full catalog so partner sees every facet even when filtered to
    # a subset. Sorted alphabetically for stable rendering.
    all_topics = sorted({e["topic"] for e in RESEARCH_ENTRIES})
    all_kinds = sorted({e["kind"] for e in RESEARCH_ENTRIES})

    def _topic_opts():
        yield {"label": "All topics", "value": "", "checked": not topic}
        for t in all_topics:
            yield {"label": t, "value": t, "checked": t == topic}

    def _kind_opts():
        yield {"label": "All formats", "value": "", "checked": not kind}
        for k in all_kinds:
            yield {"label": k, "value": k, "checked": k == kind}

    filter_rail = ck_filter_sidebar(
        title="Filter",
        form_action="/research",
        groups=[
            {"title": "By topic", "name": "topic", "input_type": "radio",
             "options": list(_topic_opts())},
            {"title": "By format", "name": "kind", "input_type": "radio",
             "options": list(_kind_opts())},
        ],
        extra_hidden={"q": q},
    )

    # Active-filter chips with one-click drop URLs.
    chips: List[Dict[str, str]] = []
    if topic:
        chips.append({"label": topic, "remove_href": _build_url(q=q, kind=kind)})
    if kind:
        chips.append({"label": kind, "remove_href": _build_url(q=q, topic=topic)})
    if q:
        chips.append({"label": f'"{q}"', "remove_href": _build_url(topic=topic, kind=kind)})

    results_head = ck_results_header(
        count=f"{len(filtered):,}",
        label="Notes" if len(filtered) != 1 else "Note",
        chips=chips or None,
        clear_all_href="/research" if chips else None,
    )

    section = ck_section_header(
        "Frameworks, methodology, and field notes",
        eyebrow="RESEARCH",
    )

    search_hero = ck_search_hero(
        action="/research",
        name="q",
        initial=q,
        label="Search",
        placeholder="Topic, framework, sector…",
        extra_hidden={"topic": topic, "kind": kind},
    )

    # Results body — editorial card per research entry. Falls back
    # to an affirm-empty band when the filter combination has zero
    # matches so partner gets a real signal not a void.
    if not filtered:
        results_body = (
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
        results_body = (
            '<div class="ck-research-grid">'
            + "".join(cards)
            + '</div>'
        )

    rail_layout = (
        '<div class="ck-rail-layout">'
        f'{filter_rail}'
        '<div class="ck-rail-content">'
        f'{section}{results_head}{results_body}'
        '</div>'
        '</div>'
    )

    body = search_hero + rail_layout

    return chartis_shell(
        body,
        title="Research",
        active_nav="research",
        subtitle=(
            f"{len(filtered)} of {len(RESEARCH_ENTRIES)} research notes"
        ),
    )
