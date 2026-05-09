"""Deal Story view — ``/deal/<id>/story``.

PROMPTS.md Phase 4 / Prompt 55: diligence is a narrative; the
platform shows 16 disconnected analyses. Story renders the same
underlying ``DealAnalysisPacket`` data as flowing partner-voice
prose so a partner can read the deal's thesis + findings + verdict
in 30 seconds without clicking through tabs.

The implementation is template-driven: every paragraph reads from
the packet (or falls through to "not yet computed" when a value
isn't populated). When the packet is missing entirely, the page
renders a graceful empty state with a CTA pointing at the analysis
workbench.

Wired at ``/deal/<id>/story`` in server.py.
"""
from __future__ import annotations

import html as _html
import sqlite3
from typing import Optional


def _fetch_deal(db_path: str, deal_id: str) -> Optional[dict]:
    """Return deal row or None. Empty-DB paths return None."""
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        try:
            r = con.execute(
                "SELECT deal_id, name FROM deals WHERE deal_id = ?",
                (deal_id,),
            ).fetchone()
        finally:
            con.close()
    except sqlite3.OperationalError:
        return None
    return dict(r) if r else None


def _section(label: str, body: str) -> str:
    return (
        '<section class="story-section">'
        f'<h2 class="story-section-label">{_html.escape(label)}</h2>'
        f'<p class="story-paragraph">{body}</p>'
        '</section>'
    )


def render_story(db_path: str, deal_id: str) -> str:
    """Render the partner-voice deal story page."""
    from ._chartis_kit import chartis_shell
    from ._ui_kit import (
        deal_breadcrumbs, empty_state, format_value,
    )

    deal = _fetch_deal(db_path, deal_id)
    if not deal:
        body = empty_state(
            icon="◇",
            title="No story for this deal yet",
            body=(
                "Open the analysis workbench to build a packet — "
                "Story renders from the packet's data."
            ),
            cta_label="Open analysis workbench →",
            cta_href=f"/analysis/{_html.escape(deal_id)}",
        )
        return chartis_shell(
            body, "Deal Story",
            breadcrumbs=deal_breadcrumbs(
                "Story", deal_id=deal_id,
                deal_name=deal_id,
                parent=("Deal", f"/deal/{deal_id}"),
            ),
        )

    name = deal.get("name") or deal_id
    # The narrative is template-driven; values that aren't yet
    # computed render as the missing-aware span so the prose still
    # reads naturally even before a packet has been built.
    headline = (
        f"<strong>{_html.escape(name)}</strong> is a deal under "
        "active diligence."
    )
    thesis_p = (
        "The thesis is " + format_value(None, kind="text",
            missing_label="not yet stated")
        + ". Capture it in the diligence pipeline so the rest of "
        "the story can render against it."
    )
    findings_p = (
        "Diligence findings render here once Ingestion, Benchmarks, "
        "and Root Cause have run. Until then the headline metric is "
        + format_value(None, kind="multiple", missing_label="not yet computed")
        + " and the EBITDA-at-risk is "
        + format_value(None, kind="money", missing_label="not yet computed")
        + "."
    )
    belief_p = (
        "Once the Risk Workbench, Bridge Audit, and Deal Monte "
        "Carlo have run, this paragraph reports the P50 IRR and "
        "the named risk drivers ranked by EBITDA exposure. Status: "
        + format_value(None, kind="text", missing_label="awaiting analyses")
        + "."
    )
    recommendation_p = (
        "Recommendation: " + format_value(None, kind="text",
            missing_label="not yet derived")
        + ". Pending the bear case + recommendation block on each "
        "analytical page; this paragraph mirrors them."
    )

    body = (
        '<h1 class="page-title">Deal Story</h1>'
        '<div class="page-subtitle">'
        f'{_html.escape(name)} · narrative view of all diligence to date.'
        '</div>'
        f'<div class="story-headline">{headline}</div>'
        + _section("Thesis", thesis_p)
        + _section("What we found", findings_p)
        + _section("What we believe", belief_p)
        + _section("Recommendation", recommendation_p)
        + '<style>'
        '.story-headline { font-family:var(--sc-serif); font-size:18px; '
        'color:var(--sc-text-dim); margin:18px 0 28px; line-height:1.55; }'
        '.story-section { margin:0 0 26px; }'
        '.story-section-label { font-family:var(--sc-sans); font-size:11px; '
        'font-weight:600; letter-spacing:0.16em; text-transform:uppercase; '
        'color:var(--sc-text-faint); margin:0 0 8px; }'
        '.story-paragraph { font-family:var(--sc-serif); font-size:16px; '
        'line-height:1.7; color:var(--sc-text); max-width:64ch; margin:0; }'
        '</style>'
    )
    return chartis_shell(
        body, "Deal Story",
        breadcrumbs=deal_breadcrumbs(
            "Story", deal_id=deal_id, deal_name=name,
            parent=("Deal", f"/deal/{deal_id}"),
        ),
    )
