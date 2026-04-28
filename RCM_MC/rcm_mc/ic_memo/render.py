"""IC memo rendering — markdown + self-contained HTML."""
from __future__ import annotations

import html as _html
from typing import List

from .memo import ICMemo


def _format_money(mm: float) -> str:
    if mm is None:
        return "—"
    if abs(mm) >= 1000:
        return f"${mm/1000:.2f}B"
    if abs(mm) >= 1:
        return f"${mm:.1f}M"
    return f"${mm*1000:.0f}K"


def render_memo_markdown(memo: ICMemo) -> str:
    """Render the IC memo as a single markdown string ready to
    paste into an IC pre-read."""
    lines: List[str] = []
    lines.append(f"# Investment Committee Memo — {memo.deal_name}")
    lines.append("")

    # ── 1. Executive Summary ────────────────────────────────
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(
        f"- **Deal:** {memo.deal_name} (ID: `{memo.deal_id}`)")
    lines.append(
        f"- **Sector:** {memo.sector}; "
        f"**states:** "
        f"{', '.join(memo.states) if memo.states else 'n/a'}.")
    lines.append(
        f"- **Revenue / EBITDA:** "
        f"{_format_money(memo.revenue_mm)} / "
        f"{_format_money(memo.ebitda_mm)} "
        f"({memo.ebitda_margin*100:.1f}% margin).")
    if memo.scenarios:
        lines.append(
            f"- **Base-case MOIC:** "
            f"{memo.scenarios.base.moic:.2f}× "
            f"({memo.scenarios.base.irr*100:.1f}% IRR over "
            f"{memo.scenarios.base.entry_equity_mm:.0f}M "
            f"entry equity → "
            f"{memo.scenarios.base.exit_equity_mm:.0f}M exit "
            f"equity).")
    lines.append(
        f"- **Risk count:** {len(memo.risks)} flagged.")
    lines.append("")

    # ── 2. Target Overview ──────────────────────────────────
    lines.append("## 2. Target Overview")
    lines.append("")
    ov = memo.target_overview
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Revenue | {_format_money(ov.get('revenue_mm', 0))} |")
    lines.append(f"| EBITDA | {_format_money(ov.get('ebitda_mm', 0))} |")
    if ov.get("adjusted_ebitda_mm") and (
            ov["adjusted_ebitda_mm"] != ov.get("ebitda_mm")):
        lines.append(
            f"| EBITDA (QoE-adjusted) | "
            f"{_format_money(ov['adjusted_ebitda_mm'])} |")
    lines.append(
        f"| EBITDA margin | "
        f"{ov.get('ebitda_margin', 0)*100:.1f}% |")
    lines.append(f"| Growth rate | "
                 f"{ov.get('growth_rate', 0)*100:.1f}% |")
    lines.append(
        f"| States | "
        f"{', '.join(ov.get('states', [])) or '—'} |")
    lines.append("")

    # ── 3. Investment Thesis ───────────────────────────────
    lines.append("## 3. Investment Thesis")
    lines.append("")
    for b in memo.thesis_bullets:
        lines.append(f"- {b}")
    lines.append("")

    # ── 4. Comparable Transactions ──────────────────────────
    lines.append("## 4. Comparable Transactions")
    lines.append("")
    if memo.comparables and memo.comparables.matches:
        lines.append(
            f"Method: **{memo.comparables.method.upper()}** "
            f"({memo.comparables.n_matches} matches)")
        lines.append("")
        edist = memo.comparables.entry_multiple_distribution
        if edist.get("p50") is not None:
            lines.append(
                f"- Entry multiple distribution: p25 "
                f"{edist.get('p25', 0):.1f}× / p50 "
                f"{edist['p50']:.1f}× / p75 "
                f"{edist.get('p75', 0):.1f}×")
        xdist = memo.comparables.exit_multiple_distribution
        if xdist.get("p50") is not None:
            lines.append(
                f"- Exit multiple distribution: p25 "
                f"{xdist.get('p25', 0):.1f}× / p50 "
                f"{xdist['p50']:.1f}× / p75 "
                f"{xdist.get('p75', 0):.1f}×")
        margin = memo.comparables.margin_expansion_distribution
        if margin.get("p50") is not None:
            lines.append(
                f"- Median margin expansion among comps: "
                f"{margin['p50']*100:+.1f} pp")
    else:
        lines.append(
            "No comparable transactions in the result. Run the "
            "DealComparablesEngine on this target before IC.")
    lines.append("")

    # ── 5. Predictions & EBITDA Bridge ──────────────────────
    lines.append("## 5. Predictions & EBITDA Bridge")
    lines.append("")
    if memo.bridge:
        lines.append(
            f"- Reported EBITDA: "
            f"**{_format_money(memo.bridge.reported_ebitda_mm)}**")
        lines.append(
            f"- QoE-adjusted EBITDA: "
            f"**{_format_money(memo.bridge.adjusted_ebitda_mm)}**")
        lines.append(
            f"- Confidence-weighted: "
            f"**{_format_money(memo.bridge.confidence_weighted_adjusted_ebitda_mm)}**")
        if memo.bridge.adjustments:
            lines.append("")
            lines.append("**Material adjustments:**")
            for adj in memo.bridge.adjustments[:8]:
                sign = "+" if adj.amount_mm > 0 else "−"
                lines.append(
                    f"- [{adj.category}] {adj.label}: "
                    f"{sign}{_format_money(abs(adj.amount_mm))} "
                    f"(conf {adj.confidence:.0%})")
    else:
        lines.append(
            "QoE bridge not yet built — partner to run the "
            "QoE-AutoFlagger before circulating this memo.")
    lines.append("")

    # ── 6. Scenarios ────────────────────────────────────────
    lines.append("## 6. Scenarios — Bull / Base / Bear")
    lines.append("")
    if memo.scenarios:
        lines.append(
            "| Scenario | MOIC | IRR | Entry Equity | "
            "Exit Equity |")
        lines.append("|---|---:|---:|---:|---:|")
        for s in (memo.scenarios.bull, memo.scenarios.base,
                  memo.scenarios.bear):
            lines.append(
                f"| **{s.name.upper()}** | {s.moic:.2f}× | "
                f"{s.irr*100:.1f}% | "
                f"{_format_money(s.entry_equity_mm)} | "
                f"{_format_money(s.exit_equity_mm)} |")
        lines.append("")
        for s in (memo.scenarios.bull, memo.scenarios.base,
                  memo.scenarios.bear):
            if s.notes:
                lines.append(f"- _{s.name.upper()}_: {s.notes}")
    lines.append("")

    # ── 7. Key Risks ────────────────────────────────────────
    lines.append("## 7. Key Risks")
    lines.append("")
    if memo.risks:
        for r in memo.risks[:8]:
            title = r.get("title", "")
            ebitda_at_risk = r.get("ebitda_at_risk_mm")
            cat = r.get("category", "")
            if ebitda_at_risk:
                lines.append(
                    f"- **[{cat}]** {title} — "
                    f"{_format_money(ebitda_at_risk)} EBITDA at "
                    f"risk")
            else:
                lines.append(f"- **[{cat}]** {title}")
    else:
        lines.append(
            "No flagged risks — partner should still complete a "
            "manual red-flag scan before IC.")
    lines.append("")

    # ── 8. Methodology Appendix ─────────────────────────────
    lines.append("## 8. Methodology Appendix")
    lines.append("")
    if memo.methods_used:
        for m in memo.methods_used:
            lines.append(f"- {m}")
    else:
        lines.append(
            "No methods recorded — IC memo built without the "
            "synthesis stack. Partner should re-run with the "
            "full DiligenceDossier.")
    lines.append("")
    lines.append(
        "_All quantitative outputs are produced by the "
        "RCM-MC platform's pure-numpy implementations of the "
        "named methods. Source code + version are captured in "
        "the deliverable header._")

    return "\n".join(lines) + "\n"


