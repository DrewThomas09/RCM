"""Cross-platform RCM synergy math (Brick 60).

When a PE firm holds ≥3 RCM platforms, shared services can unlock EBITDA
beyond single-deal models:

- **Shared denials team**: consolidate appeals / IDR shops across platforms;
  pay down-market wages once, share the learning-curve across deals.
- **Shared technology**: one RCM tech stack (clearinghouse contract,
  denials analytics, automation platforms) at portfolio pricing.
- **Shared payer leverage**: rate negotiations benefit from the union of
  covered-lives across platforms — a MSA-dominant portfolio has
  out-of-network pricing power per-platform alone can't match.

This module quantifies the opportunity using a deliberately simple,
defensible model:

  synergy_ebitda = Σ(platform_baseline_cost × shared_service_pct × savings_pct)

Where:
  - ``shared_service_pct``: fraction of the platform's RCM cost base that
    routes through a shared service (default: 40%).
  - ``savings_pct``: savings rate on the shared portion (default: 15%),
    calibrated to published PE portfolio-ops benchmarks for back-office
    consolidation. Deliberately conservative — 10-20% is the realistic
    band; 30%+ claims should be greeted with skepticism.

Excluded by design (out of RCM scope or too contested):
  - Revenue synergies (cross-selling, geographic expansion).
  - Multiple re-rating (portfolio-level platform premium on exit).
  - Net-working-capital synergies.

Runs entirely on ``deal_snapshots`` already in the store — no new
configuration files. A PE operating partner gets a defensible roll-up
in one command.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from .store import PortfolioStore
from .portfolio_snapshots import latest_per_deal


# Conservative defaults — override per run. See ops-benchmark citations in
# the module docstring for why these numbers, not higher ones.
_DEFAULT_SHARED_SERVICE_PCT = 0.40
_DEFAULT_SAVINGS_PCT = 0.15

# We approximate each platform's RCM cost base as a fraction of NPSR
# (industry rule-of-thumb: 3-4% of NPSR for hospital RCM all-in). We use
# EBITDA as a secondary proxy when NPSR isn't carried on the snapshot.
_RCM_COST_AS_PCT_OF_NPSR = 0.035
# Fallback: if we only have EBITDA, assume RCM cost ~= 8% of entry EBITDA
# (implying a deal with ~12% EBITDA margin and 3.5% RCM/NPSR).
_RCM_COST_AS_PCT_OF_EBITDA = 0.08


@dataclass
class SynergyResult:
    deal_count: int
    platforms_in_scope: int           # deals with enough data to model
    platform_baseline_rcm_cost: float  # total $ RCM cost across platforms
    shared_service_pct: float
    savings_pct: float
    synergy_ebitda: float             # annual EBITDA uplift from sharing
    per_platform: List[Dict[str, Any]]  # attribution back to each deal
    warnings: List[str]


def _platform_rcm_cost(row: pd.Series) -> Optional[float]:
    """Estimate one platform's RCM cost base from snapshot fields.

    Returns None when neither NPSR nor entry EBITDA is known — the deal
    is excluded with a warning rather than zero-filled (don't fabricate
    synergy on deals we can't size).
    """
    # NPSR not on the snapshot schema — derive from entry_ebitda / assumed margin.
    # We treat entry_ebitda as the authoritative size proxy since it's what
    # B46 materialized when the deal was underwritten.
    ebitda = row.get("entry_ebitda")
    if ebitda is not None and pd.notna(ebitda) and float(ebitda) > 0:
        return float(ebitda) * _RCM_COST_AS_PCT_OF_EBITDA
    return None


def compute_synergy(
    store: PortfolioStore,
    *,
    stage_filter: Optional[List[str]] = None,
    shared_service_pct: float = _DEFAULT_SHARED_SERVICE_PCT,
    savings_pct: float = _DEFAULT_SAVINGS_PCT,
) -> SynergyResult:
    """Compute shared-services synergy across held platforms.

    Parameters
    ----------
    stage_filter
        Only deals at these stages contribute to the synergy calc.
        Defaults to ``["closed", "hold"]`` — a pipeline deal can't share
        services yet.
    shared_service_pct
        Fraction of each platform's RCM cost that routes through shared
        infrastructure. Override when the PE firm has partial consolidation.
    savings_pct
        Savings rate on the shared portion. Calibrate against observed
        portfolio-ops benchmarks; 15% is conservative, 25% is aggressive.

    Returns
    -------
    SynergyResult with portfolio-level synergy + per-platform attribution.
    """
    if not (0.0 <= shared_service_pct <= 1.0):
        raise ValueError("shared_service_pct must be in [0, 1]")
    if not (0.0 <= savings_pct <= 1.0):
        raise ValueError("savings_pct must be in [0, 1]")

    stages = stage_filter or ["closed", "hold"]
    df = latest_per_deal(store)

    warnings: List[str] = []
    if df.empty:
        return SynergyResult(
            deal_count=0, platforms_in_scope=0,
            platform_baseline_rcm_cost=0.0,
            shared_service_pct=shared_service_pct,
            savings_pct=savings_pct,
            synergy_ebitda=0.0, per_platform=[],
            warnings=["Portfolio is empty"],
        )

    in_scope = df[df["stage"].isin(stages)]
    excluded = df[~df["stage"].isin(stages)]
    if not excluded.empty:
        warnings.append(
            f"Excluded {len(excluded)} deal(s) not at {stages} stages"
        )

    per_platform: List[Dict[str, Any]] = []
    total_baseline = 0.0
    total_synergy = 0.0
    platforms_in_scope = 0

    for _, row in in_scope.iterrows():
        cost = _platform_rcm_cost(row)
        if cost is None:
            warnings.append(
                f"Deal {row['deal_id']!r} excluded: no entry_ebitda to size RCM cost"
            )
            continue
        platforms_in_scope += 1
        shared_cost = cost * shared_service_pct
        savings = shared_cost * savings_pct
        total_baseline += cost
        total_synergy += savings
        per_platform.append({
            "deal_id": str(row["deal_id"]),
            "stage": str(row["stage"]),
            "entry_ebitda": float(row["entry_ebitda"]) if pd.notna(row.get("entry_ebitda")) else None,
            "rcm_cost_base": cost,
            "shared_cost": shared_cost,
            "synergy_contribution": savings,
        })

    if platforms_in_scope < 3:
        warnings.append(
            f"Only {platforms_in_scope} platform(s) in scope — "
            "shared-services economics typically require 3+ platforms"
        )

    return SynergyResult(
        deal_count=int(len(df)),
        platforms_in_scope=platforms_in_scope,
        platform_baseline_rcm_cost=total_baseline,
        shared_service_pct=shared_service_pct,
        savings_pct=savings_pct,
        synergy_ebitda=total_synergy,
        per_platform=per_platform,
        warnings=warnings,
    )


def _fmt_money(v: float) -> str:
    if v is None:
        return "—"
    sign = "-" if v < 0 else ""
    af = abs(v)
    if af >= 1e9:
        return f"{sign}${af/1e9:.2f}B"
    if af >= 1e6:
        return f"{sign}${af/1e6:.1f}M"
    return f"{sign}${af:,.0f}"


def format_synergy(result: SynergyResult) -> str:
    """Terminal-friendly synergy summary."""
    lines = [
        f"Cross-platform RCM synergy — {result.platforms_in_scope} platform(s) in scope",
        "─" * 64,
        f"  Portfolio deal count:         {result.deal_count}",
        f"  Platforms contributing:       {result.platforms_in_scope}",
        f"  Total RCM cost base:          {_fmt_money(result.platform_baseline_rcm_cost)}",
        f"  Shared-service %:             {result.shared_service_pct*100:.0f}%",
        f"  Savings rate on shared:       {result.savings_pct*100:.0f}%",
        f"  Annual synergy EBITDA:        {_fmt_money(result.synergy_ebitda)}",
    ]
    if result.per_platform:
        lines.append("")
        lines.append("  Per-platform attribution:")
        lines.append(
            f"    {'Deal':<20s}  {'Stage':<8s}  {'RCM cost':>10s}  "
            f"{'Synergy':>10s}"
        )
        for p in sorted(result.per_platform, key=lambda x: -x["synergy_contribution"]):
            lines.append(
                f"    {p['deal_id']:<20s}  {p['stage']:<8s}  "
                f"{_fmt_money(p['rcm_cost_base']):>10s}  "
                f"{_fmt_money(p['synergy_contribution']):>10s}"
            )
    if result.warnings:
        lines.append("")
        lines.append("  Notes:")
        for w in result.warnings:
            lines.append(f"    · {w}")
    return "\n".join(lines)


def synergy_to_dict(result: SynergyResult) -> Dict[str, Any]:
    """JSON-friendly payload (for the portfolio CLI --json path)."""
    return {
        "deal_count": result.deal_count,
        "platforms_in_scope": result.platforms_in_scope,
        "platform_baseline_rcm_cost": result.platform_baseline_rcm_cost,
        "shared_service_pct": result.shared_service_pct,
        "savings_pct": result.savings_pct,
        "synergy_ebitda": result.synergy_ebitda,
        "per_platform": result.per_platform,
        "warnings": result.warnings,
    }
