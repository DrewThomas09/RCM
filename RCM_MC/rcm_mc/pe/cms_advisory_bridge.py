"""CMS advisory → packet bridge.

Converts :mod:`rcm_mc.pe.cms_advisory` outputs into ``RiskFlag``
instances for the packet's risk_flags list + one summary metric for
the observed_metrics dict. Lives separately from the scoring math so
the advisory module stays a pure data library (testable in isolation)
and the bridge is the single place the packet's surface knows about
advisory findings.

Flags generated (up to 4 per deal):

1. **Market posture** — from consensus_rank of the target's
   provider_type. Top quartile = LOW, bottom quartile = HIGH.
2. **Operating regime** — ``declining_risk`` or ``stagnant`` →
   MEDIUM/HIGH; ``durable_growth`` → LOW.
3. **Volatility** — yoy_payment_volatility ≥ 0.35 → MEDIUM.
4. **Stress exposure** — any DEFAULT_STRESS_SCENARIOS delta worse
   than −20% → MEDIUM.

Every flag carries ``trigger_metrics`` that name the advisory table
+ row key, so the provenance UI can drill into the underlying
scoring math.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from ..analysis.packet import RiskFlag, RiskSeverity


@dataclass
class CMSAdvisoryFindings:
    """Bundled advisory output scoped to a single provider_type for
    packet consumption. Constructed by :func:`findings_for_provider`."""
    provider_type: str
    consensus_score: Optional[float] = None
    consensus_rank: Optional[int] = None
    total_provider_types: int = 0
    regime: Optional[str] = None
    regime_rank_score: Optional[float] = None
    yoy_payment_volatility: Optional[float] = None
    worst_stress_scenario: Optional[str] = None
    worst_stress_delta_pct: Optional[float] = None


def findings_for_provider(
    provider_type: str,
    *,
    consensus: Optional[pd.DataFrame] = None,
    regimes: Optional[pd.DataFrame] = None,
    volatility: Optional[pd.DataFrame] = None,
    stress: Optional[pd.DataFrame] = None,
) -> CMSAdvisoryFindings:
    """Pull one provider_type's row from each advisory DataFrame.

    Missing frames are tolerated — partners without sufficient data
    for, say, regime classification get the other three signals
    without a crash. An entirely-empty call returns a findings
    object with every field None (no flags emitted downstream)."""
    f = CMSAdvisoryFindings(provider_type=provider_type)

    if consensus is not None and not consensus.empty:
        f.total_provider_types = int(len(consensus))
        row = _row_for(consensus, provider_type)
        if row is not None:
            if "consensus_score" in row:
                f.consensus_score = float(row["consensus_score"])
            if "consensus_rank" in row:
                f.consensus_rank = int(row["consensus_rank"])

    if regimes is not None and not regimes.empty:
        row = _row_for(regimes, provider_type)
        if row is not None:
            f.regime = str(row["regime"]) if "regime" in row else None
            if "regime_rank_score" in row:
                f.regime_rank_score = float(row["regime_rank_score"])

    if volatility is not None and not volatility.empty:
        row = _row_for(volatility, provider_type)
        if row is not None and "yoy_payment_volatility" in row \
                and pd.notna(row["yoy_payment_volatility"]):
            f.yoy_payment_volatility = float(row["yoy_payment_volatility"])

    if stress is not None and not stress.empty:
        sub = stress[stress["provider_type"] == provider_type]
        if not sub.empty and "delta_pct" in sub.columns:
            worst = sub.loc[sub["delta_pct"].idxmin()]
            f.worst_stress_scenario = str(worst["scenario"])
            f.worst_stress_delta_pct = float(worst["delta_pct"])
    return f


def _row_for(df: pd.DataFrame, provider_type: str) -> Optional[pd.Series]:
    if "provider_type" not in df.columns:
        # screen_providers returns with provider_type as the index.
        if df.index.name == "provider_type":
            if provider_type in df.index:
                return df.loc[provider_type]
        return None
    match = df[df["provider_type"] == provider_type]
    if match.empty:
        return None
    return match.iloc[0]


# ── Flag construction ──────────────────────────────────────────────

def findings_to_risk_flags(
    findings: CMSAdvisoryFindings,
) -> List[RiskFlag]:
    """Produce RiskFlag rows suitable for appending to
    ``DealAnalysisPacket.risk_flags``. Returns empty list when no
    signals are strong enough to flag."""
    flags: List[RiskFlag] = []

    # 1. Market posture (consensus rank)
    if findings.consensus_rank and findings.total_provider_types:
        rank_pct = findings.consensus_rank / findings.total_provider_types
        if rank_pct <= 0.25:
            flags.append(RiskFlag(
                category="market_posture",
                severity=RiskSeverity.LOW,
                title=f"Attractive market posture for {findings.provider_type}",
                detail=(
                    f"CMS advisory consensus rank {findings.consensus_rank} of "
                    f"{findings.total_provider_types} ({rank_pct*100:.0f}th percentile). "
                    f"Top-quartile scale + margin + acuity + fragmentation composite."
                ),
                trigger_metrics=["cms_advisory.consensus_rank"],
            ))
        elif rank_pct >= 0.75:
            flags.append(RiskFlag(
                category="market_posture",
                severity=RiskSeverity.HIGH,
                title=f"Bottom-quartile market posture for {findings.provider_type}",
                detail=(
                    f"CMS advisory consensus rank {findings.consensus_rank} of "
                    f"{findings.total_provider_types}. "
                    f"Review underwriting assumptions for scale / margin / "
                    f"fragmentation — advisory composite lands in the bottom quartile."
                ),
                trigger_metrics=["cms_advisory.consensus_rank"],
            ))

    # 2. Operating regime
    if findings.regime:
        severity = {
            "durable_growth": RiskSeverity.LOW,
            "steady_compounders": RiskSeverity.LOW,
            "emerging_volatile": RiskSeverity.MEDIUM,
            "stagnant": RiskSeverity.MEDIUM,
            "declining_risk": RiskSeverity.HIGH,
        }.get(findings.regime, RiskSeverity.MEDIUM)
        if severity != RiskSeverity.LOW:
            flags.append(RiskFlag(
                category="operating_regime",
                severity=severity,
                title=f"Regime: {findings.regime}",
                detail=(
                    f"{findings.provider_type} classified as '{findings.regime}' "
                    f"(regime_rank_score={findings.regime_rank_score:.3f} "
                    f"from CMS advisory momentum × volatility)."
                    if findings.regime_rank_score is not None else
                    f"{findings.provider_type} classified as '{findings.regime}' "
                    f"from CMS advisory momentum × volatility."
                ),
                trigger_metrics=["cms_advisory.regime"],
            ))

    # 3. Volatility
    if findings.yoy_payment_volatility is not None \
            and findings.yoy_payment_volatility >= 0.35:
        flags.append(RiskFlag(
            category="earnings_durability",
            severity=RiskSeverity.MEDIUM,
            title=f"High YoY payment volatility ({findings.yoy_payment_volatility:.1%})",
            detail=(
                f"{findings.provider_type} YoY Medicare payment standard "
                f"deviation is {findings.yoy_payment_volatility:.1%}, above the "
                f"35% durability threshold. Earnings forecast should carry a "
                f"wider band at the next IC."
            ),
            trigger_metrics=["cms_advisory.yoy_payment_volatility"],
        ))

    # 4. Stress exposure
    if findings.worst_stress_delta_pct is not None \
            and findings.worst_stress_delta_pct <= -0.20:
        flags.append(RiskFlag(
            category="stress_exposure",
            severity=RiskSeverity.MEDIUM,
            title=f"Severe stress exposure to {findings.worst_stress_scenario}",
            detail=(
                f"Under scenario '{findings.worst_stress_scenario}', "
                f"{findings.provider_type} payment-per-beneficiary drops "
                f"{findings.worst_stress_delta_pct*100:.1f}%. Review "
                f"covenant headroom and the v2 bridge Monte Carlo tail."
            ),
            trigger_metrics=["cms_advisory.worst_stress_delta_pct"],
            ebitda_at_risk=None,    # bridge computes the $ impact
        ))

    return flags
