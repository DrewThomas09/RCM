"""Read helpers — the consumer surface for downstream packets.

Downstream code (PayerNegotiationSimulator, ReferralNetworkPacket,
BuyAndBuildOptimizer, ESG packet, VBC-ContractValuator) calls these
helpers — they should never query the pricing tables directly. The
helpers encapsulate the canonical query patterns:

  • point lookup of an organization NPI
  • all charges for a given service code (across hospitals)
  • all negotiated rates for an NPI (the simulator's outside-options
    query)
  • all negotiated rates for a service code (cross-payer dispersion
    used to anchor Nash bargaining)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_provider_npi(
    store: Any, npi: str,
) -> Optional[Dict[str, Any]]:
    """Lookup a single organizational NPI from the NPPES table."""
    if not npi:
        return None
    with store.connect() as con:
        row = con.execute(
            "SELECT * FROM pricing_nppes WHERE npi = ?",
            (str(npi).strip(),),
        ).fetchone()
    return dict(row) if row else None


def list_charges_by_code(
    store: Any, code: str,
    *, payer_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Hospital-MRF charges for a given normalized code, optionally
    filtered to one payer. Returns a list of dicts (one per
    hospital × payer plan)."""
    if not code:
        return []
    sql = ("SELECT * FROM pricing_hospital_charges "
           "WHERE code = ?")
    params: List[Any] = [str(code).strip()]
    if payer_name:
        sql += " AND payer_name = ?"
        params.append(payer_name)
    sql += " ORDER BY ccn, payer_name, plan_name"
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_negotiated_rates_by_npi(
    store: Any, npi: str,
    *, code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Every payer-side negotiated rate associated with a billing
    NPI. Used by the negotiation simulator as the provider's
    'outside options' set — i.e. what other payers pay this same
    provider for the same service."""
    if not npi:
        return []
    sql = ("SELECT * FROM pricing_payer_rates "
           "WHERE npi = ?")
    params: List[Any] = [str(npi).strip()]
    if code:
        sql += " AND code = ?"
        params.append(code)
    sql += " ORDER BY payer_name, plan_name, code"
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_negotiated_rates_for_code(
    store: Any, code: str,
    *, service_line: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Every negotiated rate published for a service code across
    all payer plans. Drives the cross-payer dispersion calculation
    that anchors the simulator's Nash bargaining surplus split."""
    if not code:
        return []
    sql = ("SELECT * FROM pricing_payer_rates "
           "WHERE code = ?")
    params: List[Any] = [str(code).strip()]
    if service_line:
        sql += " AND service_line = ?"
        params.append(service_line)
    sql += " ORDER BY payer_name, npi"
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
