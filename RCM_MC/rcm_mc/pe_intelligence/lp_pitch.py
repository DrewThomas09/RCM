"""LP-pitch one-pager — summary view of a PartnerReview for LP eyes.

The internal IC memo (see :mod:`ic_memo`) is a frank, partner-voice
document with "Do not show this at IC" quotes and bear-case detail.
That's not an LP deliverable. LPs want:

- One-sentence thesis.
- Three-bullet "why now" / "why us" framing.
- The top-line numbers (IRR, MOIC, hold).
- A short risks section that is honest but not alarmist.

This module renders a PartnerReview as an LP-facing one-pager in
Markdown or HTML. It softens the partner-voice tone: "do not bring to
IC" becomes "we will address X in diligence." The underlying
recommendation is preserved.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .partner_review import PartnerReview
from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .narrative import REC_PASS, REC_PROCEED, REC_PROCEED_CAVEATS, REC_STRONG_PROCEED
from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
)


# ── Tone softening ───────────────────────────────────────────────────

_REC_SOFT = {
    REC_PASS: "declining to underwrite as currently constructed",
    REC_PROCEED_CAVEATS: "advancing with named diligence workstreams",
    REC_PROCEED: "advancing to full diligence",
    REC_STRONG_PROCEED: "prioritizing for bid",
}


def _soften_partner_voice(voice: str) -> str:
    """Soften a partner-voice quote into LP-appropriate language."""
    if not voice:
        return ""
    replacements = [
        ("Do not show this", "We will re-check this"),
        ("do not show this", "we will re-check this"),
        ("Hard pass", "We do not underwrite this"),
        ("Model looks broken", "Model assumptions need review"),
        ("I don't believe", "We are skeptical of"),
        ("Model says, world disagrees.", "Model assumption is aggressive relative to peer evidence."),
        ("This is where deals die", "This is a structural risk"),
    ]
    out = voice
    for pattern, replacement in replacements:
        out = out.replace(pattern, replacement)
    return out


def _top_risks(hits: List[HeuristicHit], limit: int = 3) -> List[str]:
    """Distill top-severity hits into LP-facing risk bullets."""
    seen = set()
    out: List[str] = []
    for h in hits:
        if h.severity not in (SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM):
            continue
        key = h.id
        if key in seen:
            continue
        seen.add(key)
        # Prefer partner_voice (softened); fall back to finding.
        text = _soften_partner_voice(h.partner_voice) or h.finding
        out.append(f"{h.title} — {text}")
        if len(out) >= limit:
            break
    return out


def _top_strengths(bands: List[BandCheck], limit: int = 3) -> List[str]:
    """Distill strengths from IN_BAND checks."""
    out: List[str] = []
    for b in bands:
        if b.verdict != "IN_BAND":
            continue
        if b.metric == "irr":
            out.append(f"Base-case IRR within peer band ({_pct(b.observed)})")
        elif b.metric == "ebitda_margin":
            out.append(f"Operating margins ({_pct(b.observed)}) consistent with peers")
        elif b.metric == "exit_multiple":
            out.append(f"Exit multiple ({b.observed:.2f}x) supported by comps")
        elif b.metric.startswith("lever:"):
            name = b.metric.split(":", 1)[1].replace("_", " ")
            out.append(f"{name.title()} lever sized inside realistic band")
        if len(out) >= limit:
            break
    return out


def _pct(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{v*100:.1f}%"


def _x(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{v:.2f}x"


def _dollars_m(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1_000:
        return f"${v/1_000:.2f}B"
    return f"${v:.1f}M"


# ── Markdown ─────────────────────────────────────────────────────────

def render_lp_markdown(review: PartnerReview) -> str:
    """Render a PartnerReview as an LP-facing one-pager (Markdown)."""
    ctx = review.context_summary
    name = review.deal_name or review.deal_id or "Deal"
    thesis = review.narrative.headline
    rec_soft = _REC_SOFT.get(review.narrative.recommendation, "under review")

    lines: List[str] = [
        f"# {name} — LP Brief",
        "",
        f"_{thesis}_",
        "",
        f"**Status:** {rec_soft}.",
        "",
        "## Opportunity snapshot",
        "",
        f"| | |",
        f"|---|---|",
        f"| Segment | {ctx.get('hospital_type') or 'n/a'} |",
        f"| Location | {ctx.get('state') or 'n/a'} |",
        f"| EBITDA (current) | {_dollars_m(ctx.get('ebitda_m'))} |",
        f"| Hold period | {ctx.get('hold_years') or 'n/a'} years |",
        f"| Target IRR | {_pct(ctx.get('projected_irr'))} |",
        f"| Target MOIC | {_x(ctx.get('projected_moic'))} |",
        f"| Payer mix | " + _format_payer_mix(ctx.get("payer_mix") or {}) + " |",
        "",
        "## Why this deal",
        "",
        review.narrative.bull_case,
        "",
        "## Risks and mitigations",
        "",
    ]
    risks = _top_risks(review.heuristic_hits)
    if risks:
        for r in risks:
            lines.append(f"- {r}")
    else:
        lines.append("- No material structural risks identified at this stage.")
    lines.extend([
        "",
        "## Diligence priorities",
        "",
    ])
    for q in review.narrative.key_questions[:5]:
        lines.append(f"- {q}")
    lines.extend([
        "",
        "## Strengths vs peer",
        "",
    ])
    strengths = _top_strengths(review.reasonableness_checks)
    if strengths:
        for s in strengths:
            lines.append(f"- {s}")
    else:
        lines.append("- Further positioning to be confirmed in diligence.")
    lines.extend([
        "",
        "---",
        "",
        "_Generated from internal PartnerReview. For LP discussion only; does not constitute an offer._",
        "",
    ])
    return "\n".join(lines)


def _format_payer_mix(mix: Dict[str, float]) -> str:
    if not mix:
        return "not reported"
    norm = {k: float(v) for k, v in mix.items() if v is not None}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    parts = [f"{str(k).title()} {v*100:.0f}%"
             for k, v in sorted(norm.items(), key=lambda kv: -kv[1])]
    return ", ".join(parts)


# ── HTML ─────────────────────────────────────────────────────────────

def render_lp_html(review: PartnerReview) -> str:
    """Render a PartnerReview as LP-facing HTML one-pager."""
    ctx = review.context_summary
    name = html.escape(review.deal_name or review.deal_id or "Deal")
    thesis = html.escape(review.narrative.headline or "")
    rec_soft = html.escape(_REC_SOFT.get(review.narrative.recommendation, "under review"))
    bull = html.escape(review.narrative.bull_case or "")

    parts: List[str] = [
        '<article class="lp-brief">',
        f'<header><h1>{name} — LP Brief</h1><p class="thesis">{thesis}</p>',
        f'<p class="status"><strong>Status:</strong> {rec_soft}.</p></header>',
        '<section class="snapshot"><h2>Opportunity snapshot</h2><dl>',
        f'<dt>Segment</dt><dd>{html.escape(str(ctx.get("hospital_type") or "n/a"))}</dd>',
        f'<dt>Location</dt><dd>{html.escape(str(ctx.get("state") or "n/a"))}</dd>',
        f'<dt>EBITDA (current)</dt><dd>{html.escape(_dollars_m(ctx.get("ebitda_m")))}</dd>',
        f'<dt>Hold</dt><dd>{html.escape(str(ctx.get("hold_years") or "n/a"))} years</dd>',
        f'<dt>Target IRR</dt><dd>{html.escape(_pct(ctx.get("projected_irr")))}</dd>',
        f'<dt>Target MOIC</dt><dd>{html.escape(_x(ctx.get("projected_moic")))}</dd>',
        f'<dt>Payer mix</dt><dd>{html.escape(_format_payer_mix(ctx.get("payer_mix") or {}))}</dd>',
        '</dl></section>',
        f'<section class="why"><h2>Why this deal</h2><p>{bull}</p></section>',
        '<section class="risks"><h2>Risks and mitigations</h2><ul>',
    ]
    risks = _top_risks(review.heuristic_hits)
    if risks:
        for r in risks:
            parts.append(f"<li>{html.escape(r)}</li>")
    else:
        parts.append("<li>No material structural risks identified at this stage.</li>")
    parts.append("</ul></section>")
    parts.append('<section class="diligence"><h2>Diligence priorities</h2><ol>')
    for q in review.narrative.key_questions[:5]:
        parts.append(f"<li>{html.escape(q)}</li>")
    parts.append("</ol></section>")
    parts.append('<section class="strengths"><h2>Strengths vs peer</h2><ul>')
    strengths = _top_strengths(review.reasonableness_checks)
    if strengths:
        for s in strengths:
            parts.append(f"<li>{html.escape(s)}</li>")
    else:
        parts.append("<li>Further positioning to be confirmed in diligence.</li>")
    parts.append("</ul></section>")
    parts.append(
        '<footer><em>Generated from internal PartnerReview. For LP '
        'discussion only; does not constitute an offer.</em></footer>'
    )
    parts.append("</article>")
    return "".join(parts)


# ── All formats ──────────────────────────────────────────────────────

def render_lp_all(review: PartnerReview) -> Dict[str, str]:
    """Render all LP-brief formats."""
    return {
        "markdown": render_lp_markdown(review),
        "html": render_lp_html(review),
    }
