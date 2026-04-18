"""Memo formats — alternate IC memo renderers beyond the default.

`ic_memo.py` renders the standard markdown/html/text formats. This
module adds renderers the deal team actually uses day-to-day:

- **one_pager** — single-page summary, tightly constrained.
- **slack** — slack-formatted (no markdown headers, uses emoji + bold).
- **email** — email-body-friendly (subject line + plain paragraphs).
- **pdf_ready** — markdown with page-break hints for pandoc/weasyprint.
- **deck_bullet** — powerpoint-slide-friendly bullet list.

Each renderer takes a :class:`PartnerReview` and returns a string
(or, for `email`, a `{subject, body}` dict).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .partner_review import PartnerReview
from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
)


def _top_hits(review: PartnerReview, n: int = 3) -> List[HeuristicHit]:
    order = {SEV_CRITICAL: 4, SEV_HIGH: 3, SEV_MEDIUM: 2, "LOW": 1, "INFO": 0}
    return sorted(review.heuristic_hits,
                  key=lambda h: -order.get(h.severity, 0))[:n]


def _recommendation_line(review: PartnerReview) -> str:
    rec = review.narrative.recommendation
    return f"{rec} — {review.narrative.recommendation_rationale}"


# ── 1-pager ─────────────────────────────────────────────────────────

def render_one_pager(review: PartnerReview) -> str:
    ctx = review.context_summary or {}
    name = review.deal_name or review.deal_id or "(deal)"
    top_3 = _top_hits(review, 3)
    lines: List[str] = [
        f"# {name}",
        f"_{review.narrative.headline}_",
        "",
        f"**Recommendation:** {_recommendation_line(review)}",
        "",
        f"**Size:** ${ctx.get('ebitda_m', 'n/a')}M EBITDA  "
        f"**Hold:** {ctx.get('hold_years', 'n/a')}yr  "
        f"**IRR/MOIC:** {_fmt_pct(ctx.get('projected_irr'))} / "
        f"{_fmt_x(ctx.get('projected_moic'))}",
        "",
        "**Top flags:**",
    ]
    if not top_3:
        lines.append("- None above LOW severity.")
    else:
        for h in top_3:
            lines.append(f"- [{h.severity}] {h.title}")
    lines.extend([
        "",
        f"**Bull:** {review.narrative.bull_case}",
        "",
        f"**Bear:** {review.narrative.bear_case}",
    ])
    return "\n".join(lines)


# ── Slack ───────────────────────────────────────────────────────────

_SLACK_ICON = {
    "CRITICAL": ":rotating_light:",
    "HIGH": ":red_circle:",
    "MEDIUM": ":large_yellow_circle:",
    "LOW": ":white_circle:",
    "INFO": ":information_source:",
}


def render_slack(review: PartnerReview) -> str:
    """Slack-formatted message — bold via *…*, no markdown headers."""
    ctx = review.context_summary or {}
    name = review.deal_name or review.deal_id or "(deal)"
    rec = review.narrative.recommendation
    rec_icon = {
        "STRONG_PROCEED": ":white_check_mark:",
        "PROCEED": ":arrow_forward:",
        "PROCEED_WITH_CAVEATS": ":warning:",
        "PASS": ":no_entry:",
    }.get(rec, "")
    lines: List[str] = [
        f"*{name}* {rec_icon} *{rec}*",
        f"{review.narrative.headline}",
        "",
        f"Size: ${ctx.get('ebitda_m', 'n/a')}M EBITDA | "
        f"IRR/MOIC: {_fmt_pct(ctx.get('projected_irr'))} / "
        f"{_fmt_x(ctx.get('projected_moic'))}",
        "",
        "*Top flags:*",
    ]
    top = _top_hits(review, 5)
    if not top:
        lines.append("None.")
    else:
        for h in top:
            icon = _SLACK_ICON.get(h.severity, "")
            lines.append(f"{icon} {h.title}")
    return "\n".join(lines)


# ── Email ───────────────────────────────────────────────────────────

def render_email(review: PartnerReview) -> Dict[str, str]:
    """Returns {'subject', 'body'} for an email client."""
    name = review.deal_name or review.deal_id or "Deal"
    rec = review.narrative.recommendation
    subject = f"{name} — {rec}"
    ctx = review.context_summary or {}
    body_lines: List[str] = [
        f"{review.narrative.headline}",
        "",
        f"Recommendation: {_recommendation_line(review)}",
        "",
        f"Size / returns: ${ctx.get('ebitda_m', 'n/a')}M EBITDA; "
        f"IRR {_fmt_pct(ctx.get('projected_irr'))}, "
        f"MOIC {_fmt_x(ctx.get('projected_moic'))}.",
        "",
        "Bull case:",
        review.narrative.bull_case,
        "",
        "Bear case:",
        review.narrative.bear_case,
        "",
        "Key questions for IC:",
    ]
    for i, q in enumerate(review.narrative.key_questions, 1):
        body_lines.append(f"  {i}. {q}")
    return {"subject": subject, "body": "\n".join(body_lines)}


# ── PDF-ready markdown ──────────────────────────────────────────────

def render_pdf_ready(review: PartnerReview) -> str:
    """Markdown with explicit page-break hints for pandoc/weasyprint.

    Uses ``\\pagebreak`` which pandoc respects; weasyprint respects
    HTML-commented page-break hints added by the renderer.
    """
    ctx = review.context_summary or {}
    name = review.deal_name or review.deal_id or "Deal"
    pagebreak = "\n\n\\pagebreak\n\n"
    parts: List[str] = [
        f"# IC Memo — {name}",
        "",
        f"*{review.narrative.headline}*",
        "",
        f"**Recommendation:** {_recommendation_line(review)}",
        pagebreak,
        "## Context",
        "",
        (f"- EBITDA: ${ctx.get('ebitda_m', 'n/a')}M\n"
         f"- Hold: {ctx.get('hold_years', 'n/a')} years\n"
         f"- IRR / MOIC: {_fmt_pct(ctx.get('projected_irr'))} / "
         f"{_fmt_x(ctx.get('projected_moic'))}\n"
         f"- Entry / Exit: {_fmt_x(ctx.get('entry_multiple'))} / "
         f"{_fmt_x(ctx.get('exit_multiple'))}"),
        pagebreak,
        "## Bull case",
        "",
        review.narrative.bull_case,
        "",
        "## Bear case",
        "",
        review.narrative.bear_case,
        pagebreak,
        "## Pattern flags",
        "",
    ]
    for h in review.heuristic_hits:
        parts.append(f"- **[{h.severity}] {h.title}** — {h.finding}")
        if h.partner_voice:
            parts.append(f"  > {h.partner_voice}")
    parts.extend([pagebreak, "## Key questions"])
    for i, q in enumerate(review.narrative.key_questions, 1):
        parts.append(f"{i}. {q}")
    return "\n".join(parts)


# ── Deck bullet ─────────────────────────────────────────────────────

def render_deck_bullets(review: PartnerReview) -> List[str]:
    """List of <=10 short bullet strings for slide copy-paste."""
    bullets: List[str] = []
    rec = review.narrative.recommendation
    ctx = review.context_summary or {}
    bullets.append(f"Recommendation: {rec}")
    if review.narrative.headline:
        bullets.append(review.narrative.headline)
    if ctx.get("ebitda_m"):
        bullets.append(
            f"${ctx['ebitda_m']:.0f}M EBITDA, IRR "
            f"{_fmt_pct(ctx.get('projected_irr'))}, "
            f"MOIC {_fmt_x(ctx.get('projected_moic'))}")
    for h in _top_hits(review, 3):
        bullets.append(f"{h.severity}: {h.title}")
    for q in review.narrative.key_questions[:3]:
        bullets.append(f"Q: {q}")
    return bullets[:10]


# ── Formatting helpers ──────────────────────────────────────────────

def _fmt_pct(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v)*100:.1f}%"
    except Exception:
        return str(v)


def _fmt_x(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):.2f}x"
    except Exception:
        return str(v)


# ── Render-all dispatcher ───────────────────────────────────────────

def render_all_formats(review: PartnerReview) -> Dict[str, Any]:
    """One-call dispatcher returning every format."""
    return {
        "one_pager": render_one_pager(review),
        "slack": render_slack(review),
        "email": render_email(review),
        "pdf_ready": render_pdf_ready(review),
        "deck_bullets": render_deck_bullets(review),
    }
