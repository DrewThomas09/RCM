"""Capital Efficiency Analytics — return density per unit of entry price and hold time.

Computes three efficiency ratios from the corpus:
  1. MOIC Efficiency = MOIC / EV/EBITDA (return per turn of multiple paid)
  2. IRR Density = IRR / hold_years (annualized return velocity)
  3. Value Creation Density = (MOIC - 1) / hold_years (net return per year)

Aggregates by sector, vintage, size bucket, and payer regime to find which
deal profiles generate the most return per dollar of entry price.
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 45):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _moic(d: Dict[str, Any]) -> Optional[float]:
    for k in ("moic", "realized_moic"):
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _irr(d: Dict[str, Any]) -> Optional[float]:
    for k in ("irr", "realized_irr"):
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _hold(d: Dict[str, Any]) -> Optional[float]:
    v = d.get("hold_years")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    return None


def _ev_ebitda(d: Dict[str, Any]) -> Optional[float]:
    ev = d.get("ev_mm")
    eb = d.get("ebitda_at_entry_mm")
    if ev and eb and float(eb) > 0:
        return round(float(ev) / float(eb), 2)
    stored = d.get("ev_ebitda")
    if stored:
        try:
            return float(stored)
        except (TypeError, ValueError):
            pass
    return None


def _ev(d: Dict[str, Any]) -> Optional[float]:
    v = d.get("ev_mm")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    return None


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 4)


def _size_bucket(ev_mm: float) -> str:
    if ev_mm < 100:
        return "<$100M"
    if ev_mm < 300:
        return "$100–300M"
    if ev_mm < 750:
        return "$300–750M"
    if ev_mm < 2000:
        return "$750M–2B"
    return ">$2B"


def _payer_regime(d: Dict[str, Any]) -> str:
    pm = d.get("payer_mix")
    if not isinstance(pm, dict):
        return "Unknown"
    comm = pm.get("commercial") or pm.get("comm") or 0
    mcare = pm.get("medicare") or pm.get("mcare") or 0
    mcaid = pm.get("medicaid") or pm.get("mcaid") or 0
    try:
        comm, mcare, mcaid = float(comm), float(mcare), float(mcaid)
    except (TypeError, ValueError):
        return "Unknown"
    if comm >= 0.60:
        return "Commercial-Heavy"
    if mcare >= 0.50:
        return "Medicare-Heavy"
    if mcaid >= 0.40:
        return "Medicaid-Heavy"
    if (mcare + mcaid) >= 0.60:
        return "Government-Heavy"
    return "Balanced"


@dataclass
class DealEfficiency:
    source_id: str
    company_name: str
    sector: str
    year: int
    ev_mm: Optional[float]
    ev_ebitda: Optional[float]
    moic: float
    irr: Optional[float]
    hold_years: float
    moic_efficiency: float      # MOIC / EV/EBITDA
    irr_density: Optional[float]  # IRR / hold_years
    value_creation: float       # (MOIC - 1) / hold_years
    size_bucket: str
    payer_regime: str


@dataclass
class DimEfficiency:
    dimension: str
    label: str
    n: int
    moic_eff_p50: Optional[float]
    moic_eff_p75: Optional[float]
    irr_density_p50: Optional[float]
    value_creation_p50: Optional[float]
    avg_ev_ebitda: Optional[float]
    avg_moic: Optional[float]


@dataclass
class CapitalEfficiencyResult:
    total_deals: int
    deals: List[DealEfficiency]
    by_sector: List[DimEfficiency]
    by_size: List[DimEfficiency]
    by_payer_regime: List[DimEfficiency]
    by_vintage: List[DimEfficiency]
    # Top / bottom performers
    top_moic_eff: List[DealEfficiency]
    bottom_moic_eff: List[DealEfficiency]
    # Corpus-wide stats
    corpus_moic_eff_p50: Optional[float]
    corpus_value_creation_p50: Optional[float]


def _build_dim(deals: List[DealEfficiency], dimension: str, label: str) -> DimEfficiency:
    moic_effs = sorted([d.moic_efficiency for d in deals])
    irr_dens = sorted([d.irr_density for d in deals if d.irr_density is not None])
    vcs = sorted([d.value_creation for d in deals])
    ee_vals = [d.ev_ebitda for d in deals if d.ev_ebitda is not None]
    moics = [d.moic for d in deals]
    return DimEfficiency(
        dimension=dimension,
        label=label,
        n=len(deals),
        moic_eff_p50=_percentile(moic_effs, 0.50),
        moic_eff_p75=_percentile(moic_effs, 0.75),
        irr_density_p50=_percentile(irr_dens, 0.50),
        value_creation_p50=_percentile(vcs, 0.50),
        avg_ev_ebitda=round(sum(ee_vals) / len(ee_vals), 2) if ee_vals else None,
        avg_moic=round(sum(moics) / len(moics), 3) if moics else None,
    )


def compute_capital_efficiency(
    min_n: int = 3,
) -> CapitalEfficiencyResult:
    corpus = _load_corpus()

    deal_effs: List[DealEfficiency] = []
    for d in corpus:
        m = _moic(d)
        h = _hold(d)
        if m is None or h is None or h <= 0:
            continue
        ee = _ev_ebitda(d)
        r = _irr(d)
        ev = _ev(d)
        moic_eff = round(m / ee, 4) if ee and ee > 0 else round(m / 10.0, 4)
        irr_density = round(r / h, 4) if r is not None else None
        vc = round((m - 1) / h, 4)
        deal_effs.append(DealEfficiency(
            source_id=d.get("source_id", ""),
            company_name=d.get("company_name") or d.get("deal_name") or "",
            sector=(d.get("sector") or "Unknown").strip(),
            year=int(d["year"]) if d.get("year") else 0,
            ev_mm=ev,
            ev_ebitda=ee,
            moic=m,
            irr=r,
            hold_years=h,
            moic_efficiency=moic_eff,
            irr_density=irr_density,
            value_creation=vc,
            size_bucket=_size_bucket(ev) if ev else "Unknown",
            payer_regime=_payer_regime(d),
        ))

    from collections import defaultdict

    # By sector
    by_sec: Dict[str, List[DealEfficiency]] = defaultdict(list)
    for de in deal_effs:
        by_sec[de.sector].append(de)
    sector_dims = sorted(
        [_build_dim(v, "sector", k) for k, v in by_sec.items() if len(v) >= min_n],
        key=lambda d: -(d.moic_eff_p50 or 0),
    )

    # By size
    by_size: Dict[str, List[DealEfficiency]] = defaultdict(list)
    for de in deal_effs:
        by_size[de.size_bucket].append(de)
    size_order = ["<$100M", "$100–300M", "$300–750M", "$750M–2B", ">$2B"]
    size_dims = [
        _build_dim(v, "size", k)
        for k in size_order
        for v in [by_size.get(k, [])]
        if len(v) >= min_n
    ]

    # By payer regime
    by_pr: Dict[str, List[DealEfficiency]] = defaultdict(list)
    for de in deal_effs:
        by_pr[de.payer_regime].append(de)
    pr_dims = sorted(
        [_build_dim(v, "payer_regime", k) for k, v in by_pr.items() if len(v) >= min_n],
        key=lambda d: -(d.moic_eff_p50 or 0),
    )

    # By vintage (5-year buckets)
    def _vint(yr: int) -> str:
        if yr < 2014:
            return "Pre-2014"
        if yr < 2017:
            return "2014–2016"
        if yr < 2020:
            return "2017–2019"
        return "2020–2022"

    by_vint: Dict[str, List[DealEfficiency]] = defaultdict(list)
    for de in deal_effs:
        by_vint[_vint(de.year)].append(de)
    vint_dims = [
        _build_dim(v, "vintage", k)
        for k in ["Pre-2014", "2014–2016", "2017–2019", "2020–2022"]
        for v in [by_vint.get(k, [])]
        if len(v) >= min_n
    ]

    # Top and bottom
    sorted_effs = sorted(deal_effs, key=lambda d: -d.moic_efficiency)
    top_10 = sorted_effs[:10]
    bottom_10 = sorted_effs[-10:][::-1]

    all_me = sorted([d.moic_efficiency for d in deal_effs])
    all_vc = sorted([d.value_creation for d in deal_effs])

    return CapitalEfficiencyResult(
        total_deals=len(deal_effs),
        deals=deal_effs,
        by_sector=sector_dims,
        by_size=size_dims,
        by_payer_regime=pr_dims,
        by_vintage=vint_dims,
        top_moic_eff=top_10,
        bottom_moic_eff=bottom_10,
        corpus_moic_eff_p50=_percentile(all_me, 0.50),
        corpus_value_creation_p50=_percentile(all_vc, 0.50),
    )
