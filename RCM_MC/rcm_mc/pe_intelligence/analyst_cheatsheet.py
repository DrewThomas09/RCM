"""Analyst cheatsheet — condensed pre-read for the associate.

Associates walking into IC need a 1-page reference they can glance
at mid-discussion. This module renders a PartnerReview into:

- Top 5 facts (context, size, payer mix).
- Top 5 flags (highest severity heuristics with partner-voice quote).
- Top 3 questions (from narrative.key_questions).
- Numeric quick-check (IRR / MOIC / leverage / investability /
  stress grade).

Different from the IC memo (which is the partner's document) — this
is the associate's reference to stay oriented during IC discussion.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .partner_review import PartnerReview


def _top_hits(review: PartnerReview, n: int = 5) -> List[HeuristicHit]:
    order = {SEV_CRITICAL: 4, SEV_HIGH: 3, SEV_MEDIUM: 2, "LOW": 1, "INFO": 0}
    return sorted(review.heuristic_hits,
                  key=lambda h: -order.get(h.severity, 0))[:n]


def _fmt_pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return str(v)


def _fmt_x(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}x"
    except Exception:
        return str(v)


def build_cheatsheet(review: PartnerReview) -> Dict[str, Any]:
    """Return a structured cheatsheet dict."""
    ctx = review.context_summary or {}
    hits = _top_hits(review, 5)

    top_facts: List[str] = []
    if ctx.get("ebitda_m"):
        top_facts.append(f"${ctx['ebitda_m']:.0f}M EBITDA")
    if ctx.get("hospital_type"):
        top_facts.append(f"Subsector: {ctx['hospital_type']}")
    if ctx.get("payer_mix"):
        # Top payer
        mix = ctx["payer_mix"] or {}
        norm = {str(k): float(v) for k, v in mix.items() if v is not None}
        if norm:
            top = max(norm.items(), key=lambda kv: kv[1])
            top_facts.append(f"Top payer: {top[0].title()} {top[1]*100:.0f}%")
    if ctx.get("hold_years"):
        top_facts.append(f"Hold: {ctx['hold_years']} years")
    if ctx.get("state"):
        top_facts.append(f"Primary state: {ctx['state']}")
    top_facts = top_facts[:5]

    top_flags = [
        {
            "severity": h.severity,
            "title": h.title,
            "partner_voice": h.partner_voice or h.finding,
        }
        for h in hits
    ]

    # Quick numbers
    stress_grade = (review.stress_scenarios or {}).get("robustness_grade")
    investability = (review.investability or {}).get("score")
    quick_numbers = {
        "irr": _fmt_pct(ctx.get("projected_irr")),
        "moic": _fmt_x(ctx.get("projected_moic")),
        "leverage": _fmt_x(ctx.get("leverage_multiple")),
        "investability": (f"{investability:.0f}/100"
                          if investability is not None else "—"),
        "stress_grade": stress_grade or "—",
    }

    return {
        "deal_id": review.deal_id,
        "deal_name": review.deal_name,
        "recommendation": review.narrative.recommendation,
        "top_facts": top_facts,
        "top_flags": top_flags,
        "top_questions": list(review.narrative.key_questions)[:3],
        "quick_numbers": quick_numbers,
    }


def render_cheatsheet_markdown(review: PartnerReview) -> str:
    sheet = build_cheatsheet(review)
    name = sheet["deal_name"] or sheet["deal_id"] or "(deal)"
    lines = [
        f"# Analyst Cheatsheet — {name}",
        "",
        f"**Recommendation:** {sheet['recommendation']}",
        "",
        "## Quick numbers",
        "",
    ]
    qn = sheet["quick_numbers"]
    lines.append(
        f"IRR {qn['irr']} | MOIC {qn['moic']} | Leverage {qn['leverage']} | "
        f"Invest {qn['investability']} | Stress {qn['stress_grade']}"
    )
    lines.extend(["", "## Top facts", ""])
    for f in sheet["top_facts"]:
        lines.append(f"- {f}")
    lines.extend(["", "## Top flags", ""])
    if not sheet["top_flags"]:
        lines.append("- None.")
    else:
        for flag in sheet["top_flags"]:
            lines.append(f"- [{flag['severity']}] **{flag['title']}**")
            if flag["partner_voice"]:
                lines.append(f"  > {flag['partner_voice']}")
    lines.extend(["", "## Top questions", ""])
    for i, q in enumerate(sheet["top_questions"], 1):
        lines.append(f"{i}. {q}")
    return "\n".join(lines)
