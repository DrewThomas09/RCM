"""Exit Multiple Analysis — forward exit multiple modeling and decomposition from corpus."""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exit driver categories
# ---------------------------------------------------------------------------

_EXIT_DRIVER_WEIGHTS = {
    "sector_rerating": 0.30,      # sector-level multiple expansion/contraction
    "ebitda_growth": 0.25,        # EBITDA growth from entry to exit
    "payer_mix_improvement": 0.15,
    "scale_premium": 0.12,        # larger = higher multiple
    "strategic_buyer_premium": 0.10,
    "market_timing": 0.08,
}

# Sector baseline exit multiple benchmarks (from corpus averages)
_SECTOR_EXIT_MULT_RANGES: Dict[str, Tuple[float, float, float]] = {
    # (P25, P50, P75) exit EV/EBITDA
    "Physician Group":       (8.5,  10.5, 13.0),
    "Behavioral Health":     (8.0,  10.0, 12.5),
    "Dental":                (9.0,  11.0, 14.0),
    "Dermatology":           (9.5,  12.0, 15.0),
    "Urgent Care":           (7.5,   9.5, 12.0),
    "Ambulatory Surgery":    (8.0,  10.0, 12.5),
    "Home Health":           (7.0,   9.0, 11.5),
    "Hospice":               (8.0,  10.5, 13.0),
    "Radiology":             (8.5,  11.0, 13.5),
    "Laboratory":            (9.0,  12.0, 15.0),
    "Health IT":             (12.0, 16.0, 22.0),
    "Revenue Cycle":         (8.0,  10.5, 13.0),
    "default":               (8.0,  10.0, 13.0),
}

# MOIC sensitivity to exit multiple change (from corpus regression)
_MOIC_PER_TURN = 0.18   # 1x higher exit multiple → ~0.18x MOIC uplift per turn

# Market timing adjustment (relative to median vintage year)
_TIMING_PREMIUMS = {
    2019: 0.8, 2020: -1.2, 2021: 1.5, 2022: -0.5,
    2018: 0.3, 2017: 0.2, 2016: 0.1, 2015: 0.0,
    2014: -0.2, 2013: -0.1,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExitScenario:
    label: str
    exit_multiple: float
    ebitda_at_exit_mm: float
    ev_at_exit_mm: float
    moic: float
    irr: float
    hold_years: float
    multiple_expansion: float     # vs entry
    probability: float            # 0-1


@dataclass
class ExitDriverDecomp:
    driver: str
    label: str
    weight: float
    contribution_turns: float     # multiple turns attributable to this driver
    contribution_moic: float


@dataclass
class ExitComparable:
    company: str
    sector: str
    year: int
    entry_multiple: float
    exit_multiple_implied: float
    hold_years: float
    moic: float
    irr: float
    multiple_expansion: float


@dataclass
class ExitMultipleResult:
    sector: str
    entry_multiple: float
    ebitda_mm: float
    ev_mm: float
    scenarios: List[ExitScenario]
    decomp: List[ExitDriverDecomp]
    comparables: List[ExitComparable]
    sector_p25: float
    sector_p50: float
    sector_p75: float
    base_exit_multiple: float
    moic_sensitivity_per_turn: float
    corpus_deal_count: int
    timing_premium: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 55):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _sector_ranges(sector: str) -> Tuple[float, float, float]:
    for key, ranges in _SECTOR_EXIT_MULT_RANGES.items():
        if key.lower() in sector.lower() or sector.lower() in key.lower():
            return ranges
    return _SECTOR_EXIT_MULT_RANGES["default"]


def _calc_irr(moic: float, hold_years: float) -> float:
    if hold_years <= 0 or moic <= 0:
        return 0.0
    return round((moic ** (1 / hold_years)) - 1.0, 4)


