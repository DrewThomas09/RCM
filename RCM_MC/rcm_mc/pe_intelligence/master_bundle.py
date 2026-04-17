"""Master bundle — one-call produce every artifact for a packet.

The PE intelligence package has dozens of renderers and analyzers.
The server, CLI, and export layer want a single entry point that
produces *all* artifacts for a deal — the review, every IC memo
format, the LP pitch, the 100-day plan, the diligence board, the
board memo, the analyst cheatsheet, the priority queue entry, etc.

This module is that entry point. It extends `workbench_integration`'s
`build_workbench_bundle` with additional artifacts.

The bundle is intentionally flat + JSON-serializable so the caller
can persist it wherever (SQLite blob, S3, Notion page).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .analyst_cheatsheet import build_cheatsheet
from .auditor_view import build_audit_trail
from .board_memo import render_board_memo
from .deepdive_heuristics import run_deepdive_heuristics
from .extra_heuristics import run_all_plus_extras
from .extra_red_flags import run_extra_red_flags
from .heuristics import HeuristicContext
from .hundred_day_plan import generate_plan, render_plan_markdown
from .ic_memo import render_all as _render_ic_memo_all
from .lp_pitch import render_lp_all as _render_lp_pitch_all
from .memo_formats import (
    render_all_formats as _render_memo_formats,
)
from .narrative_styles import compose_styled_narrative
from .partner_discussion import build_discussion
from .partner_review import PartnerReview, partner_review
from .regulatory_watch import for_deal as regulatory_items_for_deal
from .scenario_narrative import render_scenario_narrative
from .bear_book import scan_bear_book


def build_master_bundle(packet: Any) -> Dict[str, Any]:
    """Generate every artifact the PE-intel package can produce.

    Returns a dict with the shape used by downstream renderers. Each
    artifact is guarded — a bug in any single one does not take down
    the bundle.
    """
    bundle: Dict[str, Any] = {}
    # Core review.
    review = partner_review(packet)
    bundle["review"] = review.to_dict()

    # Rebuild HeuristicContext approximate from review context for
    # downstream scans that need it.
    cs = review.context_summary or {}
    ctx = HeuristicContext(
        payer_mix=dict(cs.get("payer_mix") or {}),
        ebitda_m=cs.get("ebitda_m"), revenue_m=cs.get("revenue_m"),
        bed_count=cs.get("bed_count"),
        hospital_type=cs.get("hospital_type"),
        state=cs.get("state"), teaching_status=cs.get("teaching_status"),
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
        denial_improvement_bps_per_yr=cs.get("denial_improvement_bps_per_yr"),
        ar_reduction_days_per_yr=cs.get("ar_reduction_days_per_yr"),
        margin_expansion_bps_per_yr=cs.get("margin_expansion_bps_per_yr"),
        deal_structure=cs.get("deal_structure"),
    )

    # Renderer artifacts.
    try:
        bundle["ic_memo"] = _render_ic_memo_all(review)
    except Exception as exc:
        bundle["ic_memo"] = {"error": repr(exc)}
    try:
        bundle["lp_pitch"] = _render_lp_pitch_all(review)
    except Exception as exc:
        bundle["lp_pitch"] = {"error": repr(exc)}
    try:
        bundle["memo_formats"] = _render_memo_formats(review)
    except Exception as exc:
        bundle["memo_formats"] = {"error": repr(exc)}
    try:
        bundle["analyst_cheatsheet"] = build_cheatsheet(review)
    except Exception as exc:
        bundle["analyst_cheatsheet"] = {"error": repr(exc)}
    try:
        bundle["board_memo"] = render_board_memo(review)
    except Exception as exc:
        bundle["board_memo"] = {"error": repr(exc)}
    try:
        bundle["hundred_day_plan_markdown"] = render_plan_markdown(
            generate_plan(review))
    except Exception as exc:
        bundle["hundred_day_plan_markdown"] = f"error: {exc!r}"

    # Narrative styles (subset — the caller picks what they render).
    try:
        bundle["narrative_styles"] = {
            "analyst_brief": compose_styled_narrative(
                "analyst_brief",
                bands=review.reasonableness_checks,
                hits=review.heuristic_hits,
                hospital_type=ctx.hospital_type,
                ebitda_m=ctx.ebitda_m,
                payer_mix=ctx.payer_mix,
            ),
            "skeptic": compose_styled_narrative(
                "skeptic",
                bands=review.reasonableness_checks,
                hits=review.heuristic_hits,
                hospital_type=ctx.hospital_type,
                ebitda_m=ctx.ebitda_m,
                payer_mix=ctx.payer_mix,
            ),
            "three_sentence": compose_styled_narrative(
                "three_sentence",
                bands=review.reasonableness_checks,
                hits=review.heuristic_hits,
                hospital_type=ctx.hospital_type,
                ebitda_m=ctx.ebitda_m,
                payer_mix=ctx.payer_mix,
            ),
        }
    except Exception as exc:
        bundle["narrative_styles"] = {"error": repr(exc)}

    # Supplemental analyses.
    try:
        bundle["extra_heuristics"] = [
            h.to_dict() for h in run_all_plus_extras(ctx)
        ]
    except Exception as exc:
        bundle["extra_heuristics"] = {"error": repr(exc)}
    try:
        bundle["extra_red_flags"] = [
            h.to_dict() for h in run_extra_red_flags(ctx)
        ]
    except Exception as exc:
        bundle["extra_red_flags"] = {"error": repr(exc)}
    try:
        bundle["deepdive_heuristics"] = [
            h.to_dict() for h in run_deepdive_heuristics(ctx)
        ]
    except Exception as exc:
        bundle["deepdive_heuristics"] = {"error": repr(exc)}
    try:
        bundle["bear_patterns"] = [h.to_dict() for h in scan_bear_book(ctx)]
    except Exception as exc:
        bundle["bear_patterns"] = {"error": repr(exc)}
    try:
        bundle["regulatory_items"] = [
            i.to_dict() for i in regulatory_items_for_deal(
                subsector=ctx.hospital_type, state=ctx.state,
                payer_mix=ctx.payer_mix,
            )
        ]
    except Exception as exc:
        bundle["regulatory_items"] = {"error": repr(exc)}
    try:
        bundle["scenario_narrative"] = (
            render_scenario_narrative(review.stress_scenarios or {}).to_dict()
        )
    except Exception as exc:
        bundle["scenario_narrative"] = {"error": repr(exc)}
    try:
        bundle["partner_discussion"] = [
            item.to_dict() for item in build_discussion(review)
        ]
    except Exception as exc:
        bundle["partner_discussion"] = {"error": repr(exc)}
    try:
        bundle["audit_trail"] = build_audit_trail(review).to_dict()
    except Exception as exc:
        bundle["audit_trail"] = {"error": repr(exc)}

    return bundle


def bundle_index(bundle: Dict[str, Any]) -> List[str]:
    """Return the list of artifact keys in the bundle."""
    return sorted(bundle.keys())
