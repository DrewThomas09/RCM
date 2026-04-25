"""Outside-options computation — the surplus distribution that
anchors Nash bargaining.

For a given (provider NPI, billing code), an "outside option" is
the rate the provider could plausibly accept from a DIFFERENT
payer for the same service. The distribution of outside options
defines the negotiation space:

  • Provider's reservation price: 25th percentile of outside
    options (they could walk and accept this)
  • Payer's reservation price: 75th percentile of outside options
    (they could route the volume to an alternative provider that
     accepts this)
  • Surplus = payer_reservation − provider_reservation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any, Dict, List, Optional


@dataclass
class OutsideOptions:
    npi: str
    code: str
    payer_count: int = 0
    rate_count: int = 0
    rates: List[float] = field(default_factory=list)
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    surplus: float = 0.0


def _percentile(values: List[float], q: float) -> Optional[float]:
    """Linear-interpolation percentile (numpy default, type=7).
    Returns None on empty input."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def compute_outside_options(
    pricing_store: Any,
    npi: str,
    code: str,
    *,
    exclude_payer: Optional[str] = None,
) -> OutsideOptions:
    """Pull every negotiated rate for (NPI × code) from the
    pricing store and summarize as a percentile distribution.

    ``exclude_payer`` lets the caller compute the OUTSIDE options
    relative to a specific payer (i.e. drop that payer's own rate
    from the distribution).
    """
    from ..pricing import list_negotiated_rates_by_npi
    rows = list_negotiated_rates_by_npi(pricing_store, npi, code=code)
    rates: List[float] = []
    payers: set = set()
    for r in rows:
        if exclude_payer and r.get("payer_name") == exclude_payer:
            continue
        rate = r.get("negotiated_rate")
        if rate is None:
            continue
        try:
            rates.append(float(rate))
            payers.add(r.get("payer_name") or "")
        except (TypeError, ValueError):
            continue

    p25 = _percentile(rates, 0.25)
    p50 = _percentile(rates, 0.50)
    p75 = _percentile(rates, 0.75)
    surplus = (p75 - p25) if (p25 is not None and p75 is not None) else 0.0

    return OutsideOptions(
        npi=npi, code=code,
        payer_count=len(payers),
        rate_count=len(rates),
        rates=rates,
        p25=p25, p50=p50, p75=p75,
        surplus=round(surplus, 2),
    )
