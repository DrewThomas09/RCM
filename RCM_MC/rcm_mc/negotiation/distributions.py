"""Rate distributions per service-line × payer × geography.

The existing simulator surface returns rates at the (NPI × code)
level — useful for one-deal bargaining, but the user-level
question for antitrust filings, payer-mix analyses, and the LP
deck cover slide is the AGGREGATE distribution: "what's the
median in-network rate for orthopedic surgery (service line)
across BCBS Texas (payer) in the Houston CBSA (geo)?"

This module aggregates the pricing_payer_rates table along those
three axes and returns p25/p50/p75 + payer counts + n.

Geography axis: CBSA via the NPPES table when both are loaded
(NPI → state → CBSA via the stored cbsa column). When NPPES isn't
available the geography axis collapses to "ALL" and we still
return per-(service_line, payer) distributions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class RateDistribution:
    """One bucket of negotiated rates with summary statistics."""
    service_line: str
    payer_name: str
    cbsa: str
    n_rates: int
    n_npis: int
    p25: float
    p50: float
    p75: float
    mean: float
    min: float
    max: float


def _percentile(values: List[float], q: float) -> float:
    """Linear-interpolation percentile, numpy-default semantics."""
    if not values:
        return 0.0
    return float(np.percentile(values, q))


def aggregate_rate_distributions(
    pricing_store: Any,
    *,
    service_line: Optional[str] = None,
    payer_name: Optional[str] = None,
    cbsa: Optional[str] = None,
    min_bucket_size: int = 3,
) -> List[RateDistribution]:
    """Aggregate negotiated rates from pricing_payer_rates by
    (service_line, payer_name, cbsa).

    Optional filters narrow the result set. ``min_bucket_size``
    drops buckets with fewer than N rates so reporters don't
    over-interpret thin samples.

    The cbsa axis is populated via the NPPES join when the
    pricing_nppes table has the matching NPI; missing → "ALL".
    """
    # Pull all the rate rows + their NPIs
    sql = ("SELECT pr.payer_name, pr.npi, pr.code, "
           "       pr.code_type, pr.negotiated_rate, "
           "       pr.service_line "
           "FROM pricing_payer_rates pr "
           "WHERE pr.negotiated_rate IS NOT NULL")
    params: List[Any] = []
    if service_line:
        sql += " AND pr.service_line = ?"
        params.append(service_line)
    if payer_name:
        sql += " AND pr.payer_name = ?"
        params.append(payer_name)

    with pricing_store.connect() as con:
        rows = con.execute(sql, params).fetchall()

    if not rows:
        return []

    # Build NPI → CBSA crosswalk via NPPES (best-effort).
    npis = {r["npi"] for r in rows if r["npi"]}
    npi_to_cbsa: Dict[str, str] = {}
    if npis:
        with pricing_store.connect() as con:
            for npi in npis:
                rec = con.execute(
                    "SELECT cbsa FROM pricing_nppes WHERE npi = ?",
                    (npi,),
                ).fetchone()
                if rec and rec["cbsa"]:
                    npi_to_cbsa[npi] = rec["cbsa"]

    # Bucket: (service_line, payer_name, cbsa) → list of (rate, npi)
    buckets: Dict[Tuple[str, str, str], List[Tuple[float, str]]] = {}
    for r in rows:
        sl = r["service_line"] or "Other"
        pn = r["payer_name"] or "Unknown"
        c = npi_to_cbsa.get(r["npi"], "ALL")
        if cbsa and c != cbsa:
            continue
        key = (sl, pn, c)
        buckets.setdefault(key, []).append(
            (float(r["negotiated_rate"]), r["npi"]))

    out: List[RateDistribution] = []
    for (sl, pn, c), entries in buckets.items():
        if len(entries) < min_bucket_size:
            continue
        rates = [e[0] for e in entries]
        n_unique_npis = len({e[1] for e in entries if e[1]})
        out.append(RateDistribution(
            service_line=sl,
            payer_name=pn,
            cbsa=c,
            n_rates=len(rates),
            n_npis=n_unique_npis,
            p25=round(_percentile(rates, 25), 2),
            p50=round(_percentile(rates, 50), 2),
            p75=round(_percentile(rates, 75), 2),
            mean=round(float(np.mean(rates)), 2),
            min=round(float(np.min(rates)), 2),
            max=round(float(np.max(rates)), 2),
        ))
    # Stable order: service_line → payer → cbsa
    out.sort(key=lambda d: (d.service_line, d.payer_name, d.cbsa))
    return out


def cross_payer_dispersion(
    pricing_store: Any,
    code: str,
) -> Dict[str, Any]:
    """Cross-payer dispersion for a single billing code — the
    "one-page" antitrust exhibit.

    Returns:
        {
          "code": code,
          "n_payers": int,
          "n_npis": int,
          "p25": float, "p50": float, "p75": float,
          "max_min_ratio": float,    # max rate / min rate
          "by_payer": [{"payer_name": ..., "median_rate": ...}]
        }
    """
    with pricing_store.connect() as con:
        rows = con.execute(
            "SELECT payer_name, npi, negotiated_rate "
            "FROM pricing_payer_rates "
            "WHERE code = ? AND negotiated_rate IS NOT NULL",
            (str(code).strip(),),
        ).fetchall()
    if not rows:
        return {"code": code, "n_payers": 0, "n_npis": 0,
                "p25": 0.0, "p50": 0.0, "p75": 0.0,
                "max_min_ratio": 0.0, "by_payer": []}

    rates = [float(r["negotiated_rate"]) for r in rows]
    payers: Dict[str, List[float]] = {}
    for r in rows:
        payers.setdefault(r["payer_name"], []).append(
            float(r["negotiated_rate"]))

    by_payer = [
        {"payer_name": p,
         "median_rate": round(_percentile(rs, 50), 2),
         "n_rates": len(rs)}
        for p, rs in payers.items()
    ]
    by_payer.sort(key=lambda x: x["median_rate"])

    min_r = min(rates)
    max_r = max(rates)
    return {
        "code": str(code).strip(),
        "n_payers": len(payers),
        "n_npis": len({r["npi"] for r in rows if r["npi"]}),
        "p25": round(_percentile(rates, 25), 2),
        "p50": round(_percentile(rates, 50), 2),
        "p75": round(_percentile(rates, 75), 2),
        "max_min_ratio": round(max_r / max(0.01, min_r), 3),
        "by_payer": by_payer,
    }