_HTML_CSS = """
:root {
  --c-text: #111827; --c-muted: #6b7280; --c-bg: #fafbfc;
  --c-card: #ffffff; --c-border: #e5e7eb;
  --c-accent: var(--sc-navy); --c-table-head: #f3f4f6;
}
* { box-sizing: border-box; }
body {
  font-family: 'Inter', -apple-system, sans-serif;
  font-size: 14px; line-height: 1.55; color: var(--c-text);
  background: var(--c-bg); margin: 0; padding: 32px 0;
}
.icm-wrap {
  max-width: 880px; margin: 0 auto; padding: 36px 48px;
  background: var(--c-card); border: 1px solid var(--c-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}
h1 {
  font-size: 24px; margin: 0 0 8px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--c-accent);
}
h2 {
  font-size: 17px; margin: 28px 0 10px;
  color: var(--c-accent); font-weight: 600;
}
p { margin: 8px 0; }
ul { margin: 8px 0 14px 0; padding-left: 22px; }
ul li { margin: 3px 0; }
strong { font-weight: 600; }
table {
  width: 100%; border-collapse: collapse;
  margin: 10px 0; font-size: 13px;
  font-variant-numeric: tabular-nums;
}
th, td {
  padding: 8px 12px; border-bottom: 1px solid var(--c-border);
  text-align: left;
}
th {
  background: var(--c-table-head); color: var(--c-muted);
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; font-weight: 600;
}
em { color: var(--c-muted); }
@media print {
  body { background: #fff; padding: 0; }
  .icm-wrap { border: none; box-shadow: none; }
}
"""


def render_memo_html(memo: ICMemo) -> str:
    """Render the IC memo as a self-contained HTML page —
    same minimal markdown→HTML converter as the IC binder."""
    md = render_memo_markdown(memo)
    # Reuse the IC binder's md→html converter for consistency
    from ..ic_binder.html import _md_to_html
    body_html = _md_to_html(md)
    title = f"IC Memo — {memo.deal_name}"
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<title>{_html.escape(title)}</title>\n"
        f"<style>{_HTML_CSS}</style>\n"
        "</head>\n<body>\n"
        '<div class="icm-wrap">\n'
        f"{body_html}\n"
        "</div>\n</body>\n</html>"
    )
