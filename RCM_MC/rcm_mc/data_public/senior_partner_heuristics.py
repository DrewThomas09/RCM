"""Senior-partner heuristics for healthcare PE deal assessment.

Encodes pattern-recognition logic that an experienced healthcare PE partner
would apply when reviewing a new deal.  These are NOT hard rules — they are
calibrated signals that should be weighed alongside financial modeling.

Covers:
  - Entry multiple reasonableness bands by deal type + sub-sector
  - Hold-period expectations
  - Specific healthcare traps (concentration, regulatory, staffing, coding)
  - Return plausibility checks
  - Sponsor track record signals

Public API:
    EntryMultipleBand                     dataclass
    get_entry_band(deal_type, sector)     -> EntryMultipleBand
    multiple_flag(deal)                   -> list[str]  (warning flags)
    hold_period_flag(deal)                -> list[str]
    healthcare_trap_scan(deal)            -> list[dict] (trap, severity, detail)
    return_plausibility_check(deal)       -> dict
    full_heuristic_assessment(deal)       -> dict
    heuristic_report(assessment)          -> str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Entry multiple bands
# ---------------------------------------------------------------------------

@dataclass
class EntryMultipleBand:
    """Expected EV/EBITDA range for a deal type and sector."""
    sector: str
    deal_type: str
    low: float          # below this → cheap, check quality
    fair_low: float
    fair_high: float
    high: float         # above this → premium, stress-test IRR
    notes: str = ""


# Bands calibrated to 2019-2024 transaction data
_BANDS: Dict[str, Dict[str, EntryMultipleBand]] = {
    "lbo": {
        "acute_hospital": EntryMultipleBand(
            "acute_hospital", "lbo", 6.0, 7.5, 10.5, 13.0,
            "Hospital LBOs typically 7-10x; above 12x requires strong MA thesis"
        ),
        "behavioral_health": EntryMultipleBand(
            "behavioral_health", "lbo", 7.0, 9.0, 13.0, 16.0,
            "BH multiples expanded post-parity enforcement; above 14x needs de-novo proof"
        ),
        "home_health": EntryMultipleBand(
            "home_health", "lbo", 8.0, 10.0, 14.0, 17.0,
            "Home health trades at premium; PDGM reform added rate risk"
        ),
        "asc_surgical": EntryMultipleBand(
            "asc_surgical", "lbo", 7.0, 9.0, 13.0, 15.0,
            "ASC multiples vary with commercial payer mix; below 20% commercial = red flag"
        ),
        "rcm_health_it": EntryMultipleBand(
            "rcm_health_it", "lbo", 10.0, 12.0, 18.0, 25.0,
            "RCM/HIT trades on ARR multiples; NTM revenue 3-5x for SaaS-like"
        ),
        "physician_staffing": EntryMultipleBand(
            "physician_staffing", "lbo", 7.0, 8.5, 12.0, 14.0,
            "Staffing multiples depressed post-NSA; above 12x needs contract visibility"
        ),
        "hospice_palliative": EntryMultipleBand(
            "hospice_palliative", "lbo", 9.0, 11.0, 15.0, 18.0,
            "Hospice trades at significant premium; cap utilization >90% = value risk"
        ),
        "dso_dental_eye": EntryMultipleBand(
            "dso_dental_eye", "lbo", 7.0, 9.0, 13.0, 16.0,
            "DSO multiples depend on de-novo pipeline; above 14x needs M&A proof point"
        ),
        "value_based_care": EntryMultipleBand(
            "value_based_care", "lbo", 8.0, 10.0, 16.0, 22.0,
            "VBC on revenue multiples; EBITDA rarely positive; check MLR trend"
        ),
        "other": EntryMultipleBand(
            "other", "lbo", 6.0, 8.0, 12.0, 15.0,
            "General healthcare LBO range; adjust for sector specifics"
        ),
    },
    "add_on": {
        "acute_hospital": EntryMultipleBand(
            "acute_hospital", "add_on", 5.0, 6.5, 9.0, 11.0,
            "Add-ons typically 1-2x below platform; synergies must close gap"
        ),
        "behavioral_health": EntryMultipleBand(
            "behavioral_health", "add_on", 6.0, 7.5, 11.0, 14.0,
            "Add-on BH below platform but synergy credit requires integration proof"
        ),
        "asc_surgical": EntryMultipleBand(
            "asc_surgical", "add_on", 6.0, 7.5, 11.0, 13.0,
            "ASC add-ons at discount to platform; de-novo lower than tuck-in"
        ),
        "other": EntryMultipleBand(
            "other", "add_on", 5.0, 7.0, 10.0, 13.0,
            "Add-on healthcare: platform discount applies"
        ),
    },
    "carve_out": {
        "other": EntryMultipleBand(
            "other", "carve_out", 7.0, 9.0, 14.0, 18.0,
            "Carve-outs demand premium for complexity; stranded cost risk adds ~1-2x"
        ),
    },
    "ipo": {
        "value_based_care": EntryMultipleBand(
            "value_based_care", "ipo", 5.0, 8.0, 20.0, 40.0,
            "VBC IPOs on revenue; 10-15x NTM revenue for profitable; loss-making = 5-8x"
        ),
        "rcm_health_it": EntryMultipleBand(
            "rcm_health_it", "ipo", 5.0, 8.0, 25.0, 50.0,
            "HIT IPOs on ARR multiples; >20x NTM ARR requires >30% growth"
        ),
        "other": EntryMultipleBand(
            "other", "ipo", 8.0, 10.0, 18.0, 30.0,
            "Healthcare IPO range; above 20x requires hypergrowth narrative"
        ),
    },
}

_DEFAULT_BAND = EntryMultipleBand(
    "other", "other", 6.0, 8.0, 13.0, 17.0,
    "Default healthcare band; refine with sector-specific data"
)


def get_entry_band(deal_type: str, sector: str) -> EntryMultipleBand:
    """Return the entry multiple band for a given deal type and sector."""
    type_key = deal_type.lower().replace("-", "_").replace(" ", "_")
    sector_key = sector.lower().replace(" ", "_")

    type_bands = _BANDS.get(type_key, _BANDS.get("lbo", {}))
    band = type_bands.get(sector_key, type_bands.get("other", _DEFAULT_BAND))
    return band


# ---------------------------------------------------------------------------
# Multiple flag
# ---------------------------------------------------------------------------

def _classify_deal_type(deal: Dict[str, Any]) -> str:
    """Infer deal type from deal_name + notes."""
    text = ((deal.get("deal_name") or "") + " " + (deal.get("notes") or "")).lower()
    if any(k in text for k in ["ipo", "initial public"]):
        return "ipo"
    if any(k in text for k in ["spac", "acquisition corp"]):
        return "spac"
    if any(k in text for k in ["carve-out", "carve_out", "carve out"]):
        return "carve_out"
    if any(k in text for k in ["add-on", "add_on", "add on", "cluster"]):
        return "add_on"
    if any(k in text for k in ["merger", "combination"]):
        return "merger"
    return "lbo"


def _classify_sector_simple(deal: Dict[str, Any]) -> str:
    text = ((deal.get("deal_name") or "") + " " + (deal.get("notes") or "")).lower()
    _QUICK = {
        "behavioral_health": ["behavioral", "mental health", "psychiatr"],
        "home_health": ["home health", "hha", "home care", "infusion"],
        "asc_surgical": ["asc", "ambulatory", "surgical center", "surgery center"],
        "rcm_health_it": ["rcm", "revenue cycle", "health it", "netsmart"],
        "physician_staffing": ["staffing", "envision", "teamhealth"],
        "hospice_palliative": ["hospice", "palliative"],
        "dso_dental_eye": ["dental", "dso", "dermatol", "ophthalmol"],
        "value_based_care": ["value-based", "vbc", "medicare advantage", "capitation"],
        "acute_hospital": ["hospital system", "health system", "health care system"],
    }
    for sector, keywords in _QUICK.items():
        if any(kw in text for kw in keywords):
            return sector
    return "other"


def multiple_flag(deal: Dict[str, Any]) -> List[str]:
    """Return list of human-readable flags about entry multiple reasonableness.

    Returns empty list if multiple is in-band or missing.
    """
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    if not ev or not ebitda:
        return []
    try:
        ev_f, ebitda_f = float(ev), float(ebitda)
    except (TypeError, ValueError):
        return []
    if ebitda_f <= 0:
        return ["Negative/zero EBITDA — cannot compute EV/EBITDA multiple; revenue-multiple analysis required"]

    multiple = ev_f / ebitda_f
    deal_type = _classify_deal_type(deal)
    sector = _classify_sector_simple(deal)
    band = get_entry_band(deal_type, sector)

    flags = []
    if multiple < band.low:
        flags.append(
            f"Entry multiple {multiple:.1f}x below expected floor {band.low:.1f}x "
            f"({band.sector}/{band.deal_type}) — verify data or check asset quality risk"
        )
    elif multiple > band.high:
        flags.append(
            f"Entry multiple {multiple:.1f}x above ceiling {band.high:.1f}x "
            f"({band.sector}/{band.deal_type}) — stress-test IRR at 15%+ exit multiple compression"
        )
    elif multiple > band.fair_high:
        flags.append(
            f"Entry multiple {multiple:.1f}x in upper-fair range "
            f"({band.fair_high:.1f}–{band.high:.1f}x) — premium requires specific upside catalyst"
        )
    return flags


# ---------------------------------------------------------------------------
# Hold period flag
# ---------------------------------------------------------------------------

_HOLD_NORMS: Dict[str, tuple] = {
    "lbo": (3.0, 7.0),
    "add_on": (2.0, 5.0),
    "carve_out": (3.0, 7.0),
    "ipo": (2.0, 6.0),
    "spac": (1.5, 4.0),
    "merger": (2.0, 5.0),
    "other": (3.0, 7.0),
}


def hold_period_flag(deal: Dict[str, Any]) -> List[str]:
    """Flag unusual hold periods vs deal-type norms."""
    hold = deal.get("hold_years")
    if hold is None:
        return []
    try:
        hold_f = float(hold)
    except (TypeError, ValueError):
        return []

    deal_type = _classify_deal_type(deal)
    lo, hi = _HOLD_NORMS.get(deal_type, (3.0, 7.0))

    flags = []
    if hold_f < lo:
        flags.append(
            f"Hold period {hold_f:.1f}y below norm ({lo:.0f}–{hi:.0f}y) for {deal_type} "
            f"— check if forced exit or distressed situation"
        )
    elif hold_f > hi:
        flags.append(
            f"Hold period {hold_f:.1f}y above norm ({lo:.0f}–{hi:.0f}y) for {deal_type} "
            f"— may indicate difficulty exiting or value creation thesis extended"
        )
    return flags


# ---------------------------------------------------------------------------
# Healthcare trap scan
# ---------------------------------------------------------------------------

_TRAPS: List[Dict[str, Any]] = [
    {
        "trap": "medicaid_concentration",
        "severity": "high",
        "trigger": lambda d: (
            _payer_share(d, "medicaid") > 0.55
        ),
        "detail": "Medicaid >55% — rate cuts and managed care expansion risk; "
                  "check state FMAP + managed care penetration",
    },
    {
        "trap": "medicare_only_concentration",
        "severity": "medium",
        "trigger": lambda d: (
            _payer_share(d, "medicare") > 0.80
            and _payer_share(d, "medicaid") < 0.10
        ),
        "detail": "Medicare >80% concentration — exposure to CMS rate changes + "
                  "PDGM/hospice cap; limited commercial upside",
    },
    {
        "trap": "single_state_geographic",
        "severity": "medium",
        "trigger": lambda d: (
            "CA" == (d.get("state") or "")
            or "FL" == (d.get("state") or "")
        ) and (d.get("ev_mm") or 0) > 500,
        "detail": "Large single-state concentration (CA/FL) — regulatory, rate, "
                  "and staffing risk amplified vs national footprint",
    },
    {
        "trap": "negative_ebitda_at_scale",
        "severity": "high",
        "trigger": lambda d: (
            (d.get("ebitda_at_entry_mm") or 0) < -20
            and (d.get("ev_mm") or 0) > 500
        ),
        "detail": "Negative EBITDA >$20M at entry — path to profitability must "
                  "be explicit; capitation loss-ratio trend critical",
    },
    {
        "trap": "extreme_leverage",
        "severity": "high",
        "trigger": lambda d: (d.get("leverage_x") or 0) > 7.0,
        "detail": "Leverage >7x — covenant headroom likely thin; "
                  "rate sensitivity at 100bps could impair coverage",
    },
    {
        "trap": "short_hold_high_moic",
        "severity": "low",
        "trigger": lambda d: (
            (d.get("hold_years") or 99) < 2.5
            and (d.get("realized_moic") or 0) > 3.0
        ),
        "detail": "Short hold (<2.5y) + high MOIC — verify timing; "
                  "may reflect IPO pop or strategic premium rather than operational value creation",
    },
    {
        "trap": "total_loss_risk",
        "severity": "critical",
        "trigger": lambda d: (d.get("realized_moic") or 1.0) < 0.2,
        "detail": "Near-total loss (MOIC <0.2x) — review for regulatory disruption, "
                  "structural Medicaid issues, or over-leveraged distress",
    },
]


def _payer_share(deal: Dict, payer: str) -> float:
    import json
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            return 0.0
    if not isinstance(pm, dict):
        return 0.0
    return float(pm.get(payer, 0.0) or 0.0)


def healthcare_trap_scan(deal: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scan a deal for known healthcare PE traps.

    Returns list of {trap, severity, detail} dicts.
    Severity: critical / high / medium / low.
    """
    triggered = []
    for trap in _TRAPS:
        try:
            if trap["trigger"](deal):
                triggered.append({
                    "trap": trap["trap"],
                    "severity": trap["severity"],
                    "detail": trap["detail"],
                })
        except Exception:
            pass
    return triggered


