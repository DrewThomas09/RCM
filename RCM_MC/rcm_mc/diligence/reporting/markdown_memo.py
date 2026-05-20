"""Markdown diligence memo generator (PHI-safe, conservative).

Renders the 11-section PE revenue-cycle memo from already-aggregated
artifacts (analytics, data confidence, findings, follow-ups). It
consumes **only aggregates** — no claim lines, no patient tokens, no
member IDs — so the output is safe to paste into a deal workstream and
safe to hand to an LLM (plan §"MEMO GENERATION" / "SECURITY").

Language is conservative throughout: estimated / potentially
preventable / directional / requires validation. Never "guaranteed
EBITDA".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Sequence

from ..analytics.revenue_leakage import AnalyticsResult
from ..findings.finding_generator import Finding
from ..findings.follow_up_generator import FollowUpPackage
from ..reconciliation.data_confidence import DataConfidenceReport


@dataclass
class MemoContext:
    deal_name: str = "Target"
    source_file_count: int = 0
    transaction_types: Sequence[str] = ()
    period_label: Optional[str] = None
    prepared_on: Optional[str] = None


def _money(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"${v:,.0f}"


def _pct(v: Optional[float]) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def render_markdown_memo(
    *,
    analytics: AnalyticsResult,
    confidence: DataConfidenceReport,
    findings: Sequence[Finding],
    follow_ups: FollowUpPackage,
    context: Optional[MemoContext] = None,
) -> str:
    ctx = context or MemoContext()
    t = analytics.totals
    prepared = ctx.prepared_on or date.today().isoformat()
    L: List[str] = []
    add = L.append

    add(f"# Revenue-Cycle Diligence Memo — {ctx.deal_name}")
    add("")
    add(f"_Prepared {prepared} · snapshot-based · PHI-aggregated. "
        f"Directional signal pending management validation._")
    add("")

    # 1 — Executive summary
    add("## 1. Executive summary")
    add("")
    add(f"- **Data Confidence Score:** {confidence.score}/100")
    add(f"- **Gross charges reviewed:** {_money(t.gross_charges)} across "
        f"{t.claim_count:,} claim lines")
    add(f"- **Realized cash (paid):** {_money(t.paid_amount)} "
        f"(gross collection rate {_pct(t.gross_collection_rate)})")
    add(f"- **Estimated potentially preventable leakage:** "
        f"{_money(t.potentially_preventable_leakage)} "
        f"(upper bound; excludes contractual adjustments)")
    add(f"- **Findings raised:** {len(findings)}")
    add("")

    # 2 — Data reviewed
    add("## 2. Data reviewed")
    add("")
    txns = ", ".join(ctx.transaction_types) if ctx.transaction_types else "n/a"
    add(f"- Source files: {ctx.source_file_count}")
    add(f"- Transaction types: {txns}")
    if ctx.period_label:
        add(f"- Period: {ctx.period_label}")
    add(f"- Canonical claim lines: {t.claim_count:,}")
    add("")

    # 3 — Data quality and limitations
    add("## 3. Data quality and limitations")
    add("")
    for s in confidence.summaries:
        add(f"- {s}")
    if confidence.issues:
        add("")
        add("Open data-quality issues:")
        for i in confidence.issues:
            add(f"- _{i.severity}_ — {i.message}")
    add("")

    # 4 — Revenue leakage overview
    add("## 4. Revenue leakage overview")
    add("")
    add("| Metric | Amount |")
    add("|---|---|")
    add(f"| Gross charges | {_money(t.gross_charges)} |")
    add(f"| Allowed amount | {_money(t.allowed_amount)} |")
    add(f"| Paid amount | {_money(t.paid_amount)} |")
    add(f"| Contractual adjustments (not leakage) | {_money(t.contractual_adjustments)} |")
    add(f"| Denial dollars (non-contractual) | {_money(t.denial_dollars)} |")
    add(f"| Patient responsibility | {_money(t.patient_responsibility)} |")
    add(f"| Potentially preventable leakage (est.) | {_money(t.potentially_preventable_leakage)} |")
    add("")
    if analytics.by_category:
        add("Denial dollars by category (preventability):")
        add("")
        add("| Category | Dollars | Preventability | EBITDA relevance |")
        add("|---|---|---|---|")
        for c in analytics.by_category:
            if c.category == "CONTRACTUAL":
                continue
            add(f"| {c.category} | {_money(c.dollars)} | {c.preventability} "
                f"| {c.ebitda_relevance} |")
        add("")

    # 5 — Payer-level findings
    add("## 5. Payer-level findings")
    add("")
    if analytics.by_payer:
        add("| Payer | Claims | Paid | Denial $ | Paid/Charge |")
        add("|---|---|---|---|---|")
        for p in analytics.by_payer[:10]:
            add(f"| {p.key} | {p.claim_count:,} | {_money(p.paid)} "
                f"| {_money(p.denial_dollars)} | {_pct(p.paid_to_charge)} |")
    else:
        add("_No payer-level data available._")
    add("")

    # 6 — Procedure/CPT-level findings
    add("## 6. Procedure / CPT-level findings")
    add("")
    if analytics.by_cpt:
        add("| CPT | Claims | Paid | Denial $ | Paid/Charge |")
        add("|---|---|---|---|---|")
        for c in analytics.by_cpt[:10]:
            add(f"| {c.key} | {c.claim_count:,} | {_money(c.paid)} "
                f"| {_money(c.denial_dollars)} | {_pct(c.paid_to_charge)} |")
    else:
        add("_No procedure-level data available._")
    add("")

    # 7 — Provider-level findings
    add("## 7. Provider-level findings")
    add("")
    if analytics.by_provider:
        add("| Provider NPI | Claims | Denial $ | Denial rate ($) |")
        add("|---|---|---|---|")
        for p in analytics.by_provider[:10]:
            add(f"| {p.key} | {p.claim_count:,} | {_money(p.denial_dollars)} "
                f"| {_pct(p.denial_rate_dollars)} |")
    else:
        add("_No provider-level data available._")
    add("")

    # 8 — Potential EBITDA implications
    add("## 8. Potential EBITDA implications")
    add("")
    add(f"An estimated **{_money(t.potentially_preventable_leakage)}** of "
        f"potentially preventable leakage was identified. This is an "
        f"upper-bound, pre-validation estimate of operational recovery "
        f"opportunity — **not guaranteed EBITDA**. Realizable value depends "
        f"on appeal history, payer contracts, AR aging, and management "
        f"workflow, and is subject to management confirmation.")
    add("")
    if findings:
        add("Findings:")
        add("")
        for f in findings:
            add(f"### {f.title}")
            add(f"- _Confidence:_ {f.confidence}")
            if f.estimated_impact_amount is not None:
                add(f"- _Estimated impact:_ {_money(f.estimated_impact_amount)} (estimate)")
            add(f"- {f.summary}")
            for lim in f.limitations:
                add(f"  - _Caveat:_ {lim}")
            add("")

    # 9 — Follow-up diligence questions
    add("## 9. Follow-up diligence questions")
    add("")
    for q in follow_ups.questions:
        add(f"- {q}")
    add("")

    # 10 — Additional data requests
    add("## 10. Additional data requests")
    add("")
    for d in follow_ups.document_requests:
        add(f"- {d}")
    add("")

    # 11 — Methodology and caveats
    add("## 11. Methodology and caveats")
    add("")
    add("- Snapshot-based analysis of VDR-exported 835/837 files; no live "
        "system access.")
    add("- Patient/member identifiers are tokenized; this memo contains "
        "aggregate figures only — no patient-level data.")
    add("- Contractual adjustments are excluded from leakage. Patient "
        "responsibility is not counted as recoverable upside.")
    add("- Denial categorization uses X12 CARC reason codes; unmapped codes "
        "are flagged for manual review.")
    add("- All figures are directional and **subject to validation** against "
        "appeal history, payer contracts, and AR aging.")
    add("")
    return "\n".join(L)
