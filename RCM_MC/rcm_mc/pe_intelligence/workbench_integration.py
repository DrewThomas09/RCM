"""Workbench-integration helpers.

These helpers let the UI / server surface the PE intelligence outputs
without the server having to know how every module composes. Callers
hand in a :class:`DealAnalysisPacket` (or dict) and get back:

- A single :class:`PartnerReview` (core).
- A dict of renderable artifacts: IC memo (markdown + html),
  LP pitch (markdown + html), 100-day plan (markdown),
  diligence board (markdown).
- A JSON-serializable bundle of every finding for API consumers.

The package intentionally stays import-only — no side effects on load.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .diligence_tracker import (
    DiligenceBoard,
    board_from_review,
    render_board_markdown,
)
from .hundred_day_plan import (
    HundredDayPlan,
    generate_plan,
    render_plan_markdown,
)
from .ic_memo import render_all as render_ic_memo_all
from .lp_pitch import render_lp_all
from .partner_review import PartnerReview, partner_review
from .red_flags import run_red_flags
from .bear_book import scan_bear_book
from .heuristics import HeuristicContext
from .deal_archetype import (
    ArchetypeContext,
    classify_archetypes,
)
from .regulatory_watch import for_deal as regulatory_items_for_deal


# ── Public bundle API ───────────────────────────────────────────────

def build_workbench_bundle(packet: Any) -> Dict[str, Any]:
    """One-call convenience: produce every renderable artifact from a packet.

    Returns a dict:
      {
        "review": PartnerReview.to_dict(),
        "ic_memo": {"markdown": ..., "html": ..., "text": ...},
        "lp_pitch": {"markdown": ..., "html": ...},
        "hundred_day_plan_markdown": str,
        "diligence_board_markdown": str,
        "bear_patterns": [...],
        "regulatory_items": [...],
      }

    The server is expected to wrap this in a standard response shape.
    """
    review = partner_review(packet)
    ctx = _reconstruct_context(review)
    return {
        "review": review.to_dict(),
        "ic_memo": render_ic_memo_all(review),
        "lp_pitch": render_lp_all(review),
        "hundred_day_plan_markdown": render_plan_markdown(generate_plan(review)),
        "diligence_board_markdown": render_board_markdown(
            board_from_review(review)
        ),
        "bear_patterns": [h.to_dict() for h in scan_bear_book(ctx)],
        "regulatory_items": [
            i.to_dict() for i in regulatory_items_for_deal(
                subsector=ctx.hospital_type,
                state=ctx.state,
                payer_mix=ctx.payer_mix,
            )
        ],
    }


def _reconstruct_context(review: PartnerReview) -> HeuristicContext:
    """Rebuild a HeuristicContext from a review's context_summary.

    This is a convenience for modules that want to run against the same
    inputs the review used without round-tripping through the packet.
    """
    cs = review.context_summary or {}
    ctx = HeuristicContext(
        payer_mix=dict(cs.get("payer_mix") or {}),
        ebitda_m=cs.get("ebitda_m"),
        revenue_m=cs.get("revenue_m"),
        bed_count=cs.get("bed_count"),
        hospital_type=cs.get("hospital_type"),
        state=cs.get("state"),
        teaching_status=cs.get("teaching_status"),
        denial_rate=cs.get("denial_rate"),
        final_writeoff_rate=cs.get("final_writeoff_rate"),
        days_in_ar=cs.get("days_in_ar"),
        ebitda_margin=cs.get("ebitda_margin"),
        exit_multiple=cs.get("exit_multiple"),
        entry_multiple=cs.get("entry_multiple"),
        hold_years=cs.get("hold_years"),
        projected_irr=cs.get("projected_irr"),
        projected_moic=cs.get("projected_moic"),
        leverage_multiple=cs.get("leverage_multiple"),
        covenant_headroom_pct=cs.get("covenant_headroom_pct"),
        data_coverage_pct=cs.get("data_coverage_pct"),
        has_case_mix_data=cs.get("has_case_mix_data", True),
        denial_improvement_bps_per_yr=cs.get("denial_improvement_bps_per_yr"),
        ar_reduction_days_per_yr=cs.get("ar_reduction_days_per_yr"),
        margin_expansion_bps_per_yr=cs.get("margin_expansion_bps_per_yr"),
        deal_structure=cs.get("deal_structure"),
    )
    return ctx


def archetype_summary(review: PartnerReview,
                      *, archetype_ctx: Optional[ArchetypeContext] = None) -> Dict[str, Any]:
    """Return top archetype matches for a deal.

    Accepts an optional ``archetype_ctx`` because the packet does not
    hold deal-structure signals the classifier needs. If omitted,
    only signals derivable from the review are used (modest precision).
    """
    if archetype_ctx is None:
        # Build a minimal ctx from review context.
        cs = review.context_summary or {}
        archetype_ctx = ArchetypeContext(
            current_ebitda_margin=cs.get("ebitda_margin"),
            debt_to_ebitda=cs.get("leverage_multiple"),
            hospital_type=cs.get("hospital_type"),
        )
    hits = classify_archetypes(archetype_ctx, min_confidence=0.20)
    return {
        "primary": hits[0].archetype if hits else None,
        "ranked": [h.to_dict() for h in hits],
    }


# ── Slimmed API shape ───────────────────────────────────────────────

def build_api_payload(packet: Any) -> Dict[str, Any]:
    """Server-friendly payload: review + key artifacts, no raw HTML.

    Keeps the network payload small. HTML renderers are available
    separately for when the client wants the full view.
    """
    review = partner_review(packet)
    return {
        "deal_id": review.deal_id,
        "deal_name": review.deal_name,
        "recommendation": review.narrative.recommendation,
        "headline": review.narrative.headline,
        "bull_case": review.narrative.bull_case,
        "bear_case": review.narrative.bear_case,
        "key_questions": list(review.narrative.key_questions),
        "severity_counts": review.severity_counts(),
        "band_counts": review.band_counts(),
        "heuristic_hits": [h.to_dict() for h in review.heuristic_hits],
        "reasonableness_checks": [b.to_dict() for b in review.reasonableness_checks],
        "context_summary": dict(review.context_summary),
        "has_critical_flag": review.has_critical_flag(),
        "is_fundable": review.is_fundable(),
    }