# ---------------------------------------------------------------------------
# Return plausibility
# ---------------------------------------------------------------------------

_MOIC_IRR_CONSISTENCY: List[tuple] = [
    # (moic_lo, moic_hi, irr_lo, irr_hi, hold_lo, hold_hi)
    (0.0, 1.0, -1.0, 0.0, 0.0, 10.0),   # loss
    (1.0, 1.5, -0.05, 0.10, 1.0, 10.0),  # modest return
    (1.5, 2.5, 0.08, 0.25, 2.0, 8.0),    # standard
    (2.5, 4.0, 0.18, 0.40, 2.0, 7.0),    # good
    (4.0, 8.0, 0.25, 0.60, 2.0, 6.0),    # excellent
    (8.0, 100.0, 0.40, 1.0, 1.0, 5.0),   # exceptional
]


def return_plausibility_check(deal: Dict[str, Any]) -> Dict[str, Any]:
    """Check whether moic + irr + hold_years are internally consistent.

    Returns {plausible: bool, warnings: list[str]}
    """
    moic = deal.get("realized_moic")
    irr = deal.get("realized_irr")
    hold = deal.get("hold_years")

    warnings: List[str] = []

    if moic is None or irr is None:
        return {"plausible": True, "warnings": ["Insufficient data for plausibility check"]}

    try:
        moic_f = float(moic)
        irr_f = float(irr)
    except (TypeError, ValueError):
        return {"plausible": True, "warnings": ["Non-numeric MOIC/IRR"]}

    # MOIC-IRR direction consistency
    if moic_f > 1.0 and irr_f < 0:
        warnings.append(f"MOIC {moic_f:.2f}x is positive but IRR {irr_f:.1%} is negative — inconsistent")
    if moic_f < 1.0 and irr_f > 0.05:
        warnings.append(f"MOIC {moic_f:.2f}x below 1 but IRR {irr_f:.1%} positive — check hold period")

    # Hold-MOIC-IRR triangle
    if hold is not None:
        try:
            hold_f = float(hold)
        except (TypeError, ValueError):
            hold_f = None
        if hold_f and hold_f > 0 and moic_f > 0:
            implied_irr = moic_f ** (1.0 / hold_f) - 1.0
            if abs(implied_irr - irr_f) > 0.10:
                warnings.append(
                    f"MOIC {moic_f:.2f}x over {hold_f:.1f}y implies IRR ~{implied_irr:.1%} "
                    f"but reported IRR is {irr_f:.1%} (gap >{abs(implied_irr - irr_f):.0%})"
                )

    plausible = len([w for w in warnings if "inconsistent" in w or "gap" in w]) == 0
    return {"plausible": plausible, "warnings": warnings}


