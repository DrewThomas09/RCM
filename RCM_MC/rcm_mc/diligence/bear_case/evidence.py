"""Evidence dataclass + source-specific extractors for the Bear
Case Auto-Generator.

An ``Evidence`` item is one concrete, cited reason the thesis may
break: a regulatory event killing a thesis driver, a covenant path
breaching with equity-cure sizing, an EBITDA bridge lever flagged
as OVERSTATED/UNSUPPORTED, a Deal MC p10 downside, a Deal Autopsy
match to a historical failure.

Each extractor takes one of our existing pipeline outputs and
yields the three or four highest-severity Evidence items from
that source.  The generator then ranks, dedupes, and narrates
them into a partner-facing bear case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceSource(str, Enum):
    REGULATORY_CALENDAR = "REGULATORY_CALENDAR"
    COVENANT_STRESS = "COVENANT_STRESS"
    BRIDGE_AUDIT = "BRIDGE_AUDIT"
    DEAL_MC = "DEAL_MC"
    DEAL_AUTOPSY = "DEAL_AUTOPSY"
    EXIT_TIMING = "EXIT_TIMING"
    PAYER_STRESS = "PAYER_STRESS"
    HCRIS_XRAY = "HCRIS_XRAY"


class EvidenceSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # thesis-breaking on its own
    HIGH = "HIGH"           # material, IC-level risk
    MEDIUM = "MEDIUM"       # worth naming in the memo
    LOW = "LOW"             # footnote


class EvidenceTheme(str, Enum):
    REGULATORY = "REGULATORY"
    CREDIT = "CREDIT"
    OPERATIONAL = "OPERATIONAL"
    MARKET = "MARKET"
    STRUCTURAL = "STRUCTURAL"
    PATTERN = "PATTERN"


@dataclass
class Evidence:
    """One citation in the bear case."""
    title: str
    source: EvidenceSource
    theme: EvidenceTheme
    severity: EvidenceSeverity
    ebitda_impact_usd: Optional[float] = None
    affected_year: Optional[int] = None
    narrative: str = ""
    source_link: str = ""                   # deep-link to source page
    citation_key: str = ""                  # short id for the memo (R1, C2, etc.)
    # Source-specific metadata (kept as a dict so the generator can
    # extend cleanly without new fields)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def severity_rank(self) -> int:
        return {
            EvidenceSeverity.CRITICAL: 0,
            EvidenceSeverity.HIGH: 1,
            EvidenceSeverity.MEDIUM: 2,
            EvidenceSeverity.LOW: 3,
        }[self.severity]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source.value,
            "theme": self.theme.value,
            "severity": self.severity.value,
            "ebitda_impact_usd": self.ebitda_impact_usd,
            "affected_year": self.affected_year,
            "narrative": self.narrative,
            "source_link": self.source_link,
            "citation_key": self.citation_key,
            "metadata": dict(self.metadata),
        }


# ────────────────────────────────────────────────────────────────────
# Source-specific extractors
# ────────────────────────────────────────────────────────────────────
#
# Each extractor is defensive — it accepts ``None`` (source didn't
# run) and returns an empty list.  The generator concatenates
# everyone's output.

def extract_regulatory_evidence(
    exposure_report: Any,
) -> List[Evidence]:
    """Pull KILLED and top DAMAGED drivers from a
    ``RegulatoryExposureReport``."""
    if exposure_report is None:
        return []
    out: List[Evidence] = []
    try:
        timelines = getattr(exposure_report, "driver_timelines", []) or []
        events = getattr(exposure_report, "events", []) or []
        events_by_id = {
            getattr(e, "event_id", ""): e for e in events
        }
        for tl in timelines:
            worst = getattr(tl, "worst_verdict", None)
            if worst is None:
                continue
            verdict_val = getattr(worst, "value", str(worst))
            if verdict_val == "UNAFFECTED":
                continue
            severity = (
                EvidenceSeverity.CRITICAL if verdict_val == "KILLED"
                else EvidenceSeverity.HIGH
            )
            first_kill = getattr(tl, "first_kill_date", None)
            affected_year = None
            if first_kill and isinstance(first_kill, str):
                try:
                    affected_year = int(first_kill.split("-")[0])
                except (ValueError, IndexError):
                    pass
            # Which specific event is the worst for this driver?
            worst_event_id = ""
            if getattr(tl, "impacts", None):
                for imp in tl.impacts:
                    if getattr(imp, "verdict", None) and \
                       getattr(imp.verdict, "value", "") == verdict_val:
                        worst_event_id = getattr(imp, "event_id", "")
                        break
            ev = events_by_id.get(worst_event_id)
            event_title = getattr(ev, "title", "named regulatory event")
            # Approximate $ impact by margin/lift share
            impact = None
            residual = getattr(tl, "residual_lift_pct", None)
            expected = getattr(tl, "expected_lift_pct", None)
            if residual is not None and expected is not None:
                # The "impact" we surface is the *loss* of claimed lift
                impact_pct = max(0.0, expected - residual)
                # Without revenue we can't dollarize; leave None and
                # let the generator fall back on the regulatory overlay.
            out.append(Evidence(
                title=(
                    f"{tl.driver_label} "
                    f"{verdict_val.lower()} by {event_title}"
                ),
                source=EvidenceSource.REGULATORY_CALENDAR,
                theme=EvidenceTheme.REGULATORY,
                severity=severity,
                affected_year=affected_year,
                narrative=(
                    f"{event_title} impairs "
                    f"{int(getattr(tl, 'cumulative_impairment_pct', 0.0) * 100)}% "
                    f"of the driver's claimed "
                    f"{getattr(tl, 'expected_lift_pct', 0.0) * 100:.1f} pp "
                    f"EBITDA lift; residual "
                    f"{getattr(tl, 'residual_lift_pct', 0.0) * 100:.1f} pp. "
                    f"First impact "
                    f"{first_kill or 'within horizon'}."
                ),
                source_link="/diligence/regulatory-calendar",
                metadata={
                    "driver_id": getattr(tl, "driver_id", ""),
                    "verdict": verdict_val,
                    "first_kill_date": first_kill,
                    "event_id": worst_event_id,
                },
            ))
        # Add an overlay-dollar evidence if overlay exists
        overlay = getattr(exposure_report, "ebitda_overlay", []) or []
        if overlay:
            total = sum(
                getattr(o, "ebitda_delta_usd", 0.0) for o in overlay
            )
            if abs(total) >= 1_000_000:
                out.append(Evidence(
                    title=(
                        f"${total/1e6:+,.1f}M cumulative regulatory "
                        f"overlay across the horizon"
                    ),
                    source=EvidenceSource.REGULATORY_CALENDAR,
                    theme=EvidenceTheme.REGULATORY,
                    severity=(
                        EvidenceSeverity.CRITICAL if abs(total) >= 20_000_000
                        else EvidenceSeverity.HIGH if abs(total) >= 5_000_000
                        else EvidenceSeverity.MEDIUM
                    ),
                    ebitda_impact_usd=total,
                    narrative=(
                        f"Year-by-year EBITDA drag from all in-horizon "
                        f"events summed to ${total/1e6:+,.1f}M. "
                        f"Subtract from Deal MC base-case cone."
                    ),
                    source_link="/diligence/regulatory-calendar",
                    metadata={"overlay_total_usd": total},
                ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_covenant_evidence(
    covenant_report: Any,
) -> List[Evidence]:
    """Pull the earliest 50%+ breach covenants + their cure sizes."""
    if covenant_report is None:
        return []
    out: List[Evidence] = []
    try:
        first_breach = getattr(covenant_report, "first_breach", []) or []
        cures = {
            getattr(c, "covenant_name", ""): c
            for c in getattr(covenant_report, "equity_cures", []) or []
        }
        for fb in first_breach:
            q50 = getattr(fb, "first_50pct_breach_quarter", None)
            q25 = getattr(fb, "first_25pct_breach_quarter", None)
            if q50 is None and q25 is None:
                continue
            if q50 is not None:
                severity = EvidenceSeverity.CRITICAL
                q = q50
            else:
                severity = EvidenceSeverity.HIGH
                q = q25
            year = q // 4 + 1
            quarter = q % 4 + 1
            name = getattr(fb, "covenant_name", "covenant")
            cure = cures.get(name)
            cure_usd: Optional[float] = None
            cure_str = "material equity cure"
            if cure is not None:
                cure_usd = getattr(cure, "median_cure_usd", None)
                p75_cure = getattr(cure, "p75_cure_usd", None)
                if cure_usd:
                    cure_str = (
                        f"${cure_usd/1e6:.1f}M median cure "
                        f"(${(p75_cure or 0)/1e6:.1f}M P75)"
                    )
            out.append(Evidence(
                title=(
                    f"{name} covenant crosses "
                    f"{'50%' if q50 is not None else '25%'} breach in "
                    f"Y{year}Q{quarter}"
                ),
                source=EvidenceSource.COVENANT_STRESS,
                theme=EvidenceTheme.CREDIT,
                severity=severity,
                affected_year=year,
                ebitda_impact_usd=cure_usd,
                narrative=(
                    f"Across simulated EBITDA paths, the {name} "
                    f"covenant first crosses "
                    f"{'50%' if q50 is not None else '25%'} breach "
                    f"probability in Y{year}Q{quarter}, requiring "
                    f"{cure_str} to stay in compliance. "
                    f"Partners should negotiate cushion, deferral, or "
                    f"equity-cure structure at term sheet."
                ),
                source_link="/diligence/covenant-stress",
                citation_key="",
                metadata={
                    "covenant_name": name,
                    "q50_breach": q50, "q25_breach": q25,
                    "median_cure_usd": cure_usd,
                },
            ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_bridge_audit_evidence(
    audit_report: Any,
) -> List[Evidence]:
    """Pull OVERSTATED + UNSUPPORTED levers from a bridge audit."""
    if audit_report is None:
        return []
    out: List[Evidence] = []
    try:
        levers = getattr(audit_report, "per_lever", []) or []
        # Focus on the worst (largest $ gap) UNSUPPORTED/OVERSTATED
        flagged = [
            a for a in levers
            if getattr(a, "verdict", None) and getattr(
                a.verdict, "value", "",
            ) in ("UNSUPPORTED", "OVERSTATED")
        ]
        flagged.sort(key=lambda a: -getattr(a, "gap_usd", 0.0))
        for a in flagged[:4]:
            verdict_val = a.verdict.value
            severity = (
                EvidenceSeverity.CRITICAL
                if verdict_val == "UNSUPPORTED" else
                EvidenceSeverity.HIGH
            )
            lever_name = getattr(a.lever, "name", "bridge lever")
            out.append(Evidence(
                title=(
                    f"'{lever_name}' is {verdict_val.lower()} "
                    f"(${getattr(a, 'gap_usd', 0.0)/1e6:.1f}M gap vs "
                    f"realization prior)"
                ),
                source=EvidenceSource.BRIDGE_AUDIT,
                theme=EvidenceTheme.OPERATIONAL,
                severity=severity,
                ebitda_impact_usd=getattr(a, "gap_usd", None),
                narrative=(
                    f"{getattr(a, 'narrative', '')}"
                ),
                source_link="/diligence/bridge-audit",
                metadata={
                    "lever_name": lever_name,
                    "category": getattr(a.category, "value", ""),
                    "verdict": verdict_val,
                    "failure_rate": getattr(a, "failure_rate", None),
                    "claimed_usd": getattr(a, "claimed_usd", None),
                    "realistic_median_usd":
                        getattr(a, "realistic_median_usd", None),
                },
            ))
        # Bridge-level gap evidence if material
        total_gap = getattr(audit_report, "gap_usd", 0.0) or 0.0
        gap_pct = getattr(audit_report, "gap_pct", 0.0) or 0.0
        if total_gap > 2_000_000 and gap_pct > 0.15:
            out.append(Evidence(
                title=(
                    f"${total_gap/1e6:.1f}M aggregate bridge gap "
                    f"({gap_pct*100:.0f}% of banker claim)"
                ),
                source=EvidenceSource.BRIDGE_AUDIT,
                theme=EvidenceTheme.OPERATIONAL,
                severity=(
                    EvidenceSeverity.CRITICAL if gap_pct > 0.30
                    else EvidenceSeverity.HIGH
                ),
                ebitda_impact_usd=total_gap,
                narrative=(
                    f"Banker's aggregate EBITDA bridge overclaims "
                    f"by ${total_gap/1e6:.1f}M versus the realization-"
                    f"prior rebuild. At entry multiple, that equates "
                    f"to a meaningful overpayment risk."
                ),
                source_link="/diligence/bridge-audit",
                metadata={
                    "bridge_gap_usd": total_gap,
                    "bridge_gap_pct": gap_pct,
                },
            ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_deal_mc_evidence(
    mc_result: Any, scenario: Any = None,
) -> List[Evidence]:
    """Pull p10 downside + P(MOIC < 1x) from Deal MC."""
    if mc_result is None:
        return []
    out: List[Evidence] = []
    try:
        p10 = getattr(mc_result, "moic_p10", None)
        p50 = getattr(mc_result, "moic_p50", None)
        prob_sub_1 = getattr(mc_result, "prob_sub_1x", None)
        irr_p10 = getattr(mc_result, "irr_p10", None)
        irr_p50 = getattr(mc_result, "irr_p50", None)
        if p10 is not None and p10 < 1.5:
            severity = (
                EvidenceSeverity.CRITICAL if p10 < 1.0
                else EvidenceSeverity.HIGH
            )
            out.append(Evidence(
                title=(
                    f"P10 MOIC is {p10:.2f}× "
                    f"(vs P50 {p50:.2f}× if shown)"
                    if p50 else f"P10 MOIC is {p10:.2f}×"
                ),
                source=EvidenceSource.DEAL_MC,
                theme=EvidenceTheme.MARKET,
                severity=severity,
                narrative=(
                    f"10th-percentile outcome across simulated paths "
                    f"returns {p10:.2f}× MOIC, "
                    f"{(irr_p10 or 0)*100:.1f}% IRR. "
                    f"A 10% tail event at this scenario means material "
                    f"capital loss — partners should size exposure and "
                    f"earn-out protections accordingly."
                ),
                source_link="/diligence/deal-mc",
                metadata={"moic_p10": p10, "irr_p10": irr_p10},
            ))
        if prob_sub_1 is not None and prob_sub_1 > 0.10:
            severity = (
                EvidenceSeverity.CRITICAL if prob_sub_1 > 0.25
                else EvidenceSeverity.HIGH if prob_sub_1 > 0.15
                else EvidenceSeverity.MEDIUM
            )
            out.append(Evidence(
                title=(
                    f"P(MOIC < 1.0×) = {prob_sub_1*100:.1f}% "
                    f"of simulated paths"
                ),
                source=EvidenceSource.DEAL_MC,
                theme=EvidenceTheme.MARKET,
                severity=severity,
                narrative=(
                    f"{prob_sub_1*100:.1f}% of Monte Carlo paths "
                    f"return less than the equity check — a "
                    f"material probability of capital loss. "
                    f"LPs expect this to be <10% at close."
                ),
                source_link="/diligence/deal-mc",
                metadata={"prob_sub_1x": prob_sub_1},
            ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_autopsy_evidence(
    autopsy_matches: Any,
) -> List[Evidence]:
    """Pull the closest historical-failure match."""
    if not autopsy_matches:
        return []
    out: List[Evidence] = []
    try:
        top = autopsy_matches[0] if autopsy_matches else None
        if top is None:
            return []
        similarity = float(getattr(top, "similarity", 0.0) or 0.0)
        deal = getattr(top, "deal", None)
        deal_name = getattr(deal, "name", "an unnamed historical deal")
        outcome = getattr(deal, "outcome", "")
        outcome_val = getattr(outcome, "value", str(outcome))
        # Skip if the match is to a SUCCESS outcome or similarity is low
        is_failure = outcome_val.upper() in (
            "BANKRUPTCY", "FIRE_SALE", "IMPAIRMENT", "FORCED_EXIT",
            "WALK_AWAY",
        )
        if not is_failure or similarity < 0.55:
            return []
        severity = (
            EvidenceSeverity.CRITICAL if similarity >= 0.80
            else EvidenceSeverity.HIGH if similarity >= 0.65
            else EvidenceSeverity.MEDIUM
        )
        out.append(Evidence(
            title=(
                f"Signature matches {deal_name} "
                f"({outcome_val.replace('_', ' ').lower()}) at "
                f"{similarity*100:.0f}% similarity"
            ),
            source=EvidenceSource.DEAL_AUTOPSY,
            theme=EvidenceTheme.PATTERN,
            severity=severity,
            narrative=(
                f"The target's characteristic signature "
                f"(payer mix × lease intensity × regulatory "
                f"exposure × physician concentration) matches "
                f"{deal_name}, a historical failure that ended in "
                f"{outcome_val.replace('_', ' ').lower()}. "
                f"Partners should review the specific failure "
                f"mechanism in the autopsy library."
            ),
            source_link="/diligence/deal-autopsy",
            metadata={
                "matched_deal": deal_name,
                "outcome": outcome_val,
                "similarity": similarity,
            },
        ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_payer_stress_evidence(
    payer_report: Any,
) -> List[Evidence]:
    """Pull Top-1 concentration risk + P10 EBITDA drag + worst-exposed
    payer from a PayerStressReport."""
    if payer_report is None:
        return []
    out: List[Evidence] = []
    try:
        verdict = getattr(payer_report, "verdict", None)
        verdict_val = (
            getattr(verdict, "value", str(verdict or "")) if verdict
            else ""
        )
        top1 = float(getattr(payer_report, "top_1_share", 0.0) or 0.0)
        p10_ebitda = float(
            getattr(
                payer_report, "p10_cumulative_ebitda_impact_usd", 0.0,
            ) or 0.0,
        )
        # High-concentration evidence
        if top1 >= 0.30:
            severity = (
                EvidenceSeverity.CRITICAL if top1 >= 0.40
                else EvidenceSeverity.HIGH
            )
            per_payer = getattr(payer_report, "per_payer", []) or []
            top_payer = per_payer[0] if per_payer else None
            top_name = (
                getattr(top_payer, "payer_name", "top payer")
                if top_payer else "top payer"
            )
            out.append(Evidence(
                title=(
                    f"Top-1 payer {top_name} holds "
                    f"{top1*100:.0f}% of NPR"
                ),
                source=EvidenceSource.PAYER_STRESS,
                theme=EvidenceTheme.OPERATIONAL,
                severity=severity,
                narrative=(
                    f"Payer concentration risk is material — a "
                    f"5% rate cut on {top_name} alone translates "
                    f"to a "
                    f"{int(top1*5)/100*100:.2f}% NPR impact. "
                    f"Diligence should include a term-sheet "
                    f"review of the dominant-payer contract."
                ),
                source_link="/diligence/payer-stress",
                metadata={
                    "top_1_share": top1,
                    "top_1_payer": top_name,
                },
            ))
        # Material downside-tail evidence
        if abs(p10_ebitda) >= 2_000_000:
            severity = (
                EvidenceSeverity.CRITICAL if abs(p10_ebitda) >= 10_000_000
                else EvidenceSeverity.HIGH if abs(p10_ebitda) >= 5_000_000
                else EvidenceSeverity.MEDIUM
            )
            out.append(Evidence(
                title=(
                    f"P10 payer-stress EBITDA drag of "
                    f"${p10_ebitda/1e6:+,.1f}M over horizon"
                ),
                source=EvidenceSource.PAYER_STRESS,
                theme=EvidenceTheme.OPERATIONAL,
                severity=severity,
                ebitda_impact_usd=p10_ebitda,
                narrative=(
                    f"Monte Carlo of per-payer rate shocks "
                    f"produces a 10th-percentile tail EBITDA "
                    f"impact of ${p10_ebitda/1e6:+,.1f}M over the "
                    f"{getattr(payer_report, 'horizon_years', 5)}-year "
                    f"hold. Factor into Deal MC base-case and "
                    f"covenant DSCR numerator."
                ),
                source_link="/diligence/payer-stress",
                metadata={
                    "p10_ebitda_usd": p10_ebitda,
                    "verdict": verdict_val,
                },
            ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_hcris_xray_evidence(
    xray_report: Any,
) -> List[Evidence]:
    """Pull out-of-band margin + deteriorating trend + below-peer
    occupancy from an HCRIS X-Ray report."""
    if xray_report is None:
        return []
    out: List[Evidence] = []
    try:
        target = getattr(xray_report, "target", None)
        if target is None:
            return []
        # Worst-underperforming margin metric (bear-case relevant)
        margin_issues = []
        for bm in getattr(xray_report, "metrics", []) or []:
            attr = getattr(bm.spec, "attr", "")
            if attr in (
                "operating_margin_on_npr",
                "net_income_margin_on_npr",
            ):
                if (
                    bm.verdict.startswith("below")
                    and bm.spec.higher_is_better
                ):
                    margin_issues.append(bm)
        for bm in margin_issues:
            severity = (
                EvidenceSeverity.CRITICAL
                if bm.target_value < 0
                else EvidenceSeverity.HIGH
                if bm.variance_vs_median_pct < -0.30
                else EvidenceSeverity.MEDIUM
            )
            out.append(Evidence(
                title=(
                    f"HCRIS: {bm.spec.label} at "
                    f"{bm.spec.fmt(bm.target_value)} vs peer "
                    f"median {bm.spec.fmt(bm.peer_median)}"
                ),
                source=EvidenceSource.HCRIS_XRAY,
                theme=EvidenceTheme.OPERATIONAL,
                severity=severity,
                narrative=(
                    f"The target's filed Medicare cost report "
                    f"shows {bm.spec.label.lower()} of "
                    f"{bm.spec.fmt(bm.target_value)}, "
                    f"{bm.variance_vs_median_pct*100:+.1f}% vs peer "
                    f"median ({bm.verdict}). This comes from "
                    f"filed data, not banker representations — "
                    f"it is the ground truth for underwriting."
                ),
                source_link="/diligence/hcris-xray",
                metadata={
                    "metric": getattr(bm.spec, "attr", ""),
                    "target_value": bm.target_value,
                    "peer_median": bm.peer_median,
                    "variance_pct":
                        bm.variance_vs_median_pct,
                },
            ))
        # Deteriorating trend flag
        trend = getattr(xray_report, "trend_signal", "")
        history = getattr(xray_report, "target_history", []) or []
        if trend == "deteriorating" and len(history) >= 2:
            first_m = history[0].operating_margin_on_npr
            last_m = history[-1].operating_margin_on_npr
            delta_pp = (last_m - first_m) * 100
            out.append(Evidence(
                title=(
                    f"Operating margin trending "
                    f"{delta_pp:+.1f} pp over "
                    f"{len(history)} years "
                    f"(FY{history[0].fiscal_year} to "
                    f"FY{history[-1].fiscal_year})"
                ),
                source=EvidenceSource.HCRIS_XRAY,
                theme=EvidenceTheme.OPERATIONAL,
                severity=(
                    EvidenceSeverity.HIGH
                    if abs(delta_pp) >= 2
                    else EvidenceSeverity.MEDIUM
                ),
                affected_year=history[-1].fiscal_year,
                narrative=(
                    f"Operating margin declined from "
                    f"{first_m*100:+.1f}% to "
                    f"{last_m*100:+.1f}% across the target's "
                    f"filed HCRIS history. Deterioration in filed "
                    f"cost reports — which post-date any banker "
                    f"spin — is a direct bear-case signal."
                ),
                source_link="/diligence/hcris-xray",
                metadata={
                    "first_year": history[0].fiscal_year,
                    "last_year": history[-1].fiscal_year,
                    "delta_pp": delta_pp,
                },
            ))
        # High Medicare concentration
        if getattr(target, "is_medicare_heavy", False):
            out.append(Evidence(
                title=(
                    f"{target.medicare_day_pct*100:.0f}% Medicare "
                    f"day share per HCRIS"
                ),
                source=EvidenceSource.HCRIS_XRAY,
                theme=EvidenceTheme.OPERATIONAL,
                severity=EvidenceSeverity.MEDIUM,
                narrative=(
                    f"HCRIS-filed payer-day mix shows "
                    f"{target.medicare_day_pct*100:.0f}% Medicare "
                    f"concentration, exposing the target to every "
                    f"CMS rate-update cycle. Factor into "
                    f"Regulatory Calendar + Deal MC base case."
                ),
                source_link="/diligence/hcris-xray",
                metadata={
                    "medicare_pct": target.medicare_day_pct,
                },
            ))
    except Exception:  # noqa: BLE001
        pass
    return out


def extract_exit_timing_evidence(
    exit_report: Any,
) -> List[Evidence]:
    """Flag when the exit-timing curve never clears a 1.5× MOIC
    hurdle — an IC-level red flag."""
    if exit_report is None:
        return []
    out: List[Evidence] = []
    try:
        rec = getattr(exit_report, "recommendation", None)
        if rec is None:
            return []
        moic = getattr(rec, "expected_moic", None)
        summary = getattr(rec, "summary", "") or ""
        # The analyzer prepends a ⚠ when below hurdle
        if ("No exit candidate" in summary
                or "below-hurdle" in summary
                or (moic is not None and moic < 1.5)):
            out.append(Evidence(
                title=(
                    f"No exit path clears 1.5× MOIC hurdle "
                    f"(peak {moic:.2f}× if available)"
                ),
                source=EvidenceSource.EXIT_TIMING,
                theme=EvidenceTheme.MARKET,
                severity=EvidenceSeverity.CRITICAL,
                narrative=(
                    f"Every (year, buyer) combination in the "
                    f"exit-timing simulation produces a MOIC below "
                    f"the 1.5× fund hurdle. The thesis requires "
                    f"material improvement (revenue uplift, debt "
                    f"restructure, entry-multiple reduction) "
                    f"before the curve clears."
                ),
                source_link="/diligence/exit-timing",
                metadata={"moic": moic, "summary": summary[:200]},
            ))
    except Exception:  # noqa: BLE001
        pass
    return out
