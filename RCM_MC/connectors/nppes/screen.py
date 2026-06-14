"""Target screen — ranked acquisition long-list.

The synthesis deliverable: rather than reading six metric tables, a deal team
wants one ranked list of candidate organizations that fit a thesis. This
module scores every in-scope Type-2 organization on three CDD axes and ranks
them, with a transparent component breakdown so the score is defensible.

Axes (each normalized 0..1, weighted, summed to a 0..100 score):
  • **market_growth** — net provider growth of the org's (geography ×
    specialty) market over the recent window (a growing market lifts a
    platform).
  • **fragmentation** — the market's roll-up score (fragmented markets have
    consolidation runway).
  • **scale_fit** — how well the org's captive-provider footprint matches the
    thesis: ``platform`` rewards mid/large captive scale; ``addon`` rewards
    sub-scale independents.

Weights are explicit and overridable. Pure read-over-canonical; returns
ranked candidates with the component scores and a one-line rationale.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import cdd


def _norm(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _market_growth_ratios(
    store: Any, geo_level: str, recent_years: int
) -> Dict[tuple, float]:
    """Per (geo, classification): (recent new − recent deactivated) / total,
    a bounded net-growth ratio."""
    geo_c = cdd._geo_col(geo_level)
    enum_y = cdd._YEAR_EXPR.format(c="p.enumeration_date")
    deact_y = cdd._YEAR_EXPR.format(c="p.deactivation_date")
    sql = f"""
        WITH s AS (
            SELECT {geo_c} AS geo,
                   COALESCE(t.classification,'(unclassified)') AS classification,
                   {enum_y} AS ey,
                   CASE WHEN p.deactivation_date IS NOT NULL AND p.deactivation_date<>''
                        THEN {deact_y} ELSE NULL END AS dy
            FROM dim_provider p
            JOIN dim_provider_address a ON a.npi=p.npi AND a.address_purpose='practice'
            LEFT JOIN bridge_provider_taxonomy bt ON bt.npi=p.npi AND bt.primary_flag=1
            LEFT JOIN dim_taxonomy t ON t.taxonomy_code=bt.taxonomy_code
            WHERE {geo_c} IS NOT NULL AND {geo_c}<>''
        ),
        maxy AS (SELECT MAX(CAST(ey AS INTEGER)) my FROM s WHERE ey GLOB '[12][0-9][0-9][0-9]')
        SELECT geo, classification,
               COUNT(*) AS total,
               SUM(CASE WHEN ey GLOB '[12][0-9][0-9][0-9]'
                        AND CAST(ey AS INTEGER) >= (SELECT my FROM maxy)-? THEN 1 ELSE 0 END) AS recent_adds,
               SUM(CASE WHEN dy GLOB '[12][0-9][0-9][0-9]'
                        AND CAST(dy AS INTEGER) >= (SELECT my FROM maxy)-? THEN 1 ELSE 0 END) AS recent_deacts
        FROM s GROUP BY geo, classification
    """
    out: Dict[tuple, float] = {}
    with store.connect() as con:
        for r in con.execute(sql, (recent_years, recent_years)).fetchall():
            tot = r["total"] or 1
            out[(r["geo"], r["classification"])] = (
                (r["recent_adds"] - r["recent_deacts"]) / tot)
    return out


def screen_targets(
    store: Any, *, thesis: str = "platform", classification: Optional[str] = None,
    geo_level: str = "state", geo: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None, limit: int = 25,
) -> List[Dict[str, Any]]:
    """Rank in-scope Type-2 orgs into an acquisition long-list for ``thesis``
    ∈ {platform, addon}."""
    w = {"market_growth": 0.35, "fragmentation": 0.35, "scale_fit": 0.30}
    if weights:
        w.update(weights)

    growth = _market_growth_ratios(store, geo_level, recent_years=3)
    frag = {(f["geo"], f["classification"]): f
            for f in cdd.fragmentation_scan(store, geo_level=geo_level,
                                            classification=classification,
                                            min_providers=1, limit=100000)}
    geo_c = cdd._geo_col(geo_level)
    args: List[Any] = []
    where = ["p.entity_type=2", "p.status='active'"]
    join_taxo = (" LEFT JOIN bridge_provider_taxonomy bt ON bt.npi=p.npi AND bt.primary_flag=1"
                 " LEFT JOIN dim_taxonomy t ON t.taxonomy_code=bt.taxonomy_code")
    if classification:
        where.append("t.classification = ?"); args.append(classification)
    if geo:
        where.append(f"{geo_c} = ?"); args.append(geo)
    wsql = " AND ".join(where)
    sql = f"""
        SELECT p.npi, p.organization_name, {geo_c} AS geo,
               COALESCE(t.classification,'(unclassified)') AS classification,
               COALESCE(fc.captive,0) AS captive
        FROM dim_provider p
        JOIN dim_provider_address a ON a.npi=p.npi AND a.address_purpose='practice'
        {join_taxo}
        LEFT JOIN (SELECT organization_npi, COUNT(DISTINCT individual_npi) captive
                   FROM bridge_provider_affiliation GROUP BY organization_npi) fc
             ON fc.organization_npi=p.npi
        WHERE {wsql}
    """
    with store.connect() as con:
        orgs = con.execute(sql, args).fetchall()

    # normalization bounds from the candidate pool
    growth_vals = list(growth.values()) or [0.0]
    g_lo, g_hi = min(growth_vals), max(growth_vals)
    frag_vals = [f["rollup_score"] for f in frag.values()] or [0.0]
    f_lo, f_hi = min(frag_vals), max(frag_vals)
    captives = [o["captive"] for o in orgs] or [0]
    c_hi = max(captives) or 1

    scored = []
    for o in orgs:
        key = (o["geo"], o["classification"])
        mg = _norm(growth.get(key, 0.0), g_lo, g_hi)
        fr = _norm(frag[key]["rollup_score"], f_lo, f_hi) if key in frag else 0.0
        cap_norm = o["captive"] / c_hi
        if thesis == "addon":
            scale = 1.0 - cap_norm           # reward sub-scale independents
        else:                                 # platform
            scale = cap_norm                  # reward captive scale
        score = 100 * (w["market_growth"] * mg + w["fragmentation"] * fr +
                       w["scale_fit"] * scale)
        rationale = (f"{thesis}: market_growth={mg:.2f}, fragmentation={fr:.2f}, "
                     f"scale_fit={scale:.2f} (captive={o['captive']})")
        scored.append({
            "npi": o["npi"], "organization_name": o["organization_name"],
            "geo": o["geo"], "classification": o["classification"],
            "captive_providers": o["captive"],
            "score": round(score, 1),
            "components": {"market_growth": round(mg, 3),
                           "fragmentation": round(fr, 3),
                           "scale_fit": round(scale, 3)},
            "rationale": rationale,
        })
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:limit]