def _build_decomp(entry_multiple: float, base_exit: float, sector: str,
                  ebitda_growth_pct: float, comm_pct: float, ev_mm: float) -> List[ExitDriverDecomp]:
    total_expansion = base_exit - entry_multiple
    decomps = []

    # Sector rerating
    sector_rerate = total_expansion * _EXIT_DRIVER_WEIGHTS["sector_rerating"]
    decomps.append(ExitDriverDecomp(
        driver="sector_rerating",
        label="Sector Re-Rating",
        weight=_EXIT_DRIVER_WEIGHTS["sector_rerating"],
        contribution_turns=round(sector_rerate, 2),
        contribution_moic=round(sector_rerate * _MOIC_PER_TURN, 3),
    ))

    # EBITDA growth premium (higher growth → buyers pay more)
    growth_premium = max(0.0, (ebitda_growth_pct - 5.0) / 100 * 8.0)
    ebitda_contrib = min(total_expansion * _EXIT_DRIVER_WEIGHTS["ebitda_growth"],
                        growth_premium)
    decomps.append(ExitDriverDecomp(
        driver="ebitda_growth",
        label="EBITDA Growth Premium",
        weight=_EXIT_DRIVER_WEIGHTS["ebitda_growth"],
        contribution_turns=round(ebitda_contrib, 2),
        contribution_moic=round(ebitda_contrib * _MOIC_PER_TURN, 3),
    ))

    # Payer mix improvement (commercial-heavy → premium)
    payer_premium = (comm_pct - 0.50) * 3.0 if comm_pct > 0.50 else 0.0
    payer_contrib = min(total_expansion * _EXIT_DRIVER_WEIGHTS["payer_mix_improvement"],
                       payer_premium)
    decomps.append(ExitDriverDecomp(
        driver="payer_mix_improvement",
        label="Payer Mix Premium",
        weight=_EXIT_DRIVER_WEIGHTS["payer_mix_improvement"],
        contribution_turns=round(payer_contrib, 2),
        contribution_moic=round(payer_contrib * _MOIC_PER_TURN, 3),
    ))

    # Scale premium
    scale = math.log10(max(ev_mm, 10)) / math.log10(1000)
    scale_contrib = total_expansion * _EXIT_DRIVER_WEIGHTS["scale_premium"] * scale
    decomps.append(ExitDriverDecomp(
        driver="scale_premium",
        label="Scale Premium",
        weight=_EXIT_DRIVER_WEIGHTS["scale_premium"],
        contribution_turns=round(scale_contrib, 2),
        contribution_moic=round(scale_contrib * _MOIC_PER_TURN, 3),
    ))

    # Strategic buyer premium
    strat_contrib = total_expansion * _EXIT_DRIVER_WEIGHTS["strategic_buyer_premium"]
    decomps.append(ExitDriverDecomp(
        driver="strategic_buyer_premium",
        label="Strategic Buyer Premium",
        weight=_EXIT_DRIVER_WEIGHTS["strategic_buyer_premium"],
        contribution_turns=round(strat_contrib, 2),
        contribution_moic=round(strat_contrib * _MOIC_PER_TURN, 3),
    ))

    # Market timing (residual)
    residual = total_expansion - sum(d.contribution_turns for d in decomps)
    decomps.append(ExitDriverDecomp(
        driver="market_timing",
        label="Market Timing",
        weight=_EXIT_DRIVER_WEIGHTS["market_timing"],
        contribution_turns=round(residual, 2),
        contribution_moic=round(residual * _MOIC_PER_TURN, 3),
    ))

    return decomps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_exit_multiple(
    sector: str,
    entry_multiple: float,
    ebitda_mm: float,
    hold_years: float = 5.0,
    ebitda_growth_pct: float = 8.0,
    comm_pct: float = 0.55,
    entry_year: int = 2020,
) -> ExitMultipleResult:
    corpus = _load_corpus()

    ev_mm = entry_multiple * ebitda_mm
    p25, p50, p75 = _sector_ranges(sector)
    timing_adj = _TIMING_PREMIUMS.get(entry_year, 0.0)
    base_exit = p50 + timing_adj

    # EBITDA at exit
    ebitda_exit = ebitda_mm * (1 + ebitda_growth_pct / 100) ** hold_years

    def _scenario(label: str, exit_mult: float, prob: float) -> ExitScenario:
        ev_exit = exit_mult * ebitda_exit
        equity_entry = ev_mm * 0.45
        equity_exit = ev_exit * 0.45
        moic = round(equity_exit / equity_entry, 2) if equity_entry > 0 else 0.0
        irr = _calc_irr(moic, hold_years)
        return ExitScenario(
            label=label,
            exit_multiple=round(exit_mult, 1),
            ebitda_at_exit_mm=round(ebitda_exit, 1),
            ev_at_exit_mm=round(ev_exit, 1),
            moic=moic,
            irr=irr,
            hold_years=hold_years,
            multiple_expansion=round(exit_mult - entry_multiple, 1),
            probability=prob,
        )

    scenarios = [
        _scenario("Bear", p25 - 0.5, 0.20),
        _scenario("Base", base_exit, 0.45),
        _scenario("Bull", p75 + 0.5, 0.25),
        _scenario("Strategic Exit", p75 + 2.0, 0.10),
    ]

    decomp = _build_decomp(entry_multiple, base_exit, sector,
                           ebitda_growth_pct, comm_pct, ev_mm)

    # Corpus comparables
    sector_deals = [d for d in corpus if
                    sector.lower()[:6] in (d.get("sector") or "").lower() or
                    (d.get("sector") or "").lower()[:6] in sector.lower()]
    if len(sector_deals) < 5:
        sector_deals = corpus

    def _comp(d: dict) -> ExitComparable:
        em = d.get("ev_ebitda") or 10.0
        hold = d.get("hold_years") or 4.0
        moic = d.get("moic") or 2.5
        irr = d.get("irr") or 0.22
        # Implied exit multiple: moic = (exit_mult/entry_mult) * (1+g)^hold => exit_mult = moic * entry_mult / (1+g)^hold
        growth_factor = (1 + ebitda_growth_pct / 100) ** hold
        implied_exit = em * moic / growth_factor if growth_factor > 0 else em
        return ExitComparable(
            company=d.get("company_name", "—"),
            sector=d.get("sector", "—"),
            year=d.get("year", 0),
            entry_multiple=round(em, 1),
            exit_multiple_implied=round(implied_exit, 1),
            hold_years=round(hold, 1),
            moic=round(moic, 2),
            irr=round(irr, 4),
            multiple_expansion=round(implied_exit - em, 1),
        )

    comps_raw = sorted(sector_deals,
                       key=lambda d: abs((d.get("ev_ebitda") or 10.0) - entry_multiple))[:15]
    comparables = [_comp(d) for d in comps_raw]

    return ExitMultipleResult(
        sector=sector,
        entry_multiple=entry_multiple,
        ebitda_mm=ebitda_mm,
        ev_mm=ev_mm,
        scenarios=scenarios,
        decomp=decomp,
        comparables=comparables,
        sector_p25=p25,
        sector_p50=p50,
        sector_p75=p75,
        base_exit_multiple=base_exit,
        moic_sensitivity_per_turn=_MOIC_PER_TURN,
        corpus_deal_count=len(corpus),
        timing_premium=timing_adj,
    )
