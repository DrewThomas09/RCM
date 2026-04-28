"""IC memo formatter — render a PartnerReview as an IC-ready memo.

Partners do not read JSON. They read memos. This module takes a
:class:`PartnerReview` and renders it three ways:

1. **Markdown** — for Slack / Notion / email thread.
2. **HTML** — for the workbench's /partner-review page.
3. **Plaintext** — for CLI partner briefings.

The memo structure follows the shape used on the partner desk:

  1. Deal identity + summary line
  2. Partner recommendation (one word, with the rationale)
  3. Context (size, subsector, payer mix)
  4. Bull case / bear case
  5. Reasonableness summary (IRR, margin, multiple, lever bands)
  6. Pattern flags (heuristics + red flags by severity)
  7. Key questions for the deal team
  8. IC memo paragraph (the partner-voice dictation line)

No I/O — the formatter produces strings. Persistence is the caller's
responsibility.
"""
from __future__ import annotations

import html
from typing import Dict, Iterable, List, Optional

from .partner_review import PartnerReview
from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM, SEV_LOW, SEV_INFO
from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
)


# ── Severity palette ─────────────────────────────────────────────────

_SEV_EMOJI_MD = {
    SEV_CRITICAL: "!!",
    SEV_HIGH: "!",
    SEV_MEDIUM: "•",
    SEV_LOW: "·",
    SEV_INFO: " ",
}

_VERDICT_TAG = {
    VERDICT_IN_BAND: "OK",
    VERDICT_STRETCH: "STRETCH",
    VERDICT_OUT_OF_BAND: "OUT",
    VERDICT_IMPLAUSIBLE: "FAIL",
    VERDICT_UNKNOWN: "?",
}


def _fmt_pct(v: Optional[float], digits: int = 1) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:.{digits}f}%"


