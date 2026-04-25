"""Payer contract strength estimator.

Given the TiC payer MRF data already ingested into
``pricing_payer_rates`` plus the NPPES Type-2 registry, estimate
how a target hospital's negotiated rates compare to the market —
specifically: for each (payer × CPT) the hospital negotiates,
where does its rate sit in the distribution of every other
NPI in the same state's negotiated rates?

Why this matters:

  • TiC publishes contracted rates by NPI, not by hospital. A
    Type-2 hospital NPI may negotiate above-market on imaging
    but below-market on surgery; the partner needs the
    decomposition, not just an average.
  • An above-market hospital is likely to give back rates in a
    rate-reset cycle — exit-thesis risk. A below-market hospital
    is rate-uplift opportunity (the value-creation thesis).
  • Volume-weighting matters. Out-performing on a low-volume
    code doesn't move the EBITDA needle; out-performing on a
    high-volume code does.

Output:
  • Overall strength: volume-weighted geometric mean of
    (hospital_rate / market_p50) across services. >1.0 = above
    market, <1.0 = below.
  • Per-payer breakdown: which payers does this hospital
    out-/under-negotiate?
  • Per-service-line: same decomposition by HCUP / OPPS service
    line classifier.
  • Top variances: the 5 codes furthest above and below market
    — partner uses these to direct rate-negotiation work.
  • Dispersion: how variable is the hospital's pricing relative
    to market? High dispersion = inconsistent contracts (often
    a clue that one vendor is ramming through aggressive rates
    while others lag).

Public API::

    from rcm_mc.ml.contract_strength import (
        MarketReferenceRates,
        ContractStrengthScore,
        compute_market_reference_rates,
        compute_contract_strength,
    )
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Strength bands the partner cares about. >1.10 = >10% above
# market = strong contracts (exit-cycle risk); <0.90 = >10%
# below = uplift opportunity.
STRENGTH_BANDS: List[Tuple[float, str]] = [
    (0.85, "very_weak"),
    (0.95, "weak"),
    (1.05, "market"),
    (1.15, "strong"),
    (10.0, "very_strong"),
]


@dataclass
class MarketReferenceRates:
    """Per (payer, code) reference rate distribution within a
    geographic market (state by default).

    rates_by_pair[(payer, code)] = {
        "p25": float, "p50": float, "p75": float, "n": int,
    }
    """
    rates_by_pair: Dict[
        Tuple[str, str], Dict[str, float]] = field(
            default_factory=dict)
    state: Optional[str] = None


@dataclass
class CodeComparison:
    """One (payer × code) comparison row."""
    payer_name: str
    code: str
    code_type: str
    service_line: Optional[str]
    hospital_rate: float
    market_p50: float
    market_p25: float
    market_p75: float
    market_n: int
    rate_ratio: float          # hospital_rate / market_p50
    weight: float              # volume weight; 1.0 if equal


@dataclass
class ContractStrengthScore:
    """Full estimator output for one NPI."""
    npi: str
    state: Optional[str]
    n_codes_compared: int
    n_payers_compared: int
    overall_strength: float          # geo-mean ratio; 1.0 = market
    overall_band: str                # 'weak' / 'market' / 'strong'
    pct_above_market: float          # share of codes >5% above p50
    pct_below_market: float          # share of codes >5% below p50
    dispersion: float                # std of log ratios
    by_payer: Dict[str, float] = field(default_factory=dict)
    by_service_line: Dict[
        str, float] = field(default_factory=dict)
    top_above_market: List[
        CodeComparison] = field(default_factory=list)
    top_below_market: List[
        CodeComparison] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────

def _percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    n = len(vs)
    if n == 1:
        return vs[0]
    k = (n - 1) * q
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vs[int(k)]
    return vs[f] * (c - k) + vs[c] * (k - f)


def _band_for_strength(strength: float) -> str:
    for thresh, label in STRENGTH_BANDS:
        if strength < thresh:
            return label
    return STRENGTH_BANDS[-1][1]


# ── Market reference rates ────────────────────────────────────

def compute_market_reference_rates(
    store: Any,
    *,
    state: Optional[str] = None,
    payer_name: Optional[str] = None,
    min_providers: int = 3,
) -> MarketReferenceRates:
    """Build the (payer, code) → percentile lookup.

    Args:
      store: PortfolioStore-shaped handle.
      state: when set, restrict the reference set to NPIs in this
        state (state of practice from NPPES).
      payer_name: optional filter on a single payer.
      min_providers: drop (payer, code) pairs with fewer than
        ``min_providers`` distinct NPIs — not statistically useful.

    Returns: MarketReferenceRates keyed by (payer, code).
    """
    sql = (
        "SELECT r.payer_name AS payer_name, "
        "       r.code AS code, "
        "       r.npi AS npi, "
        "       r.negotiated_rate AS rate "
        "FROM pricing_payer_rates r "
    )
    params: List[Any] = []
    where_parts: List[str] = [
        "r.negotiated_rate IS NOT NULL",
        "r.negotiated_rate > 0",
    ]
    if state:
        sql += "JOIN pricing_nppes n ON r.npi = n.npi "
        where_parts.append("UPPER(n.state) = ?")
        params.append(state.upper())
    if payer_name:
        where_parts.append("r.payer_name = ?")
        params.append(payer_name)
    sql += "WHERE " + " AND ".join(where_parts)

    bucket: Dict[
        Tuple[str, str], Dict[str, List[float]]] = (
        defaultdict(lambda: {"rates": [], "npis": []}))
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    for row in rows:
        d = dict(row)
        key = (d["payer_name"], d["code"])
        bucket[key]["rates"].append(float(d["rate"]))
        bucket[key]["npis"].append(d["npi"])

    out: Dict[Tuple[str, str], Dict[str, float]] = {}
    for key, vals in bucket.items():
        unique_npis = len(set(vals["npis"]))
        if unique_npis < min_providers:
            continue
        rates = vals["rates"]
        out[key] = {
            "p25": _percentile(rates, 0.25),
            "p50": _percentile(rates, 0.50),
            "p75": _percentile(rates, 0.75),
            "n": unique_npis,
        }
    return MarketReferenceRates(
        rates_by_pair=out, state=state)


# ── Contract strength scoring ────────────────────────────────

def compute_contract_strength(
    store: Any,
    npi: str,
    *,
    state: Optional[str] = None,
    code_volumes: Optional[Dict[str, float]] = None,
    reference: Optional[MarketReferenceRates] = None,
    min_codes: int = 5,
    top_k: int = 5,
) -> Optional[ContractStrengthScore]:
    """Score one NPI's negotiated rates vs market.

    Args:
      store: PortfolioStore handle.
      npi: target hospital's billing NPI (Type-2 typically).
      state: market for the reference set. If None, falls back to
        the NPI's NPPES-recorded state.
      code_volumes: optional {code: volume} dict for volume-
        weighted scoring. Without it, every code weights equally.
      reference: pre-computed MarketReferenceRates; if None,
        computed at call time.
      min_codes: refuse to score with fewer than this many
        comparable (payer × code) pairs — partner can't trust a
        2-code average. Returns None when below threshold.
      top_k: how many top-above and top-below codes to surface.

    Returns: ContractStrengthScore or None when min_codes not met.
    """
    if not npi:
        return None

    # Resolve state if not given
    if state is None:
        with store.connect() as con:
            row = con.execute(
                "SELECT state FROM pricing_nppes "
                "WHERE npi = ? LIMIT 1",
                (str(npi).strip(),)).fetchone()
        if row and row["state"]:
            state = str(row["state"]).upper()

    if reference is None:
        reference = compute_market_reference_rates(
            store, state=state)

    # Pull this NPI's rates
    with store.connect() as con:
        own_rows = con.execute(
            "SELECT payer_name, code, code_type, "
            "       service_line, negotiated_rate "
            "FROM pricing_payer_rates "
            "WHERE npi = ? "
            "  AND negotiated_rate IS NOT NULL "
            "  AND negotiated_rate > 0",
            (str(npi).strip(),)).fetchall()

    comps: List[CodeComparison] = []
    for r in own_rows:
        d = dict(r)
        key = (d["payer_name"], d["code"])
        ref = reference.rates_by_pair.get(key)
        if not ref:
            continue
        p50 = ref["p50"]
        if p50 <= 0:
            continue
        rate = float(d["negotiated_rate"])
        ratio = rate / p50
        weight = ((code_volumes or {}).get(d["code"], 1.0)
                  if code_volumes else 1.0)
        comps.append(CodeComparison(
            payer_name=d["payer_name"],
            code=d["code"],
            code_type=d["code_type"],
            service_line=d.get("service_line"),
            hospital_rate=rate,
            market_p50=p50,
            market_p25=ref["p25"],
            market_p75=ref["p75"],
            market_n=int(ref["n"]),
            rate_ratio=ratio,
            weight=weight,
        ))

    if len(comps) < min_codes:
        return None

    # Volume-weighted geometric mean of ratios
    log_ratios = [math.log(c.rate_ratio) for c in comps]
    weights = [c.weight for c in comps]
    total_w = sum(weights)
    if total_w <= 0:
        return None
    weighted_log = (
        sum(lr * w for lr, w in zip(log_ratios, weights))
        / total_w)
    overall = math.exp(weighted_log)

    # Above / below market shares
    above = sum(1 for c in comps if c.rate_ratio > 1.05)
    below = sum(1 for c in comps if c.rate_ratio < 0.95)
    n = len(comps)
    pct_above = above / n
    pct_below = below / n

    # Dispersion: weighted std of log ratios
    weighted_var = (
        sum(w * (lr - weighted_log) ** 2
            for lr, w in zip(log_ratios, weights))
        / total_w)
    dispersion = math.sqrt(weighted_var)

    # Per-payer breakdown
    by_payer_logs: Dict[str, List[Tuple[float, float]]] = (
        defaultdict(list))
    for c in comps:
        by_payer_logs[c.payer_name].append(
            (math.log(c.rate_ratio), c.weight))
    by_payer = {}
    for payer, items in by_payer_logs.items():
        tw = sum(w for _, w in items)
        if tw > 0:
            wm = sum(lr * w for lr, w in items) / tw
            by_payer[payer] = round(math.exp(wm), 4)

    # Per-service-line breakdown
    by_sl_logs: Dict[str, List[Tuple[float, float]]] = (
        defaultdict(list))
    for c in comps:
        sl = c.service_line or "unclassified"
        by_sl_logs[sl].append(
            (math.log(c.rate_ratio), c.weight))
    by_sl = {}
    for sl, items in by_sl_logs.items():
        tw = sum(w for _, w in items)
        if tw > 0:
            wm = sum(lr * w for lr, w in items) / tw
            by_sl[sl] = round(math.exp(wm), 4)

    # Top variances
    sorted_above = sorted(
        comps, key=lambda c: -c.rate_ratio)[:top_k]
    sorted_below = sorted(
        comps, key=lambda c: c.rate_ratio)[:top_k]

    notes: List[str] = []
    if pct_above > 0.50:
        notes.append(
            f"{int(pct_above * 100)}% of contracts >5% above "
            f"market — exit-cycle rate-reset risk.")
    if pct_below > 0.50:
        notes.append(
            f"{int(pct_below * 100)}% of contracts >5% below "
            f"market — rate-uplift opportunity.")
    if dispersion > 0.30:
        notes.append(
            "High contract dispersion (σ > 0.30) — likely "
            "inconsistent vendor management.")

    return ContractStrengthScore(
        npi=str(npi).strip(),
        state=state,
        n_codes_compared=n,
        n_payers_compared=len({c.payer_name for c in comps}),
        overall_strength=round(overall, 4),
        overall_band=_band_for_strength(overall),
        pct_above_market=round(pct_above, 4),
        pct_below_market=round(pct_below, 4),
        dispersion=round(dispersion, 4),
        by_payer=by_payer,
        by_service_line=by_sl,
        top_above_market=sorted_above,
        top_below_market=sorted_below,
        notes=notes,
    )


def rank_hospitals_by_strength(
    store: Any,
    npis: Iterable[str],
    *,
    state: Optional[str] = None,
    code_volumes: Optional[Dict[str, float]] = None,
    min_codes: int = 5,
) -> List[ContractStrengthScore]:
    """Rank a set of hospitals by overall contract strength.

    Reuses one MarketReferenceRates build across all NPIs — the
    reference set is the same for every hospital in the same
    state. Skips NPIs that don't have enough comparable codes.
    """
    reference = compute_market_reference_rates(
        store, state=state)
    out: List[ContractStrengthScore] = []
    for npi in npis:
        score = compute_contract_strength(
            store, npi,
            state=state,
            code_volumes=code_volumes,
            reference=reference,
            min_codes=min_codes,
        )
        if score is not None:
            out.append(score)
    out.sort(key=lambda s: -s.overall_strength)
    return out
