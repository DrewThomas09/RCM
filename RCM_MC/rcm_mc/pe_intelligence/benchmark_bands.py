"""Benchmark bands — additional subsector benchmarks not elsewhere.

Extends `reasonableness.py`, `extra_bands.py`, `reimbursement_bands.py`
with five more partner-prudent bands:

- **SG&A as % of revenue** — overhead intensity.
- **Interest expense as % of EBITDA** — debt-service intensity.
- **Same-store-sales growth** — volume-vs-rate decomposition.
- **Net working-capital days** — AR + inventory - AP.
- **Outpatient mix** — share of revenue from outpatient.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .reasonableness import (
    Band,
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
)


# ── SG&A bands ─────────────────────────────────────────────────────

_SGA_BANDS: Dict[str, Band] = {
    "acute_care": Band(
        metric="sga_pct_of_revenue", regime="acute-care",
        low=0.06, high=0.10, stretch_high=0.13, implausible_high=0.18,
        implausible_low=0.02,
        source="AHA + CMS cost reports",
    ),
    "asc": Band(
        metric="sga_pct_of_revenue", regime="ASC",
        low=0.08, high=0.13, stretch_high=0.17, implausible_high=0.22,
        source="ASCA",
    ),
    "behavioral": Band(
        metric="sga_pct_of_revenue", regime="behavioral",
        low=0.08, high=0.15, stretch_high=0.20, implausible_high=0.28,
        source="Industry",
    ),
    "post_acute": Band(
        metric="sga_pct_of_revenue", regime="post-acute",
        low=0.06, high=0.12, stretch_high=0.15, implausible_high=0.20,
        source="AHCA",
    ),
    "outpatient": Band(
        metric="sga_pct_of_revenue", regime="outpatient / MSO",
        low=0.10, high=0.16, stretch_high=0.20, implausible_high=0.28,
        source="MGMA",
    ),
}


def _key(s: Optional[str]) -> str:
    if not s:
        return ""
    alias = {
        "hospital": "acute_care", "acute": "acute_care",
        "snf": "post_acute", "ltach": "post_acute",
        "psych": "behavioral", "clinic": "outpatient",
        "cah": "acute_care",
    }
    return alias.get(s.lower().strip(), s.lower().strip())


def check_sga_intensity(
    sga_pct: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if sga_pct is None:
        return BandCheck(
            metric="sga_pct_of_revenue", observed=None,
            verdict=VERDICT_UNKNOWN, rationale="SG&A not provided.",
        )
    key = _key(hospital_type)
    band = _SGA_BANDS.get(key)
    if band is None:
        return BandCheck(
            metric="sga_pct_of_revenue", observed=sga_pct,
            verdict=VERDICT_UNKNOWN,
            rationale=f"No SG&A band for {key}.",
        )
    verdict = band.classify(sga_pct)
    pct = f"{sga_pct*100:.1f}%"
    note_map = {
        VERDICT_IN_BAND: "SG&A intensity is peer-normal.",
        VERDICT_STRETCH: "SG&A is above peer — overhead rationalization lever exists.",
        VERDICT_OUT_OF_BAND: "SG&A outside peer range — investigate accounting definition.",
        VERDICT_IMPLAUSIBLE: "SG&A outside any defensible range — re-verify allocations.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric="sga_pct_of_revenue", observed=sga_pct, verdict=verdict,
        band=band,
        rationale=f"{pct} SG&A intensity vs {band.regime} peer "
                  f"{band.low*100:.0f}-{band.high*100:.0f}%.",
        partner_note=note_map.get(verdict, ""),
    )


# ── Interest expense as % of EBITDA ────────────────────────────────

_INTEREST_BAND = Band(
    metric="interest_to_ebitda", regime="LBO capital structure",
    low=0.25, high=0.45, stretch_high=0.55, implausible_high=0.75,
    implausible_low=0.10,
    source="HC-PE LBO comps",
)


def check_interest_to_ebitda(
    ratio: Optional[float],
) -> BandCheck:
    if ratio is None:
        return BandCheck(
            metric="interest_to_ebitda", observed=None,
            verdict=VERDICT_UNKNOWN,
            rationale="Interest/EBITDA ratio not reported.",
        )
    verdict = _INTEREST_BAND.classify(ratio)
    pct = f"{ratio*100:.1f}%"
    note_map = {
        VERDICT_IN_BAND: "Interest burden normal for healthcare LBOs.",
        VERDICT_STRETCH: "Interest burden elevated — coverage thin.",
        VERDICT_OUT_OF_BAND: "Interest burden outside peer range.",
        VERDICT_IMPLAUSIBLE: "Interest burden implausible — verify rate assumption.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric="interest_to_ebitda", observed=ratio, verdict=verdict,
        band=_INTEREST_BAND,
        rationale=f"{pct} of EBITDA goes to interest vs peer "
                  f"{_INTEREST_BAND.low*100:.0f}-{_INTEREST_BAND.high*100:.0f}%.",
        partner_note=note_map.get(verdict, ""),
    )


# ── Same-store sales growth ────────────────────────────────────────

_SSSG_BAND = Band(
    metric="same_store_sales_growth", regime="healthcare",
    low=0.02, high=0.06, stretch_high=0.09, implausible_high=0.15,
    implausible_low=-0.05,
    source="Same-store revenue growth peer set",
)


def check_same_store_sales_growth(
    growth: Optional[float],
) -> BandCheck:
    if growth is None:
        return BandCheck(
            metric="same_store_sales_growth", observed=None,
            verdict=VERDICT_UNKNOWN,
            rationale="SSSG not reported.",
        )
    verdict = _SSSG_BAND.classify(growth)
    pct = f"{growth*100:.1f}%"
    note_map = {
        VERDICT_IN_BAND: "Same-store growth within peer band.",
        VERDICT_STRETCH: "Same-store growth above peer — validate drivers.",
        VERDICT_OUT_OF_BAND: "Off-peer same-store growth.",
        VERDICT_IMPLAUSIBLE: "SSSG implausible — likely mis-classified or one-time.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric="same_store_sales_growth", observed=growth, verdict=verdict,
        band=_SSSG_BAND,
        rationale=f"SSSG {pct} vs peer {_SSSG_BAND.low*100:.1f}-{_SSSG_BAND.high*100:.1f}%.",
        partner_note=note_map.get(verdict, ""),
    )


# ── Net working-capital days ──────────────────────────────────────

_NWC_BAND = Band(
    metric="net_working_capital_days", regime="healthcare",
    low=15, high=45, stretch_high=60, implausible_high=90,
    implausible_low=-15,
    source="Healthcare NWC peer set",
)


def check_nwc_days(
    days: Optional[float],
) -> BandCheck:
    if days is None:
        return BandCheck(
            metric="net_working_capital_days", observed=None,
            verdict=VERDICT_UNKNOWN,
            rationale="Net working capital days not reported.",
        )
    verdict = _NWC_BAND.classify(days)
    note_map = {
        VERDICT_IN_BAND: "NWC days within peer band.",
        VERDICT_STRETCH: "NWC days elevated — working-capital lever opportunity.",
        VERDICT_OUT_OF_BAND: "NWC days outside peer band.",
        VERDICT_IMPLAUSIBLE: "NWC days implausible — verify components.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric="net_working_capital_days", observed=days, verdict=verdict,
        band=_NWC_BAND,
        rationale=f"NWC days {days:.0f} vs peer {_NWC_BAND.low:.0f}-{_NWC_BAND.high:.0f}.",
        partner_note=note_map.get(verdict, ""),
    )


# ── Outpatient mix ────────────────────────────────────────────────

_OUTPATIENT_BANDS: Dict[str, Band] = {
    "acute_care": Band(
        metric="outpatient_revenue_share", regime="acute-care",
        low=0.40, high=0.65, stretch_high=0.80, implausible_high=0.95,
        implausible_low=0.15,
        source="AHA",
    ),
    "critical_access": Band(
        metric="outpatient_revenue_share", regime="CAH",
        low=0.50, high=0.75, stretch_high=0.88, implausible_high=0.98,
        implausible_low=0.25,
        source="CMS CAH data",
    ),
}


def check_outpatient_share(
    share: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if share is None:
        return BandCheck(
            metric="outpatient_revenue_share", observed=None,
            verdict=VERDICT_UNKNOWN,
            rationale="Outpatient share not reported.",
        )
    key = _key(hospital_type)
    band = _OUTPATIENT_BANDS.get(key)
    if band is None:
        return BandCheck(
            metric="outpatient_revenue_share", observed=share,
            verdict=VERDICT_UNKNOWN,
            rationale="Outpatient share band only for acute-care / CAH.",
        )
    verdict = band.classify(share)
    pct = f"{share*100:.1f}%"
    note_map = {
        VERDICT_IN_BAND: "Outpatient mix within peer band.",
        VERDICT_STRETCH: "Higher outpatient share — reflects recent shift.",
        VERDICT_OUT_OF_BAND: "Off-peer outpatient share.",
        VERDICT_IMPLAUSIBLE: "Outpatient share implausible.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric="outpatient_revenue_share", observed=share, verdict=verdict,
        band=band,
        rationale=f"Outpatient share {pct} vs {band.regime} peer "
                  f"{band.low*100:.0f}-{band.high*100:.0f}%.",
        partner_note=note_map.get(verdict, ""),
    )


def run_benchmark_bands(
    *,
    hospital_type: Optional[str] = None,
    sga_pct_of_revenue: Optional[float] = None,
    interest_to_ebitda: Optional[float] = None,
    same_store_sales_growth: Optional[float] = None,
    net_working_capital_days: Optional[float] = None,
    outpatient_revenue_share: Optional[float] = None,
) -> List[BandCheck]:
    out: List[BandCheck] = []
    out.append(check_sga_intensity(sga_pct_of_revenue,
                                   hospital_type=hospital_type))
    out.append(check_interest_to_ebitda(interest_to_ebitda))
    out.append(check_same_store_sales_growth(same_store_sales_growth))
    out.append(check_nwc_days(net_working_capital_days))
    out.append(check_outpatient_share(outpatient_revenue_share,
                                      hospital_type=hospital_type))
    return out
