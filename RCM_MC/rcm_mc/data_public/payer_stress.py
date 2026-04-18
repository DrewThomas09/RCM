"""Payer Mix Stress Tester — corpus-calibrated payer-shift MOIC impact.

Estimates MOIC sensitivity to payer mix changes: what happens to expected
returns if commercial payer share drops X%, or Medicare rates are cut Y%?
Uses a simple linear regression on corpus peer data to quantify the impact.
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 43):
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


def _comm_pct(d: Dict[str, Any]) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        for k in ("commercial", "comm"):
            v = pm.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return None


def _medicare_pct(d: Dict[str, Any]) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        for k in ("medicare", "mcare"):
            v = pm.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return None


def _medicaid_pct(d: Dict[str, Any]) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        for k in ("medicaid", "mcaid"):
            v = pm.get(k)
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
    return round(s[idx], 3)


def _linear_regression(
    xs: List[float], ys: List[float]
) -> Tuple[float, float, float]:
    """Return (slope, intercept, r2)."""
    n = len(xs)
    if n < 3:
        return 0.0, 0.0, 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_yy = sum((y - mean_y) ** 2 for y in ys)
    if ss_xx < 1e-10:
        return 0.0, mean_y, 0.0
    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    r2 = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 1e-10 else 0.0
    return round(slope, 4), round(intercept, 4), round(r2, 4)


@dataclass
class PayerReg:
    """Regression of one payer % vs MOIC from corpus data."""
    payer: str
    slope: float
    intercept: float
    r2: float
    n: int
    moic_p50: Optional[float]
    moic_per_10pct: float  # MOIC change per 10pp shift in this payer


@dataclass
class StressScenario:
    label: str
    description: str
    delta_comm: float    # change in commercial share (e.g. -0.10 = -10pp)
    delta_mcare: float
    delta_mcaid: float
    base_moic: float
    stressed_moic: float
    moic_delta: float
    pct_impact: float    # % change from base


@dataclass
class PayerStressResult:
    base_comm: float
    base_mcare: float
    base_mcaid: float
    base_moic_estimate: float
    comm_reg: PayerReg
    mcare_reg: PayerReg
    mcaid_reg: PayerReg
    scenarios: List[StressScenario]
    n_corpus_peers: int
    corpus_p50: Optional[float]
    sector_filter: str


def compute_payer_stress(
    base_comm: float = 0.60,
    base_mcare: float = 0.25,
    base_mcaid: float = 0.10,
    sector: str = "",
    ev_mm: Optional[float] = None,
) -> PayerStressResult:
    corpus = _load_corpus()

    # Filter to sector and EV range if provided
    peers = []
    for d in corpus:
        if _moic(d) is None:
            continue
        if sector:
            deal_sector = (d.get("sector") or "").lower()
            query_words = set(sector.lower().split())
            sector_words = set(deal_sector.split())
            if not (query_words & sector_words or sector.lower() in deal_sector):
                continue
        if ev_mm:
            d_ev = d.get("ev_mm")
            if d_ev and not (float(ev_mm) * 0.3 <= float(d_ev) <= float(ev_mm) * 3.0):
                continue
        peers.append(d)

    # Fallback to all corpus if too few peers
    if len(peers) < 20:
        peers = [d for d in corpus if _moic(d) is not None]

    # Regression of each payer vs MOIC
    def _build_reg(payer_fn, payer_label) -> PayerReg:
        pairs = [
            (payer_fn(d), _moic(d))
            for d in peers
            if payer_fn(d) is not None and _moic(d) is not None
        ]
        if not pairs:
            return PayerReg(payer_label, 0.0, 2.5, 0.0, 0, None, 0.0)
        xs, ys = zip(*pairs)
        slope, intercept, r2 = _linear_regression(list(xs), list(ys))
        moics = sorted(ys)
        return PayerReg(
            payer=payer_label,
            slope=slope,
            intercept=intercept,
            r2=r2,
            n=len(pairs),
            moic_p50=_percentile(moics, 0.50),
            moic_per_10pct=round(slope * 0.10, 4),
        )

    comm_reg = _build_reg(_comm_pct, "Commercial")
    mcare_reg = _build_reg(_medicare_pct, "Medicare")
    mcaid_reg = _build_reg(_medicaid_pct, "Medicaid")

    # Blend the regressions to estimate base MOIC
    all_moics = sorted([_moic(d) for d in peers if _moic(d) is not None])
    corpus_p50 = _percentile(all_moics, 0.50) or 2.5

    # Weighted blend of individual predictions
    def _predict(c: float, m: float, mc: float) -> float:
        pred_c = comm_reg.slope * c + comm_reg.intercept if comm_reg.r2 > 0.01 else corpus_p50
        pred_m = mcare_reg.slope * m + mcare_reg.intercept if mcare_reg.r2 > 0.01 else corpus_p50
        pred_mc = mcaid_reg.slope * mc + mcaid_reg.intercept if mcaid_reg.r2 > 0.01 else corpus_p50
        # Weight by R²
        total_r2 = comm_reg.r2 + mcare_reg.r2 + mcaid_reg.r2
        if total_r2 < 0.01:
            return corpus_p50
        wc = comm_reg.r2 / total_r2
        wm = mcare_reg.r2 / total_r2
        wmc = mcaid_reg.r2 / total_r2
        return round(pred_c * wc + pred_m * wm + pred_mc * wmc, 3)

    base_moic = _predict(base_comm, base_mcare, base_mcaid)

    def _scenario(
        label: str,
        desc: str,
        dc: float,
        dm: float,
        dmc: float,
    ) -> StressScenario:
        sc = _predict(
            max(0.0, min(1.0, base_comm + dc)),
            max(0.0, min(1.0, base_mcare + dm)),
            max(0.0, min(1.0, base_mcaid + dmc)),
        )
        delta = round(sc - base_moic, 3)
        pct = round((sc / base_moic - 1) * 100, 1) if base_moic else 0.0
        return StressScenario(
            label=label,
            description=desc,
            delta_comm=dc,
            delta_mcare=dm,
            delta_mcaid=dmc,
            base_moic=base_moic,
            stressed_moic=sc,
            moic_delta=delta,
            pct_impact=pct,
        )

    scenarios = [
        _scenario("Base", "Current payer mix", 0, 0, 0),
        _scenario(
            "Comm −10pp",
            "One large commercial contract lost or re-priced",
            -0.10, +0.05, +0.05,
        ),
        _scenario(
            "Comm −20pp",
            "Significant commercial contract churn or MA conversion",
            -0.20, +0.10, +0.10,
        ),
        _scenario(
            "Medicare +10pp",
            "Aging demographics shift, MA conversion, site-of-care change",
            -0.10, +0.10, 0,
        ),
        _scenario(
            "Medicare −5% rate",
            "CMS IPPS/OPPS final rule rate reduction (approximated as -5pp effect)",
            0, -0.05, 0,
        ),
        _scenario(
            "Medicaid +15pp",
            "Program expansion, Medicaid managed care growth",
            -0.15, 0, +0.15,
        ),
        _scenario(
            "Gov-heavy shift",
            "Combined Medicare +10pp, Medicaid +10pp, commercial −20pp",
            -0.20, +0.10, +0.10,
        ),
        _scenario(
            "Comm +10pp",
            "New commercial contract wins, better in-network coverage",
            +0.10, -0.05, -0.05,
        ),
    ]

    return PayerStressResult(
        base_comm=base_comm,
        base_mcare=base_mcare,
        base_mcaid=base_mcaid,
        base_moic_estimate=base_moic,
        comm_reg=comm_reg,
        mcare_reg=mcare_reg,
        mcaid_reg=mcaid_reg,
        scenarios=scenarios,
        n_corpus_peers=len(peers),
        corpus_p50=corpus_p50,
        sector_filter=sector,
    )