def _fmt_x(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{v:.2f}x"


def _fmt_dollars_m(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1_000:
        return f"${v/1_000:.2f}B"
    return f"${v:.1f}M"


# ── Markdown ─────────────────────────────────────────────────────────

def render_markdown(review: PartnerReview) -> str:
    """Render a PartnerReview as a partner-ready Markdown memo."""
    ctx = review.context_summary
    name = review.deal_name or review.deal_id or "(unnamed deal)"
    rec = review.narrative.recommendation
    lines: List[str] = [
        f"# IC Memo — {name}",
        "",
        f"**Recommendation:** `{rec}` — {review.narrative.recommendation_rationale}",
        "",
        f"**Partner read:** {review.narrative.headline}",
        "",
        "## Context",
        "",
        f"- **Size:** {_fmt_dollars_m(ctx.get('ebitda_m'))} EBITDA"
        + (f" on {_fmt_dollars_m(ctx.get('revenue_m'))} revenue" if ctx.get("revenue_m") else ""),
        f"- **Type:** {ctx.get('hospital_type') or 'n/a'}"
        + (f", {ctx.get('bed_count')} beds" if ctx.get("bed_count") else "")
        + (f", {ctx.get('state')}" if ctx.get("state") else ""),
        f"- **Payer mix:** " + _fmt_payer_mix_md(ctx.get("payer_mix") or {}),
        f"- **Hold / IRR / MOIC:** "
        f"{ctx.get('hold_years') or 'n/a'}yr, "
        f"IRR {_fmt_pct(ctx.get('projected_irr'))}, "
        f"MOIC {_fmt_x(ctx.get('projected_moic'))}",
        f"- **Entry / Exit multiples:** {_fmt_x(ctx.get('entry_multiple'))} → {_fmt_x(ctx.get('exit_multiple'))}",
        f"- **Leverage:** {_fmt_x(ctx.get('leverage_multiple'))} at close, "
        f"covenant headroom {_fmt_pct(ctx.get('covenant_headroom_pct'))}",
        "",
        "## Bull case",
        "",
        review.narrative.bull_case,
        "",
        "## Bear case",
        "",
        review.narrative.bear_case,
        "",
        "## Reasonableness",
        "",
        _render_band_table_md(review.reasonableness_checks),
        "",
        "## Pattern flags",
        "",
        _render_hits_md(review.heuristic_hits),
        "",
        "## Key questions",
        "",
    ]
    for i, q in enumerate(review.narrative.key_questions, 1):
        lines.append(f"{i}. {q}")
    lines.extend([
        "",
        "## Partner dictation",
        "",
        f"> {review.narrative.ic_memo_paragraph}",
        "",
    ])
    return "\n".join(lines)


def _fmt_payer_mix_md(mix: Dict[str, float]) -> str:
    if not mix:
        return "not reported"
    parts: List[str] = []
    # Normalize to percents for display.
    norm = {k: float(v) for k, v in mix.items() if v is not None}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    for payer, share in sorted(norm.items(), key=lambda kv: -kv[1]):
        parts.append(f"{str(payer).title()} {share*100:.0f}%")
    return ", ".join(parts)


def _render_band_table_md(bands: List[BandCheck]) -> str:
    if not bands:
        return "_No reasonableness checks ran._"
    rows = ["| Metric | Observed | Verdict | Rationale |",
            "|--------|----------|---------|-----------|"]
    for b in bands:
        observed = b.observed
        obs_fmt: str
        if observed is None:
            obs_fmt = "n/a"
        elif b.metric == "irr" or b.metric == "ebitda_margin":
            obs_fmt = _fmt_pct(observed)
        elif b.metric == "exit_multiple":
            obs_fmt = _fmt_x(observed)
        elif b.metric.startswith("lever:"):
            obs_fmt = f"{observed:.0f}"
        else:
            obs_fmt = f"{observed}"
        verdict_tag = _VERDICT_TAG.get(b.verdict, b.verdict)
        rows.append(f"| `{b.metric}` | {obs_fmt} | {verdict_tag} | {b.rationale} |")
    return "\n".join(rows)


def _render_hits_md(hits: List[HeuristicHit]) -> str:
    if not hits:
        return "_No pattern flags fired — nothing in the rulebook triggered._"
    lines: List[str] = []
    for h in hits:
        marker = _SEV_EMOJI_MD.get(h.severity, " ")
        lines.append(f"- `{marker}` **[{h.severity}]** {h.title}")
        if h.partner_voice:
            lines.append(f"  > {h.partner_voice}")
        if h.remediation:
            lines.append(f"  - _Remediation:_ {h.remediation}")
    return "\n".join(lines)


# ── Plain text ───────────────────────────────────────────────────────

def render_text(review: PartnerReview) -> str:
    """Render a PartnerReview as a plaintext brief (CLI-friendly)."""
    ctx = review.context_summary
    name = review.deal_name or review.deal_id or "(unnamed deal)"
    lines: List[str] = [
        f"IC MEMO — {name}",
        "=" * (len(name) + 12),
        "",
        f"Recommendation : {review.narrative.recommendation}",
        f"Rationale      : {review.narrative.recommendation_rationale}",
        f"Headline       : {review.narrative.headline}",
        "",
        "CONTEXT",
        f"  EBITDA        : {_fmt_dollars_m(ctx.get('ebitda_m'))}",
        f"  Type          : {ctx.get('hospital_type') or 'n/a'}",
        f"  Payer mix     : {_fmt_payer_mix_md(ctx.get('payer_mix') or {})}",
        f"  IRR / MOIC    : {_fmt_pct(ctx.get('projected_irr'))} / {_fmt_x(ctx.get('projected_moic'))}",
        f"  Hold          : {ctx.get('hold_years') or 'n/a'} years",
        f"  Entry / Exit  : {_fmt_x(ctx.get('entry_multiple'))} / {_fmt_x(ctx.get('exit_multiple'))}",
        f"  Leverage      : {_fmt_x(ctx.get('leverage_multiple'))}",
        "",
        "BULL CASE",
        "  " + review.narrative.bull_case,
        "",
        "BEAR CASE",
        "  " + review.narrative.bear_case,
        "",
        "REASONABLENESS",
    ]
    for b in review.reasonableness_checks:
        tag = _VERDICT_TAG.get(b.verdict, b.verdict)
        lines.append(f"  [{tag:7}] {b.metric:20} {b.rationale}")
    lines += ["", "PATTERN FLAGS"]
    if not review.heuristic_hits:
        lines.append("  (none)")
    else:
        for h in review.heuristic_hits:
            lines.append(f"  [{h.severity:8}] {h.title}")
            if h.partner_voice:
                lines.append(f"      \"{h.partner_voice}\"")
    lines += ["", "KEY QUESTIONS"]
    for i, q in enumerate(review.narrative.key_questions, 1):
        lines.append(f"  {i}. {q}")
    lines += ["", "DICTATION", f"  {review.narrative.ic_memo_paragraph}", ""]
    return "\n".join(lines)


# ── HTML ─────────────────────────────────────────────────────────────

def render_html(review: PartnerReview) -> str:
    """Render a PartnerReview as inline HTML for the workbench.

    Uses the project's dark-mode palette via CSS variables. Output is
    a self-contained fragment — the caller wraps it in a page shell.
    """
    ctx = review.context_summary
    name = html.escape(review.deal_name or review.deal_id or "(unnamed deal)")
    rec = html.escape(review.narrative.recommendation)
    rec_rationale = html.escape(review.narrative.recommendation_rationale or "")
    headline = html.escape(review.narrative.headline or "")
    bull = html.escape(review.narrative.bull_case or "")
    bear = html.escape(review.narrative.bear_case or "")
    dictation = html.escape(review.narrative.ic_memo_paragraph or "")

    rec_color = _rec_color_html(review.narrative.recommendation)

    parts: List[str] = [
        '<article class="ic-memo">',
        f'<header class="ic-memo__header">',
        f'<h1>IC Memo — {name}</h1>',
        f'<div class="ic-memo__rec" style="color:{rec_color}">',
        f'<strong>{rec}</strong> &middot; {rec_rationale}',
        "</div>",
        f'<p class="ic-memo__headline">{headline}</p>',
        "</header>",
        '<section class="ic-memo__context"><h2>Context</h2><dl>',
        f'<dt>EBITDA</dt><dd>{html.escape(_fmt_dollars_m(ctx.get("ebitda_m")))}</dd>',
        f'<dt>Type</dt><dd>{html.escape(str(ctx.get("hospital_type") or "n/a"))}</dd>',
        f'<dt>Payer mix</dt><dd>{html.escape(_fmt_payer_mix_md(ctx.get("payer_mix") or {}))}</dd>',
        f'<dt>IRR / MOIC</dt>',
        f'<dd>{html.escape(_fmt_pct(ctx.get("projected_irr")))} / {html.escape(_fmt_x(ctx.get("projected_moic")))}</dd>',
        f'<dt>Entry → Exit multiple</dt>',
        f'<dd>{html.escape(_fmt_x(ctx.get("entry_multiple")))} → {html.escape(_fmt_x(ctx.get("exit_multiple")))}</dd>',
        "</dl></section>",
        '<section class="ic-memo__cases">',
        f'<h2>Bull case</h2><p>{bull}</p>',
        f'<h2>Bear case</h2><p>{bear}</p>',
        "</section>",
        '<section class="ic-memo__bands"><h2>Reasonableness</h2>',
        _render_band_table_html(review.reasonableness_checks),
        "</section>",
        '<section class="ic-memo__flags"><h2>Pattern flags</h2>',
        _render_hits_html(review.heuristic_hits),
        "</section>",
        '<section class="ic-memo__questions"><h2>Key questions</h2><ol>',
    ]
    for q in review.narrative.key_questions:
        parts.append(f"<li>{html.escape(q)}</li>")
    parts += [
        "</ol></section>",
        f'<blockquote class="ic-memo__dictation">{dictation}</blockquote>',
        "</article>",
    ]
    return "".join(parts)


def _rec_color_html(rec: str) -> str:
    return {
        "PASS": "#EF4444",
        "PROCEED_WITH_CAVEATS": "#F59E0B",
        "PROCEED": "#10B981",
        "STRONG_PROCEED": "var(--sc-navy)",
    }.get(rec, "inherit")


def _render_band_table_html(bands: List[BandCheck]) -> str:
    if not bands:
        return "<p><em>No reasonableness checks ran.</em></p>"
    rows = ["<table class='ic-memo__table'><thead><tr><th>Metric</th><th>Observed</th>"
            "<th>Verdict</th><th>Rationale</th></tr></thead><tbody>"]
    for b in bands:
        observed = b.observed
        obs_fmt = "n/a"
        if observed is not None:
            if b.metric in ("irr", "ebitda_margin"):
                obs_fmt = _fmt_pct(observed)
            elif b.metric == "exit_multiple":
                obs_fmt = _fmt_x(observed)
            else:
                obs_fmt = f"{observed:.2f}" if isinstance(observed, float) else str(observed)
        verdict_tag = _VERDICT_TAG.get(b.verdict, b.verdict)
        rows.append(
            f"<tr><td><code>{html.escape(b.metric)}</code></td>"
            f"<td>{html.escape(obs_fmt)}</td>"
            f"<td class='verdict verdict--{html.escape(b.verdict.lower())}'>{html.escape(verdict_tag)}</td>"
            f"<td>{html.escape(b.rationale or '')}</td></tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _render_hits_html(hits: List[HeuristicHit]) -> str:
    if not hits:
        return "<p><em>No pattern flags fired.</em></p>"
    parts = ["<ul class='ic-memo__flag-list'>"]
    for h in hits:
        parts.append(
            f"<li class='severity severity--{html.escape(h.severity.lower())}'>"
            f"<strong>[{html.escape(h.severity)}]</strong> {html.escape(h.title)}"
        )
        if h.partner_voice:
            parts.append(f"<blockquote>{html.escape(h.partner_voice)}</blockquote>")
        if h.remediation:
            parts.append(f"<small>Remediation: {html.escape(h.remediation)}</small>")
        parts.append("</li>")
    parts.append("</ul>")
    return "".join(parts)


# ── Export all three ─────────────────────────────────────────────────

def render_all(review: PartnerReview) -> Dict[str, str]:
    """Render every format; returns ``{"markdown": ..., "text": ..., "html": ...}``."""
    return {
        "markdown": render_markdown(review),
        "text": render_text(review),
        "html": render_html(review),
    }
