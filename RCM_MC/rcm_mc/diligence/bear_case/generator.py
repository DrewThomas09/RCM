"""Bear Case Auto-Generator orchestrator.

Given a ThesisPipelineReport (or individual module outputs),
produces a ranked, themed, cited bear case with:

    * a partner-facing headline naming the 3 biggest drivers
      that could break the thesis
    * ranked Evidence list (CRITICAL → HIGH → MEDIUM) with
      citation keys and source-module deep links
    * combined EBITDA-at-risk tally across overlapping themes
      (dedup regulatory + bridge overlap)
    * IC-memo-drop-in HTML block partners can copy into the
      memo directly
    * per-theme narrative paragraphs (regulatory, credit,
      operational, market, pattern)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .evidence import (
    Evidence, EvidenceSeverity, EvidenceSource, EvidenceTheme,
    extract_autopsy_evidence, extract_bridge_audit_evidence,
    extract_covenant_evidence, extract_deal_mc_evidence,
    extract_exit_timing_evidence, extract_hcris_xray_evidence,
    extract_payer_stress_evidence, extract_regulatory_evidence,
)


@dataclass
class BearCaseReport:
    """Partner-facing bear-case output."""
    target_name: str
    evidence: List[Evidence] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    combined_ebitda_at_risk_usd: float = 0.0
    thesis_breakers_named: List[str] = field(default_factory=list)
    narrative_by_theme: Dict[str, str] = field(default_factory=dict)
    headline: str = ""
    top_line_summary: str = ""
    ic_memo_html: str = ""
    sources_active: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "evidence": [e.to_dict() for e in self.evidence],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "combined_ebitda_at_risk_usd":
                self.combined_ebitda_at_risk_usd,
            "thesis_breakers_named": list(self.thesis_breakers_named),
            "narrative_by_theme": dict(self.narrative_by_theme),
            "headline": self.headline,
            "top_line_summary": self.top_line_summary,
            "ic_memo_html": self.ic_memo_html,
            "sources_active": list(self.sources_active),
        }


# ────────────────────────────────────────────────────────────────────
# Ranking + dedupe + narrative
# ────────────────────────────────────────────────────────────────────

def _rank_evidence(evidence: List[Evidence]) -> List[Evidence]:
    """Sort by (severity, abs($ impact), source priority)."""
    source_priority = {
        EvidenceSource.COVENANT_STRESS: 0,
        EvidenceSource.REGULATORY_CALENDAR: 1,
        EvidenceSource.BRIDGE_AUDIT: 2,
        EvidenceSource.DEAL_AUTOPSY: 3,
        EvidenceSource.HCRIS_XRAY: 4,
        EvidenceSource.PAYER_STRESS: 5,
        EvidenceSource.DEAL_MC: 6,
        EvidenceSource.EXIT_TIMING: 7,
    }
    def key(e: Evidence):
        impact = abs(e.ebitda_impact_usd) if e.ebitda_impact_usd else 0.0
        return (
            e.severity_rank,
            -impact,
            source_priority.get(e.source, 9),
        )
    return sorted(evidence, key=key)


def _assign_citation_keys(evidence: List[Evidence]) -> None:
    """Mutates Evidence in place with R1/R2, C1/C2, B1/B2... keys."""
    prefix_map = {
        EvidenceSource.REGULATORY_CALENDAR: "R",
        EvidenceSource.COVENANT_STRESS: "C",
        EvidenceSource.BRIDGE_AUDIT: "B",
        EvidenceSource.DEAL_MC: "M",
        EvidenceSource.DEAL_AUTOPSY: "A",
        EvidenceSource.EXIT_TIMING: "E",
        EvidenceSource.PAYER_STRESS: "P",
        EvidenceSource.HCRIS_XRAY: "H",
    }
    counters: Dict[EvidenceSource, int] = {}
    for e in evidence:
        counters[e.source] = counters.get(e.source, 0) + 1
        e.citation_key = f"{prefix_map.get(e.source, 'X')}{counters[e.source]}"


def _combined_ebitda_at_risk(evidence: List[Evidence]) -> float:
    """Sum $ impact avoiding double-count of obvious overlaps.

    Regulatory overlay already aggregates per-driver impacts, so we
    pick the single largest regulatory-source evidence rather than
    summing.  Bridge-audit total_gap also rolls up per-lever gaps,
    so we similarly pick the largest bridge-source evidence.  Covenant
    cures and Autopsy pattern don't dollarize consistently, so they
    don't contribute to the $ tally.
    """
    regulatory_max = 0.0
    bridge_max = 0.0
    other_total = 0.0
    for e in evidence:
        impact = abs(e.ebitda_impact_usd or 0.0)
        if impact == 0:
            continue
        if e.source == EvidenceSource.REGULATORY_CALENDAR:
            regulatory_max = max(regulatory_max, impact)
        elif e.source == EvidenceSource.BRIDGE_AUDIT:
            bridge_max = max(bridge_max, impact)
        else:
            other_total += impact
    return regulatory_max + bridge_max + other_total


def _narrative_for_theme(
    theme: EvidenceTheme,
    items: List[Evidence],
) -> str:
    if not items:
        return ""
    # Order by severity
    items = sorted(items, key=lambda e: e.severity_rank)
    bullets = []
    for e in items[:3]:
        ck = e.citation_key or e.title[:20]
        bullets.append(
            f"[{ck}] {e.title}"
        )
    bullet_text = "; ".join(bullets)
    theme_label = {
        EvidenceTheme.REGULATORY: "Regulatory",
        EvidenceTheme.CREDIT: "Credit / covenant",
        EvidenceTheme.OPERATIONAL: "Operational / RCM bridge",
        EvidenceTheme.MARKET: "Market / distribution",
        EvidenceTheme.STRUCTURAL: "Deal structure",
        EvidenceTheme.PATTERN: "Historical pattern",
    }.get(theme, theme.value.title())
    critical_bits = [
        e for e in items
        if e.severity == EvidenceSeverity.CRITICAL
    ]
    if critical_bits:
        lead = (
            f"{theme_label} risk is material — "
            f"{len(critical_bits)} CRITICAL + "
            f"{len(items) - len(critical_bits)} secondary evidence item"
            f"{'s' if (len(items) - len(critical_bits)) != 1 else ''}."
        )
    else:
        lead = (
            f"{theme_label} risk is elevated — "
            f"{len(items)} evidence item"
            f"{'s' if len(items) != 1 else ''}."
        )
    return f"{lead} {bullet_text}."


def _build_headline(
    target: str,
    ranked: List[Evidence],
    at_risk_usd: float,
) -> str:
    if not ranked:
        return (
            f"{target}: no material bear-case evidence surfaced "
            f"across the modules run. The thesis passes automated "
            f"screens — partners should still write a manual "
            f"counter-narrative before IC."
        )
    top = ranked[:3]
    names = [e.title.split(" ")[0:5] for e in top]
    # Partner-ready headline
    critical = [
        e for e in ranked if e.severity == EvidenceSeverity.CRITICAL
    ]
    if critical:
        head = (
            f"Thesis is at risk on "
            f"{len(critical)} CRITICAL evidence item"
            f"{'s' if len(critical) != 1 else ''}"
        )
    else:
        head = f"Thesis is at risk on {len(ranked)} material item{'s' if len(ranked) != 1 else ''}"
    if at_risk_usd >= 1_000_000:
        head += (
            f" — combined ${at_risk_usd/1e6:.1f}M of EBITDA at risk"
        )
    head += "."
    # Add "thesis breakers" naming
    breakers = []
    for e in top:
        if e.source == EvidenceSource.REGULATORY_CALENDAR:
            first_kill = e.metadata.get("first_kill_date")
            if first_kill:
                breakers.append(f"regulatory event on {first_kill}")
            else:
                breakers.append("regulatory exposure")
        elif e.source == EvidenceSource.COVENANT_STRESS:
            cov = e.metadata.get("covenant_name", "covenant")
            breakers.append(f"{cov} covenant")
        elif e.source == EvidenceSource.BRIDGE_AUDIT:
            lever = e.metadata.get("lever_name", "bridge lever")
            breakers.append(f"'{lever}' bridge realization")
        elif e.source == EvidenceSource.DEAL_AUTOPSY:
            matched = e.metadata.get("matched_deal", "historical failure")
            breakers.append(f"{matched} signature")
        elif e.source == EvidenceSource.DEAL_MC:
            breakers.append("Monte Carlo P10 downside")
        elif e.source == EvidenceSource.EXIT_TIMING:
            breakers.append("exit-hurdle failure")
    if breakers:
        head += f" Top drivers: {', '.join(breakers[:3])}."
    return head


def _build_ic_memo_html(
    target: str,
    ranked: List[Evidence],
    at_risk_usd: float,
) -> str:
    """Drop-in IC-memo ready HTML block. Print-friendly, light theme."""
    rows = []
    for e in ranked[:8]:
        tone = {
            EvidenceSeverity.CRITICAL: "#b91c1c",
            EvidenceSeverity.HIGH: "#d97706",
            EvidenceSeverity.MEDIUM: "#64748b",
            EvidenceSeverity.LOW: "#94a3b8",
        }[e.severity]
        impact = (
            f" · ${e.ebitda_impact_usd/1e6:+,.1f}M impact"
            if e.ebitda_impact_usd else ""
        )
        rows.append(
            f'<tr><td style="padding:6px 10px;vertical-align:top;'
            f'font-weight:700;color:{tone};font-family:monospace;">'
            f'[{e.citation_key}] {e.severity.value}</td>'
            f'<td style="padding:6px 10px;vertical-align:top;">'
            f'<div style="font-weight:600;">'
            f'{e.title}{impact}</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:3px;">'
            f'{e.narrative}</div></td></tr>'
        )
    return (
        f'<section style="font-family:Georgia,serif;color:#1a1a1a;'
        f'padding:16px 20px;background:#fff;border:1px solid #e5e7eb;'
        f'border-radius:4px;page-break-before:always;">'
        f'<div style="font-size:11px;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:#64748b;font-weight:600;">'
        f'Bear Case · auto-generated</div>'
        f'<h2 style="font-size:20px;margin:6px 0 10px 0;">'
        f'{target} — What Could Break the Thesis</h2>'
        f'<div style="padding:10px 14px;background:#fef2f2;'
        f'border-left:3px solid #b91c1c;font-size:13px;'
        f'line-height:1.6;margin-bottom:12px;">'
        f'<strong>Combined EBITDA at risk:</strong> '
        f'${at_risk_usd/1e6:,.1f}M. {len([e for e in ranked if e.severity == EvidenceSeverity.CRITICAL])} CRITICAL + '
        f'{len([e for e in ranked if e.severity == EvidenceSeverity.HIGH])} HIGH evidence items across '
        f'{len(set(e.source for e in ranked))} source modules.'
        f'</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:13px;">'
        f'<tbody>{"".join(rows)}</tbody></table>'
        f'<div style="font-size:11px;color:#64748b;line-height:1.5;'
        f'margin-top:12px;">Auto-generated from Regulatory Calendar '
        f'× Covenant Stress × Bridge Audit × Deal MC × Deal '
        f'Autopsy. Citations map to source-module detail pages. '
        f'Refresh before IC.</div>'
        f'</section>'
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def generate_bear_case(
    *,
    target_name: str = "Target",
    regulatory_exposure: Any = None,
    covenant_stress: Any = None,
    bridge_audit: Any = None,
    deal_mc_result: Any = None,
    deal_scenario: Any = None,
    exit_timing: Any = None,
    autopsy_matches: Any = None,
    payer_stress: Any = None,
    hcris_xray: Any = None,
) -> BearCaseReport:
    """Compose a full bear case from whichever inputs are provided.

    All inputs are optional — the generator runs every extractor
    defensively and simply gets no evidence from silent modules.
    This means partners running only a subset of the pipeline still
    get a useful bear case from what's available.
    """
    raw_evidence: List[Evidence] = []
    sources_active: List[str] = []

    if regulatory_exposure is not None:
        items = extract_regulatory_evidence(regulatory_exposure)
        if items:
            raw_evidence.extend(items)
            sources_active.append("REGULATORY_CALENDAR")

    if covenant_stress is not None:
        items = extract_covenant_evidence(covenant_stress)
        if items:
            raw_evidence.extend(items)
            sources_active.append("COVENANT_STRESS")

    if bridge_audit is not None:
        items = extract_bridge_audit_evidence(bridge_audit)
        if items:
            raw_evidence.extend(items)
            sources_active.append("BRIDGE_AUDIT")

    if deal_mc_result is not None:
        items = extract_deal_mc_evidence(deal_mc_result, deal_scenario)
        if items:
            raw_evidence.extend(items)
            sources_active.append("DEAL_MC")

    if exit_timing is not None:
        items = extract_exit_timing_evidence(exit_timing)
        if items:
            raw_evidence.extend(items)
            sources_active.append("EXIT_TIMING")

    if autopsy_matches is not None:
        items = extract_autopsy_evidence(autopsy_matches)
        if items:
            raw_evidence.extend(items)
            sources_active.append("DEAL_AUTOPSY")

    if payer_stress is not None:
        items = extract_payer_stress_evidence(payer_stress)
        if items:
            raw_evidence.extend(items)
            sources_active.append("PAYER_STRESS")

    if hcris_xray is not None:
        items = extract_hcris_xray_evidence(hcris_xray)
        if items:
            raw_evidence.extend(items)
            sources_active.append("HCRIS_XRAY")

    ranked = _rank_evidence(raw_evidence)
    _assign_citation_keys(ranked)

    # Counts
    critical_count = sum(
        1 for e in ranked if e.severity == EvidenceSeverity.CRITICAL
    )
    high_count = sum(
        1 for e in ranked if e.severity == EvidenceSeverity.HIGH
    )
    medium_count = sum(
        1 for e in ranked if e.severity == EvidenceSeverity.MEDIUM
    )
    at_risk = _combined_ebitda_at_risk(ranked)

    # Thesis breakers (deduped list of driver/lever/covenant names)
    breakers: List[str] = []
    seen = set()
    for e in ranked[:6]:
        if e.source == EvidenceSource.REGULATORY_CALENDAR:
            key = e.metadata.get("driver_id") or e.title
            if key not in seen:
                seen.add(key)
                breakers.append(key)
        elif e.source == EvidenceSource.COVENANT_STRESS:
            key = f"covenant:{e.metadata.get('covenant_name', '')}"
            if key not in seen:
                seen.add(key)
                breakers.append(e.metadata.get("covenant_name", ""))
        elif e.source == EvidenceSource.BRIDGE_AUDIT:
            key = f"lever:{e.metadata.get('lever_name', '')}"
            if key not in seen:
                seen.add(key)
                breakers.append(e.metadata.get("lever_name", ""))

    # Per-theme narratives
    themes: Dict[str, List[Evidence]] = {}
    for e in ranked:
        themes.setdefault(e.theme.value, []).append(e)
    narrative_by_theme: Dict[str, str] = {}
    for theme_val, items in themes.items():
        narrative_by_theme[theme_val] = _narrative_for_theme(
            EvidenceTheme(theme_val), items,
        )

    headline = _build_headline(target_name, ranked, at_risk)

    # Top-line summary paragraph
    if ranked:
        top3 = ranked[:3]
        top_line = (
            f"The three largest bear-case drivers are "
            f"[{top3[0].citation_key}] "
            f"{top3[0].title[:60]}"
            + (f", [{top3[1].citation_key}] {top3[1].title[:60]}"
               if len(top3) > 1 else "")
            + (f", and [{top3[2].citation_key}] {top3[2].title[:60]}"
               if len(top3) > 2 else "")
            + ". Combined EBITDA at risk across the bear case is "
            f"${at_risk/1e6:,.1f}M. "
            f"{critical_count} CRITICAL, {high_count} HIGH, and "
            f"{medium_count} MEDIUM evidence items drawn from "
            f"{len(sources_active)} source module"
            f"{'s' if len(sources_active) != 1 else ''} "
            f"({', '.join(sources_active)})."
        )
    else:
        top_line = (
            "No bear-case evidence surfaced from the modules run. "
            "Run the full Thesis Pipeline to ensure all sources "
            "executed."
        )

    ic_memo_html = _build_ic_memo_html(target_name, ranked, at_risk)

    return BearCaseReport(
        target_name=target_name,
        evidence=ranked,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        combined_ebitda_at_risk_usd=at_risk,
        thesis_breakers_named=breakers,
        narrative_by_theme=narrative_by_theme,
        headline=headline,
        top_line_summary=top_line,
        ic_memo_html=ic_memo_html,
        sources_active=sources_active,
    )


def generate_bear_case_from_pipeline(
    pipeline_report: Any,
    target_name: str = "",
) -> BearCaseReport:
    """Convenience: pull every source off a ThesisPipelineReport."""
    name = target_name or getattr(
        pipeline_report, "deal_name", None,
    ) or "Target"
    return generate_bear_case(
        target_name=name,
        regulatory_exposure=getattr(
            pipeline_report, "regulatory_exposure", None,
        ),
        covenant_stress=getattr(
            pipeline_report, "covenant_stress", None,
        ),
        bridge_audit=getattr(
            pipeline_report, "bridge_audit", None,
        ),
        deal_mc_result=getattr(
            pipeline_report, "deal_mc_result", None,
        ),
        deal_scenario=getattr(
            pipeline_report, "deal_scenario", None,
        ),
        exit_timing=getattr(
            pipeline_report, "exit_timing_report", None,
        ),
        autopsy_matches=getattr(
            pipeline_report, "autopsy_matches", None,
        ),
        payer_stress=getattr(
            pipeline_report, "payer_stress", None,
        ),
        hcris_xray=getattr(
            pipeline_report, "hcris_xray", None,
        ),
    )
