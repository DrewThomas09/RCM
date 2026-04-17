"""Board memo — governance-focused memo for sponsor boards.

Sponsor boards see a different cut of the deal than the IC:

- **Fiduciary framing** — reminds the board of its legal duties
  (sponsor-side: LPA provisions, conflicts disclosure, valuation
  oversight).
- **Approval matrix** — what the board is approving vs merely
  informed about (valuation? management? related-party?).
- **Required disclosures** — specific items that must be on the
  record (side-letter adherence, LPAC notifications, insurance
  changes).
- **Action list** — the concrete board asks.

This module renders a PartnerReview into that structure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .heuristics import SEV_CRITICAL, SEV_HIGH
from .partner_review import PartnerReview


def _rec_board_language(rec: str) -> str:
    """Translate IC rec into board-friendly language."""
    return {
        "STRONG_PROCEED": "APPROVE",
        "PROCEED": "APPROVE",
        "PROCEED_WITH_CAVEATS": "APPROVE subject to caveats",
        "PASS": "DECLINE",
    }.get(rec, rec)


def _required_disclosures(review: PartnerReview) -> List[str]:
    """Surface disclosures triggered by review findings."""
    out: List[str] = []
    # LP side-letter signals surface via specific heuristic ids when
    # the deal-comparison uses them; here we use a generic sweep.
    for hit in review.heuristic_hits:
        if hit.id in ("leverage_too_high_govt_mix",
                      "covenant_headroom_tight"):
            out.append(
                "Capital-structure disclosure: leverage / covenant detail "
                "required at the specific level flagged.")
        if hit.id in ("payer_concentration_risk", "340b_margin_dependency",
                      "medicare_heavy_multiple_ceiling"):
            out.append(
                "Payer-concentration disclosure: single-payer dependency "
                "material to the deal thesis.")
        if hit.id in ("prior_regulatory_action",
                      "regulatory_inspection_open"):
            out.append(
                "Regulatory-history disclosure: prior or open enforcement "
                "must be on the record before approval.")
        if hit.id in ("succession_transition", "key_payer_churn"):
            out.append(
                "Key-dependency disclosure: founder / key-relationship "
                "transitions material to the underwrite.")
    # Dedup preserving order.
    seen: set = set()
    uniq: List[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    # Always add LPA conflicts reminder.
    uniq.append(
        "Confirm no LPA conflict-of-interest provisions implicate this "
        "transaction; LPAC notice required if so.")
    return uniq


def _approval_matrix(review: PartnerReview) -> List[Dict[str, Any]]:
    """Structured list of approval-vs-informed items."""
    rec = review.narrative.recommendation
    invest = review.investability or {}
    items = [
        {"item": "Final purchase price / valuation",
         "action": "APPROVE" if rec != "PASS" else "N/A"},
        {"item": "Capital structure at close (debt, equity)",
         "action": "APPROVE"},
        {"item": "Management retention terms",
         "action": "APPROVE"},
        {"item": "Investability composite",
         "action": "INFORM",
         "detail": f"{invest.get('score', 'n/a')}/100 / {invest.get('grade', 'n/a')}"},
        {"item": "Stress-test results",
         "action": "INFORM",
         "detail": f"grade {(review.stress_scenarios or {}).get('robustness_grade', 'n/a')}"},
    ]
    # If the deal has critical risk, add an explicit risk-acceptance item.
    if any(h.severity == SEV_CRITICAL for h in review.heuristic_hits):
        items.append({
            "item": "Acceptance of critical-risk items",
            "action": "APPROVE",
            "detail": "Board must explicitly accept critical flags.",
        })
    return items


def _action_list(review: PartnerReview) -> List[str]:
    """Concrete board asks."""
    actions: List[str] = []
    rec = review.narrative.recommendation
    if rec == "PASS":
        actions.append("Decline the transaction.")
        return actions
    actions.append(f"Approve management's recommendation: {_rec_board_language(rec)}.")
    critical = [h for h in review.heuristic_hits if h.severity == SEV_CRITICAL]
    if critical:
        actions.append(
            f"Note {len(critical)} critical risk(s) formally accepted.")
    high = [h for h in review.heuristic_hits if h.severity == SEV_HIGH]
    if len(high) >= 3:
        actions.append(
            f"Authorize post-close monitoring for {len(high)} high-severity "
            "items.")
    # Caveats → diligence workstreams.
    if rec == "PROCEED_WITH_CAVEATS":
        actions.append("Authorize diligence completion under listed caveats.")
    return actions


def render_board_memo(review: PartnerReview) -> Dict[str, Any]:
    """Return a structured board-memo dict."""
    deal_name = review.deal_name or review.deal_id or "(deal)"
    return {
        "deal_id": review.deal_id,
        "deal_name": deal_name,
        "board_recommendation": _rec_board_language(
            review.narrative.recommendation),
        "executive_summary": review.narrative.headline,
        "fiduciary_reminder": (
            "The board's duty is to act in good faith and on an informed "
            "basis. Review the material items below before voting; abstain "
            "on any item with a personal or related-party interest."),
        "approval_matrix": _approval_matrix(review),
        "required_disclosures": _required_disclosures(review),
        "action_list": _action_list(review),
    }


def render_board_memo_markdown(review: PartnerReview) -> str:
    d = render_board_memo(review)
    lines = [
        f"# Board Memo — {d['deal_name']}",
        "",
        f"**Board recommendation:** {d['board_recommendation']}",
        "",
        f"_{d['executive_summary']}_",
        "",
        "## Fiduciary reminder",
        "",
        d["fiduciary_reminder"],
        "",
        "## Approval matrix",
        "",
        "| Item | Action | Detail |",
        "|---|---|---|",
    ]
    for row in d["approval_matrix"]:
        lines.append(
            f"| {row['item']} | {row['action']} | {row.get('detail', '')} |"
        )
    lines.extend(["", "## Required disclosures", ""])
    for disc in d["required_disclosures"]:
        lines.append(f"- {disc}")
    lines.extend(["", "## Action list", ""])
    for i, action in enumerate(d["action_list"], 1):
        lines.append(f"{i}. {action}")
    return "\n".join(lines)
