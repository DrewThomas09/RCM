"""Diligence market maps over the canonical openFDA tables.

The source spec calls out specific signals worth preserving; this module
turns the normalized tables into the four that matter for a deal, all as
cheap SQL aggregates (no extra openFDA round-trips — the expensive pulls
already happened at ingest):

  * **Device clearance timeline by product_code** — competitive-entry /
    margin-compression signal: clearances per product_code per year.
  * **Competitive entry by product_code** — distinct applicants
    (companies) plus first/last decision dates; more entrants ⇒ more
    margin pressure.
  * **MAUDE safety intensity** — adverse-event counts per product_code
    normalized by approximate units in market (UDI records as the proxy
    denominator): the safety-liability signal.
  * **Drug risk by NDC** — FAERS adverse-event + recall counts keyed to
    NDC: the drug-risk signal.

Each returns plain list-of-dicts so the CLI, a notebook, or a UI surface
can render them directly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .tables import OpenFdaStore


def clearance_timeline_by_product_code(
    store: OpenFdaStore, *, product_code: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Clearances per product_code per decision year (510k + PMA).

    ``decision_date`` is ``YYYY-MM-DD`` for device endpoints, so the year
    is the first four chars. Classification rows (no decision date) are
    excluded.
    """
    where = "decision_date IS NOT NULL AND decision_date <> ''"
    args: List[Any] = []
    if product_code:
        where += " AND product_code = ?"
        args.append(str(product_code).upper())
    sql = (f"SELECT product_code, substr(decision_date, 1, 4) AS year, "
           f"COUNT(*) AS clearances, COUNT(DISTINCT company_key) AS applicants "
           f"FROM dim_device WHERE {where} "
           f"GROUP BY product_code, year ORDER BY product_code, year LIMIT ?")
    return [dict(r) for r in store.fetchall(sql, (*args, int(limit)))]


def competitive_entry_by_product_code(
    store: OpenFdaStore, *, min_clearances: int = 1, limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Per product_code: distinct applicants + decision-date span.

    The competitive-entry read: a product_code many distinct companies
    have cleared into is a crowded, margin-compressed niche.
    """
    sql = (
        "SELECT product_code, "
        "COUNT(*) AS clearances, "
        "COUNT(DISTINCT company_key) AS distinct_applicants, "
        "MIN(decision_date) AS first_decision, "
        "MAX(decision_date) AS last_decision "
        "FROM dim_device "
        "WHERE decision_date IS NOT NULL AND decision_date <> '' "
        "AND product_code IS NOT NULL AND product_code <> '' "
        "GROUP BY product_code HAVING clearances >= ? "
        "ORDER BY distinct_applicants DESC, clearances DESC LIMIT ?")
    return [dict(r) for r in store.fetchall(sql, (int(min_clearances), int(limit)))]


def maude_safety_intensity(
    store: OpenFdaStore, *, limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Per product_code: MAUDE event count, UDI count, events-per-UDI.

    ``events_per_udi`` normalizes raw MAUDE volume by approximate units
    in market (distinct UDI records as the proxy denominator) so a
    high-volume product code isn't automatically flagged as high-risk.
    Product codes with no UDI denominator report ``None`` (uncomparable).
    """
    events = _counts(store, "fact_device_adverse_event", "product_code")
    udis = _counts(store, "dim_device_udi", "product_code")
    out: List[Dict[str, Any]] = []
    for pcode, ev in events.items():
        udi = udis.get(pcode, 0)
        out.append({
            "product_code": pcode,
            "maude_events": ev,
            "udi_units": udi,
            "events_per_udi": round(ev / udi, 4) if udi else None,
        })
    # Most events first; uncomparable (no UDI) sink to the bottom of ties.
    out.sort(key=lambda r: (r["events_per_udi"] is None, -(r["events_per_udi"] or 0),
                            -r["maude_events"]))
    return out[:int(limit)]


def drug_risk_by_ndc(
    store: OpenFdaStore, *, limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Per NDC: FAERS adverse-event count + recall count (drug-risk map)."""
    faers = _counts(store, "fact_drug_adverse_event", "ndc")
    recalls = _counts(store, "fact_drug_recall", "ndc")
    ndcs = set(faers) | set(recalls)
    out = [{
        "ndc": ndc,
        "faers_events": faers.get(ndc, 0),
        "recalls": recalls.get(ndc, 0),
        "risk_signal": faers.get(ndc, 0) + 5 * recalls.get(ndc, 0),  # recalls weigh more
    } for ndc in ndcs]
    out.sort(key=lambda r: -r["risk_signal"])
    return out[:int(limit)]


def _counts(store: OpenFdaStore, table: str, col: str) -> Dict[str, int]:
    sql = (f"SELECT {col} AS k, COUNT(*) AS n FROM {table} "
           f"WHERE {col} IS NOT NULL AND {col} <> '' GROUP BY {col}")
    return {str(r["k"]): int(r["n"]) for r in store.fetchall(sql)}


MARKET_MAPS = {
    "clearance_timeline": clearance_timeline_by_product_code,
    "competitive_entry": competitive_entry_by_product_code,
    "maude_intensity": maude_safety_intensity,
    "drug_risk": drug_risk_by_ndc,
}