# ---------------------------------------------------------------------------
# Full assessment
# ---------------------------------------------------------------------------

def full_heuristic_assessment(deal: Dict[str, Any]) -> Dict[str, Any]:
    """Run all heuristics on a single deal dict.

    Returns {deal_name, multiple_flags, hold_flags, traps,
             plausibility, sector, deal_type, entry_band, overall_signal}.
    """
    m_flags = multiple_flag(deal)
    h_flags = hold_period_flag(deal)
    traps = healthcare_trap_scan(deal)
    plaus = return_plausibility_check(deal)

    sector = _classify_sector_simple(deal)
    deal_type = _classify_deal_type(deal)
    band = get_entry_band(deal_type, sector)

    # Overall signal
    critical_count = sum(1 for t in traps if t["severity"] == "critical")
    high_count = sum(1 for t in traps if t["severity"] == "high")
    flag_count = len(m_flags) + len(h_flags)

    if critical_count > 0 or not plaus["plausible"]:
        signal = "red"
    elif high_count >= 2 or (high_count >= 1 and flag_count >= 2):
        signal = "amber"
    elif high_count >= 1 or flag_count >= 2:
        signal = "amber"
    elif flag_count >= 1 or len(traps) >= 2:
        signal = "yellow"
    else:
        signal = "green"

    return {
        "deal_name": deal.get("deal_name", ""),
        "sector": sector,
        "deal_type": deal_type,
        "entry_band": {
            "low": band.low,
            "fair_low": band.fair_low,
            "fair_high": band.fair_high,
            "high": band.high,
            "notes": band.notes,
        },
        "multiple_flags": m_flags,
        "hold_flags": h_flags,
        "traps": traps,
        "plausibility": plaus,
        "overall_signal": signal,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_SIGNAL_LABEL = {
    "red": "🔴 RED — critical issues require resolution",
    "amber": "🟠 AMBER — significant concerns warrant deeper diligence",
    "yellow": "🟡 YELLOW — minor flags; manageable with monitoring",
    "green": "🟢 GREEN — no material heuristic concerns",
}


def heuristic_report(assessment: Dict[str, Any]) -> str:
    """Format a full heuristic assessment as a human-readable text report."""
    lines = [
        f"Senior Partner Heuristic Assessment",
        f"Deal: {assessment.get('deal_name', 'N/A')}",
        "=" * 64,
        f"  Sector     : {assessment.get('sector', '')}",
        f"  Deal type  : {assessment.get('deal_type', '')}",
        f"  Signal     : {_SIGNAL_LABEL.get(assessment.get('overall_signal', 'green'), '')}",
        "-" * 64,
    ]

    band = assessment.get("entry_band", {})
    lines.append(
        f"  Entry band : {band.get('low', '?'):.1f}x — "
        f"{band.get('fair_low', '?'):.1f}x / {band.get('fair_high', '?'):.1f}x — "
        f"{band.get('high', '?'):.1f}x"
    )
    if band.get("notes"):
        lines.append(f"               {band['notes']}")

    if assessment.get("multiple_flags"):
        lines.append("")
        lines.append("  Multiple Flags:")
        for f in assessment["multiple_flags"]:
            lines.append(f"    • {f}")

    if assessment.get("hold_flags"):
        lines.append("")
        lines.append("  Hold Period Flags:")
        for f in assessment["hold_flags"]:
            lines.append(f"    • {f}")

    if assessment.get("traps"):
        lines.append("")
        lines.append("  Healthcare Traps:")
        for t in assessment["traps"]:
            lines.append(f"    [{t['severity'].upper()}] {t['trap']}: {t['detail']}")

    plaus = assessment.get("plausibility", {})
    if plaus.get("warnings"):
        lines.append("")
        lines.append("  Return Plausibility:")
        for w in plaus["warnings"]:
            lines.append(f"    • {w}")

    lines.append("=" * 64)
    return "\n".join(lines) + "\n"
