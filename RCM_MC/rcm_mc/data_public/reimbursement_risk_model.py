"""Reimbursement risk model — quantifies EBITDA exposure to CMS rate changes.

Answers the IC question: "How much EBITDA do we lose if CMS cuts
[sector] rates by X%?" Integrates payer mix, historical CMS rate
trend volatility, and deal-level EBITDA to produce dollar-denominated
downside scenarios.

Grounded in historical CMS rate events:
  - Home health: PDGM reform 2020 (-1.5% to -3% net of behavior change)
  - Dialysis: ESRD bundled payment 2011 (-4.1% year one)
  - SNF: RUG to PDPM 2019 (+2.4% on average, but -15% for outliers)
  - Physician: SGR freeze / MACRA transition (0-2% annual headwinds)
  - Hospital inpatient: market basket - productivity adjustment (~1.5-2.0% net)
  - Hospice: annual market basket update (+2-3%, most stable)
  - Behavioral health: Medicaid managed care penetration variability

Public API:
    ReimbursementScenario                              dataclass
    RateShockAssumptions                               dataclass
    model_reimbursement_risk(deal, scenarios)          -> Dict[str, ReimbursementScenario]
    sector_rate_history(sector)                        -> List[Dict]
    build_scenarios(deal, custom_shocks)               -> Dict[str, RateShockAssumptions]
    reimbursement_risk_table(scenarios)                -> str
    reimbursement_risk_report(deal, scenarios)         -> str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Historical CMS rate volatility by sector (used to calibrate shock sizes)
# Derived from CMS final rules 2010-2023
# ---------------------------------------------------------------------------

_SECTOR_RATE_HISTORY: Dict[str, List[Dict[str, Any]]] = {
    "home_health": [
        {"year": 2011, "change_pct": -0.011, "event": "PPACA market basket update"},
        {"year": 2014, "change_pct": -0.035, "event": "Home health rebasing (-$80/episode)"},
        {"year": 2015, "change_pct": -0.032, "event": "Rebasing year 2"},
        {"year": 2016, "change_pct": -0.018, "event": "Rebasing year 3"},
        {"year": 2017, "change_pct": -0.011, "event": "Rebasing + market basket"},
        {"year": 2020, "change_pct": -0.015, "event": "PDGM implementation (net of behavior)"},
        {"year": 2023, "change_pct": -0.018, "event": "CY23 final rule temporary adjustment"},
    ],
    "dialysis": [
        {"year": 2011, "change_pct": -0.041, "event": "ESRD bundled payment launch"},
        {"year": 2012, "change_pct": 0.022, "event": "ESRD QIP + market basket"},
        {"year": 2017, "change_pct": -0.003, "event": "ESRD payment rebasing"},
        {"year": 2019, "change_pct": -0.012, "event": "ESRD QIP penalties + market basket"},
    ],
    "snf": [
        {"year": 2011, "change_pct": 0.021, "event": "SNF market basket update"},
        {"year": 2012, "change_pct": -0.021, "event": "SNF prospective payment adjustment"},
        {"year": 2019, "change_pct": 0.024, "event": "PDPM implementation avg (outlier -15%)"},
        {"year": 2022, "change_pct": 0.056, "event": "SNF market basket + COVID lump sum"},
    ],
    "physician_group": [
        {"year": 2012, "change_pct": -0.045, "event": "SGR cut averted but fear premium"},
        {"year": 2016, "change_pct": 0.005, "event": "MACRA QPP transition"},
        {"year": 2021, "change_pct": -0.032, "event": "E&M code revaluation net effect on specialists"},
        {"year": 2022, "change_pct": -0.040, "event": "Physician fee schedule conversion factor cut"},
        {"year": 2023, "change_pct": -0.025, "event": "CF cut + MIPS QPP adjustments"},
    ],
    "hospital": [
        {"year": 2011, "change_pct": 0.015, "event": "IPPS market basket update"},
        {"year": 2014, "change_pct": -0.009, "event": "VBP + HACRP penalties"},
        {"year": 2016, "change_pct": 0.009, "event": "IPPS net (MBU minus productivity)"},
        {"year": 2020, "change_pct": 0.032, "event": "FY20 IPPS + ACA indirect GME"},
    ],
    "hospice": [
        {"year": 2012, "change_pct": 0.030, "event": "Hospice wage index update"},
        {"year": 2016, "change_pct": 0.023, "event": "Hospice market basket"},
        {"year": 2020, "change_pct": 0.026, "event": "FY20 hospice update"},
        {"year": 2022, "change_pct": 0.033, "event": "FY22 hospice + aggregate cap"},
    ],
    "behavioral_health": [
        {"year": 2014, "change_pct": 0.050, "event": "ACA Medicaid expansion (BH volume surge)"},
        {"year": 2017, "change_pct": -0.020, "event": "IMD exclusion partial waiver debate"},
        {"year": 2020, "change_pct": 0.080, "event": "COVID BH demand surge + telehealth parity"},
        {"year": 2023, "change_pct": -0.015, "event": "Medicaid redeterminations (unwinding) volume loss"},
    ],
    "managed_care": [
        {"year": 2013, "change_pct": -0.020, "event": "MA benchmark cut (ACA sequester)"},
        {"year": 2015, "change_pct": 0.017, "event": "MA Star ratings bonus + benchmark"},
        {"year": 2020, "change_pct": 0.025, "event": "MA benchmark + risk model favorable"},
        {"year": 2023, "change_pct": -0.018, "event": "MA risk model v28 transition impact"},
    ],
    "asc": [
        {"year": 2012, "change_pct": 0.018, "event": "ASC market basket update"},
        {"year": 2017, "change_pct": 0.014, "event": "ASC market basket - productivity"},
        {"year": 2021, "change_pct": 0.020, "event": "ASC CY21 update"},
        {"year": 2023, "change_pct": 0.025, "event": "ASC market basket + dental addition"},
    ],
}

# Sector volatility estimates (std dev of annual rate changes) from history
_SECTOR_VOLATILITY: Dict[str, float] = {
    "home_health": 0.020,
    "dialysis": 0.024,
    "snf": 0.030,
    "physician_group": 0.025,
    "hospital": 0.012,
    "hospice": 0.005,
    "behavioral_health": 0.035,
    "managed_care": 0.020,
    "asc": 0.007,
    "physical_therapy": 0.020,
    "dme_home_health": 0.028,
    "dental": 0.008,
    "lab": 0.015,
    "health_it": 0.005,
    "rcm": 0.005,
}

_DEFAULT_VOLATILITY = 0.020


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RateShockAssumptions:
    """Definition of a single reimbursement scenario."""
    name: str
    medicare_rate_change: float    # % change to Medicare rates (e.g. -0.10 = -10%)
    medicaid_rate_change: float
    commercial_rate_change: float
    description: str


@dataclass
class ReimbursementScenario:
    """Result of applying a rate shock to a deal."""
    scenario_name: str
    deal_source_id: Optional[str]
    deal_name: Optional[str]
    ebitda_entry_mm: Optional[float]
    govt_exposure: float           # Medicare + Medicaid as fraction
    medicare_pct: float
    medicaid_pct: float
    commercial_pct: float
    medicare_ebitda_impact_mm: Optional[float]
    medicaid_ebitda_impact_mm: Optional[float]
    commercial_ebitda_impact_mm: Optional[float]
    total_ebitda_impact_mm: Optional[float]
    stressed_ebitda_mm: Optional[float]
    ebitda_impact_pct: Optional[float]    # Impact as % of entry EBITDA
    moic_haircut: Optional[float]         # Approximate MOIC reduction (rough)
    severity: str = "moderate"            # low / moderate / high / severe


# ---------------------------------------------------------------------------
# Standard scenario library — calibrated to historical CMS events
# ---------------------------------------------------------------------------

_STANDARD_SCENARIOS: Dict[str, RateShockAssumptions] = {
    "base_case": RateShockAssumptions(
        name="base_case",
        medicare_rate_change=0.02,
        medicaid_rate_change=0.01,
        commercial_rate_change=0.03,
        description="Normal market basket updates (~2% Medicare, ~1% Medicaid, ~3% commercial inflation)",
    ),
    "mild_cut": RateShockAssumptions(
        name="mild_cut",
        medicare_rate_change=-0.02,
        medicaid_rate_change=-0.01,
        commercial_rate_change=0.02,
        description="Mild CMS regulatory headwind — market basket minus productivity offset",
    ),
    "moderate_cut": RateShockAssumptions(
        name="moderate_cut",
        medicare_rate_change=-0.05,
        medicaid_rate_change=-0.03,
        commercial_rate_change=0.01,
        description="Moderate reform (PDGM-style, one-time rebasing); historical 50th-pctile downside",
    ),
    "severe_cut": RateShockAssumptions(
        name="severe_cut",
        medicare_rate_change=-0.10,
        medicaid_rate_change=-0.06,
        commercial_rate_change=-0.02,
        description="Severe legislative cut (SGR-style, NSA surprise-billing impact); historical 95th-pctile",
    ),
    "structural_shift": RateShockAssumptions(
        name="structural_shift",
        medicare_rate_change=-0.15,
        medicaid_rate_change=-0.10,
        commercial_rate_change=-0.05,
        description="Structural policy reversal — site-neutral payment, global budget, value-based migration",
    ),
    "covid_disruption": RateShockAssumptions(
        name="covid_disruption",
        medicare_rate_change=-0.08,
        medicaid_rate_change=0.05,
        commercial_rate_change=-0.12,
        description="COVID-like volume disruption — Medicare stable, Medicaid expanded, commercial volume collapse",
    ),
}


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def build_scenarios(
    deal: Dict[str, Any],
    custom_shocks: Optional[Dict[str, RateShockAssumptions]] = None,
) -> Dict[str, RateShockAssumptions]:
    """Return the scenario set to apply, merging standard + custom shocks."""
    scenarios = dict(_STANDARD_SCENARIOS)
    if custom_shocks:
        scenarios.update(custom_shocks)
    return scenarios


def _extract_payer_mix(deal: Dict[str, Any]) -> Dict[str, float]:
    """Return payer mix fractions from deal dict."""
    import json

    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = {}
    if not isinstance(pm, dict):
        pm = {}

    medicare = float(pm.get("medicare", 0) or 0)
    medicaid = float(pm.get("medicaid", 0) or 0)
    commercial = float(pm.get("commercial", 0) or 0)
    self_pay = float(pm.get("self_pay", 0) or 0)

    # Normalize if sum is off
    total = medicare + medicaid + commercial + self_pay
    if total > 0 and abs(total - 1.0) > 0.05:
        medicare /= total
        medicaid /= total
        commercial /= total

    return {"medicare": medicare, "medicaid": medicaid, "commercial": commercial}


def _moic_haircut_from_ebitda_impact(
    ebitda_impact_pct: float,
    hold_years: float = 5.0,
    ev_ebitda: float = 12.0,
    leverage_pct: float = 0.55,
) -> float:
    """Rough MOIC haircut from EBITDA compression.

    Assumes exit multiple contracts proportionally with EBITDA decline,
    and entry equity at (1-leverage) * ev.
    """
    if ev_ebitda <= 0:
        return 0.0
    # Exit EV drops by ebitda_impact_pct × ev_ebitda multiple
    exit_ev_decline_multiple = -ebitda_impact_pct  # in multiples of entry EBITDA
    # Entry equity fraction of EV
    equity_fraction = 1 - leverage_pct
    # MOIC haircut ≈ exit_ev_decline / entry_equity_as_fraction_of_ev / 1.0 (normalized to 1.0x equity)
    # Exit EV haircut as % of entry EV: -ebitda_impact_pct (since exit EBITDA falls same way)
    moic_haircut = -ebitda_impact_pct * ev_ebitda / (ev_ebitda * equity_fraction)
    return round(moic_haircut, 3)


def model_reimbursement_risk(
    deal: Dict[str, Any],
    scenarios: Optional[Dict[str, RateShockAssumptions]] = None,
) -> Dict[str, ReimbursementScenario]:
    """Apply rate shock scenarios to a deal's EBITDA.

    Args:
        deal:      Deal dict with ebitda_mm (or ebitda_at_entry_mm), payer_mix
        scenarios: Dict of scenario name -> RateShockAssumptions (defaults to standard set)

    Returns:
        Dict of scenario name -> ReimbursementScenario
    """
    if scenarios is None:
        scenarios = _STANDARD_SCENARIOS

    ebitda = deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm")
    if ebitda is not None:
        ebitda = float(ebitda)

    ev_ebitda = float(deal.get("ev_ebitda") or 12.0)
    hold_years = float(deal.get("hold_years") or 5.0)
    leverage_pct = 0.55

    pm = _extract_payer_mix(deal)
    medicare = pm["medicare"]
    medicaid = pm["medicaid"]
    commercial = pm["commercial"]
    govt_exposure = medicare + medicaid

    results: Dict[str, ReimbursementScenario] = {}

    for name, shock in scenarios.items():
        if ebitda is not None:
            mcr_impact = ebitda * medicare * shock.medicare_rate_change
            mcd_impact = ebitda * medicaid * shock.medicaid_rate_change
            com_impact = ebitda * commercial * shock.commercial_rate_change
            total_impact = mcr_impact + mcd_impact + com_impact
            stressed = ebitda + total_impact
            impact_pct = total_impact / ebitda if ebitda != 0 else 0.0
            haircut = _moic_haircut_from_ebitda_impact(impact_pct, hold_years, ev_ebitda, leverage_pct)
        else:
            mcr_impact = mcd_impact = com_impact = total_impact = None
            stressed = None
            impact_pct = None
            haircut = None

        # Severity classification
        if impact_pct is None:
            severity = "unknown"
        elif impact_pct >= -0.02:
            severity = "low"
        elif impact_pct >= -0.05:
            severity = "moderate"
        elif impact_pct >= -0.10:
            severity = "high"
        else:
            severity = "severe"

        results[name] = ReimbursementScenario(
            scenario_name=name,
            deal_source_id=deal.get("source_id"),
            deal_name=deal.get("deal_name"),
            ebitda_entry_mm=ebitda,
            govt_exposure=round(govt_exposure, 3),
            medicare_pct=round(medicare, 3),
            medicaid_pct=round(medicaid, 3),
            commercial_pct=round(commercial, 3),
            medicare_ebitda_impact_mm=round(mcr_impact, 2) if mcr_impact is not None else None,
            medicaid_ebitda_impact_mm=round(mcd_impact, 2) if mcd_impact is not None else None,
            commercial_ebitda_impact_mm=round(com_impact, 2) if com_impact is not None else None,
            total_ebitda_impact_mm=round(total_impact, 2) if total_impact is not None else None,
            stressed_ebitda_mm=round(stressed, 2) if stressed is not None else None,
            ebitda_impact_pct=round(impact_pct, 4) if impact_pct is not None else None,
            moic_haircut=round(haircut, 3) if haircut is not None else None,
            severity=severity,
        )

    return results


def sector_rate_history(sector: str) -> List[Dict[str, Any]]:
    """Return historical CMS rate change events for a sector."""
    # Normalize
    key = sector.lower().replace(" ", "_").replace("-", "_")
    # Check direct match
    if key in _SECTOR_RATE_HISTORY:
        return _SECTOR_RATE_HISTORY[key]
    # Fuzzy match
    for k in _SECTOR_RATE_HISTORY:
        if k in key or key in k:
            return _SECTOR_RATE_HISTORY[k]
    return []


def sector_volatility(sector: str) -> float:
    """Return estimated annual rate change std dev for a sector."""
    key = sector.lower().replace(" ", "_")
    return _SECTOR_VOLATILITY.get(key, _DEFAULT_VOLATILITY)


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def reimbursement_risk_table(scenarios: Dict[str, ReimbursementScenario]) -> str:
    """Formatted scenario table for IC memo."""
    lines = [
        f"{'Scenario':<22} {'MCR Δ':>8} {'MCD Δ':>8} {'Total Δ $M':>12} {'Stressed EBITDA':>16} {'Impact%':>8} {'Severity':>9}",
        "-" * 90,
    ]
    order = ["base_case", "mild_cut", "moderate_cut", "severe_cut", "structural_shift", "covid_disruption"]
    seen = set()
    for name in order + [k for k in scenarios if k not in order]:
        if name not in scenarios or name in seen:
            continue
        seen.add(name)
        s = scenarios[name]
        mcr = f"${s.medicare_ebitda_impact_mm:+.1f}M" if s.medicare_ebitda_impact_mm is not None else "  —  "
        mcd = f"${s.medicaid_ebitda_impact_mm:+.1f}M" if s.medicaid_ebitda_impact_mm is not None else "  —  "
        total = f"${s.total_ebitda_impact_mm:+.1f}M" if s.total_ebitda_impact_mm is not None else "  —  "
        stressed = f"${s.stressed_ebitda_mm:.1f}M" if s.stressed_ebitda_mm is not None else "  —  "
        pct = f"{s.ebitda_impact_pct:.1%}" if s.ebitda_impact_pct is not None else "  —  "
        lines.append(
            f"{name[:21]:<22} {mcr:>8} {mcd:>8} {total:>12} {stressed:>16} {pct:>8} {s.severity:>9}"
        )
    return "\n".join(lines) + "\n"


def reimbursement_risk_report(
    deal: Dict[str, Any],
    scenarios: Dict[str, ReimbursementScenario],
) -> str:
    """Narrative reimbursement risk section for IC memo."""
    ebitda = deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm")
    pm = _extract_payer_mix(deal)
    sector = deal.get("sector", "unknown")
    history = sector_rate_history(sector)
    vol = sector_volatility(sector)

    lines = [
        f"Reimbursement Risk Assessment — {deal.get('deal_name', 'Unknown Deal')}",
        "=" * 65,
        f"  Sector:             {sector}",
        f"  Entry EBITDA:       ${ebitda:,.1f}M" if ebitda else "  Entry EBITDA:       Unknown",
        f"  Govt exposure:      {(pm['medicare']+pm['medicaid']):.0%} "
        f"(Medicare {pm['medicare']:.0%} / Medicaid {pm['medicaid']:.0%})",
        f"  Sector rate vol:    ±{vol:.1%} annually (historical std dev)",
        "",
        "  Historical rate context:",
    ]
    for h in history[-3:]:  # last 3 events
        lines.append(f"    {h['year']}: {h['change_pct']:+.1%}  ({h['event']})")

    lines += ["", "  Scenario EBITDA impacts:"]
    for name in ["mild_cut", "moderate_cut", "severe_cut"]:
        if name in scenarios:
            s = scenarios[name]
            if s.total_ebitda_impact_mm is not None:
                lines.append(
                    f"    {name}: ${s.total_ebitda_impact_mm:+.1f}M EBITDA "
                    f"({s.ebitda_impact_pct:.1%}) → "
                    f"${s.stressed_ebitda_mm:.1f}M stressed [{s.severity}]"
                )

    severe = scenarios.get("severe_cut")
    if severe and severe.moic_haircut is not None:
        lines += [
            "",
            f"  Severe-cut MOIC haircut: ~{severe.moic_haircut:.2f}x (rough estimate)",
        ]

    return "\n".join(lines) + "\n"
