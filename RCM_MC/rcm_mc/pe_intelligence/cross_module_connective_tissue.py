"""Cross-module connective tissue — reason ACROSS signals.

A partner does not read reasonableness flags, then heuristics,
then bear book patterns independently. They connect them. A
specific bear pattern plus a specific red flag plus a specific
reasonableness miss tells a coherent story the raw lists do not.

This module takes a **SignalBundle** — a tagged dict of signals
from several modules — and emits **ConnectedInsights**: named
partner-voice observations that only appear when multiple signals
co-occur.

Example insights partners make mentally:

- "Envision pattern (historical) + OON dependency (red flag) +
  claimed rate growth 5% (reasonableness) — this is exactly the
  failed thesis, not a mitigated version."
- "Roll-up archetype + integration < 70% + pro-forma EBITDA
  add-backs > 15% — the earnings are fiction."
- "Peak cycle (regime) + leverage > 6.5x (cap structure) +
  covenant-lite absent (red flag) — covenant breach at -10%
  EBITDA is likely."
- "CMI uplift thesis + denial rate spike + DAR > 55 — cash flow
  is going to get WORSE before it gets better."
- "Medicare-heavy + pricing power < 40 + OBBBA exposure > 10% —
  there is no base-case defense."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SignalBundle:
    """Tagged inputs from other modules, all optional."""
    # Historical / archetype.
    historical_failure_matches: List[str] = field(default_factory=list)
    archetype: Optional[str] = None
    bear_book_hits: int = 0
    # Red flags & reasonableness.
    red_flag_high_count: int = 0
    red_flag_names: List[str] = field(default_factory=list)
    reasonableness_out_of_band: int = 0
    oon_revenue_share: float = 0.0
    # Operations.
    denial_rate: float = 0.05
    days_in_ar: int = 45
    cmi_uplift_in_thesis: bool = False
    integration_pct: float = 1.0
    pro_forma_addbacks_pct: float = 0.0
    # Market / regime.
    cycle_phase: str = "mid_expansion"
    regime: str = "balanced"
    pricing_power_score_0_100: int = 60
    # Structure.
    leverage: float = 0.0
    has_covenant_lite: bool = False
    interest_coverage: float = 3.0
    # Regulatory.
    obbba_combined_pct: float = 0.0      # from regulatory stress report
    medicare_pct: float = 0.0


@dataclass
class ConnectedInsight:
    name: str
    severity: str                         # "high" / "medium"
    signals_triggered: List[str]
    narrative: str                        # partner-voice paragraph

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "severity": self.severity,
            "signals_triggered": list(self.signals_triggered),
            "narrative": self.narrative,
        }


def _envision_confirmed(s: SignalBundle) -> Optional[ConnectedInsight]:
    if (
        "envision_surprise_billing_2023" in s.historical_failure_matches
        and s.oon_revenue_share >= 0.20
        and s.pricing_power_score_0_100 < 50
    ):
        return ConnectedInsight(
            name="envision_thesis_confirmed", severity="high",
            signals_triggered=[
                "historical:envision_surprise_billing_2023",
                f"oon_revenue_share={s.oon_revenue_share:.2f}",
                f"pricing_power_score={s.pricing_power_score_0_100}",
            ],
            narrative=(
                "This is the Envision failure, not a mitigated "
                "version of it. The historical pattern matches and "
                "the two structural reasons that pattern played out "
                "— OON dependency and weak pricing power — are both "
                "present here. A mitigated Envision-like deal would "
                "show explicit in-network wins and commercial pricing "
                "power. This shows neither. Pass."),
        )
    return None


def _rollup_earnings_fiction(
    s: SignalBundle,
) -> Optional[ConnectedInsight]:
    if (
        s.archetype == "roll_up"
        and s.integration_pct < 0.70
        and s.pro_forma_addbacks_pct > 0.15
    ):
        return ConnectedInsight(
            name="rollup_earnings_fiction", severity="high",
            signals_triggered=[
                "archetype=roll_up",
                f"integration_pct={s.integration_pct:.2f}",
                f"pro_forma_addbacks_pct={s.pro_forma_addbacks_pct:.2f}",
            ],
            narrative=(
                "A roll-up with < 70% integrated and > 15% "
                "pro-forma add-backs is showing EBITDA that will "
                "not survive audit. The exit buyer underwrites "
                "what is actually integrated, not the bridge. "
                "Haircut pro-forma to 30% of headline before IC."),
        )
    return None


def _peak_cycle_high_leverage_covenant_risk(
    s: SignalBundle,
) -> Optional[ConnectedInsight]:
    if (
        s.cycle_phase == "peak"
        and s.leverage >= 6.5
        and not s.has_covenant_lite
    ):
        return ConnectedInsight(
            name="peak_cycle_covenant_breach_likely", severity="high",
            signals_triggered=[
                f"cycle_phase={s.cycle_phase}",
                f"leverage={s.leverage:.1f}",
                "covenant_lite=False",
            ],
            narrative=(
                "Entering at peak cycle with > 6.5x leverage and "
                "covenanted debt is a covenant-breach setup. A "
                "garden-variety 10% EBITDA miss trips the coverage "
                "test. Either reduce leverage, negotiate covenant-"
                "lite terms, or plan the restructure before you "
                "close."),
        )
    return None


def _cmi_uplift_cash_squeeze(
    s: SignalBundle,
) -> Optional[ConnectedInsight]:
    if (
        s.cmi_uplift_in_thesis
        and s.denial_rate >= 0.10
        and s.days_in_ar >= 55
    ):
        return ConnectedInsight(
            name="cmi_uplift_cash_squeeze", severity="high",
            signals_triggered=[
                "cmi_uplift_in_thesis=True",
                f"denial_rate={s.denial_rate:.3f}",
                f"days_in_ar={s.days_in_ar}",
            ],
            narrative=(
                "CMI uplift + elevated denials + long DAR = cash is "
                "going to get worse before it gets better. Upcoding "
                "without clinical documentation improvement raises "
                "denials first; the DPO extension on the receivables "
                "side deepens the liquidity hole. Budget 12-18 months "
                "of negative working-capital drag."),
        )
    return None


def _medicare_heavy_no_defense(
    s: SignalBundle,
) -> Optional[ConnectedInsight]:
    if (
        s.medicare_pct >= 0.40
        and s.pricing_power_score_0_100 < 40
        and s.obbba_combined_pct >= 0.10
    ):
        return ConnectedInsight(
            name="medicare_heavy_no_defense", severity="high",
            signals_triggered=[
                f"medicare_pct={s.medicare_pct:.2f}",
                f"pricing_power_score={s.pricing_power_score_0_100}",
                f"obbba_combined_pct={s.obbba_combined_pct:.2f}",
            ],
            narrative=(
                "A Medicare-heavy deal with no pricing power and "
                "double-digit combined regulatory exposure has no "
                "base-case defense. If OBBBA or sequestration even "
                "partially realizes, there is no commercial book to "
                "cross-subsidize. Thesis is rate-policy-dependent — "
                "that is not a business, it is a bet."),
        )
    return None


def _multiple_bear_hits_with_reasonableness_miss(
    s: SignalBundle,
) -> Optional[ConnectedInsight]:
    if (
        s.bear_book_hits >= 2
        and s.reasonableness_out_of_band >= 2
    ):
        return ConnectedInsight(
            name="bear_book_plus_reasonableness_stacked",
            severity="medium",
            signals_triggered=[
                f"bear_book_hits={s.bear_book_hits}",
                f"reasonableness_out_of_band={s.reasonableness_out_of_band}",
            ],
            narrative=(
                "Two bear patterns present + two out-of-band peer "
                "cells is the stacked-risk signature. Each alone "
                "manageable; together, the base case is load-bearing "
                "on assumptions already flagged as aggressive."),
        )
    return None


DETECTORS = (
    _envision_confirmed,
    _rollup_earnings_fiction,
    _peak_cycle_high_leverage_covenant_risk,
    _cmi_uplift_cash_squeeze,
    _medicare_heavy_no_defense,
    _multiple_bear_hits_with_reasonableness_miss,
)


@dataclass
class ConnectedReport:
    insights: List[ConnectedInsight] = field(default_factory=list)
    high_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insights": [i.to_dict() for i in self.insights],
            "high_count": self.high_count,
            "partner_note": self.partner_note,
        }


def connect_signals(bundle: SignalBundle) -> ConnectedReport:
    insights = [d(bundle) for d in DETECTORS]
    insights = [i for i in insights if i is not None]
    high = sum(1 for i in insights if i.severity == "high")
    if high >= 2:
        note = ("Connective-tissue reasoning surfaces multiple "
                "compounding risk patterns — this is a pass-level "
                "set of signals in combination, even if each seems "
                "manageable in isolation.")
    elif high == 1:
        note = ("One connected-insight pattern surfaced — this is "
                "more than a generic warning; partners should walk "
                "through it explicitly in IC.")
    elif insights:
        note = ("Medium-level connective-tissue patterns present; "
                "note but continue diligence.")
    else:
        note = ("No connective-tissue risk patterns — signals do "
                "not compound.")
    return ConnectedReport(
        insights=insights,
        high_count=high,
        partner_note=note,
    )


def render_connected_markdown(r: ConnectedReport) -> str:
    lines = [
        "# Connective-tissue reasoning",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    for i in r.insights:
        lines.append(f"## {i.name} ({i.severity.upper()})")
        lines.append(f"- **Signals:** {', '.join(i.signals_triggered)}")
        lines.append("")
        lines.append(i.narrative)
        lines.append("")
    return "\n".join(lines)
