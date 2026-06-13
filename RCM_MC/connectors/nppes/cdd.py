"""Commercial-due-diligence analytics over the NPPES canonical tables.

The dimensions (`dim_provider`, `bridge_provider_taxonomy`,
`dim_provider_address`, `bridge_provider_affiliation`) are the raw material;
this module turns them into the signals a CDD analyst actually asks for on a
healthcare-services target:

  • **TAM / market structure** — provider count by taxonomy × geography
    (the spine of sizing and white-space analysis).
  • **Market concentration (HHI)** — how consolidated a (geography ×
    specialty) market is, using each organization's captive-provider share
    as a revenue proxy, scored against the DOJ/FTC thresholds.
  • **Fragmentation / roll-up scan** — markets with many sub-scale
    independent organizations are platform/add-on hunting grounds.
  • **Roster integrity** — deactivation / reactivation rates, the
    terminated-provider risk to a target's revenue base.
  • **Affiliation footprint** — organizations ranked by captive provider
    count (a referral / captive-volume proxy and a platform indicator).

Everything is read-only and expressed in SQL so it stays bounded on the
real 8M-row universe (window functions pick one firm per provider; the
heavy joins are index-backed). Geography is the practice-location state by
default; a future Census-geocoded `fips_county` slots in by changing the
`geo_col` without touching the metric logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# DOJ/FTC Horizontal Merger Guidelines HHI bands (points, 0..10000).
HHI_UNCONCENTRATED = 1500
HHI_MODERATE = 2500


def _geo_col(geo_level: str) -> str:
    """Map a geo level to the practice-address column. ``county`` resolves
    to the (currently NULL-stubbed) fips_county so the call site is stable
    once the Census geocoder lands."""
    return {
        "state": "a.state",
        "city": "a.city",
        "zip5": "a.zip5",
        "county": "a.fips_county",
    }.get(geo_level, "a.state")


def _hhi_band(hhi: float) -> str:
    if hhi < HHI_UNCONCENTRATED:
        return "unconcentrated"
    if hhi < HHI_MODERATE:
        return "moderately_concentrated"
    return "highly_concentrated"


# Common CTE: each provider's primary practice market + primary specialty.
# Pulled once and reused by several metrics. Restricted to active providers
# with a practice address so the denominators are clean.
def _provider_market_sql(geo_level: str, entity_type: Optional[int]) -> str:
    geo = _geo_col(geo_level)
    et = "" if entity_type is None else f" AND p.entity_type = {int(entity_type)}"
    return f"""
        SELECT p.npi AS npi, p.entity_type AS entity_type,
               {geo} AS geo,
               t.classification AS classification,
               bt.taxonomy_code AS taxonomy_code
        FROM dim_provider p
        JOIN dim_provider_address a
             ON a.npi = p.npi AND a.address_purpose = 'practice'
        LEFT JOIN bridge_provider_taxonomy bt
             ON bt.npi = p.npi AND bt.primary_flag = 1
        LEFT JOIN dim_taxonomy t
             ON t.taxonomy_code = bt.taxonomy_code
        WHERE p.status = 'active' AND {geo} IS NOT NULL AND {geo} <> ''{et}
    """


@dataclass
class MarketRow:
    geo: str
    classification: str
    provider_count: int


def tam_by_taxonomy_geography(
    store: Any, *, geo_level: str = "state", entity_type: Optional[int] = None,
    classification: Optional[str] = None, limit: int = 200,
) -> List[Dict[str, Any]]:
    """Provider count by (geography × specialty classification). The TAM /
    market-structure spine. Sorted densest-first."""
    base = _provider_market_sql(geo_level, entity_type)
    having = ""
    args: List[Any] = []
    if classification:
        having = "HAVING classification = ?"
        args.append(classification)
    sql = (f"SELECT geo, COALESCE(classification,'(unclassified)') classification, "
           f"COUNT(*) provider_count FROM ({base}) "
           f"GROUP BY geo, classification {having} "
           f"ORDER BY provider_count DESC LIMIT ?")
    args.append(int(limit))
    with store.connect() as con:
        rows = con.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def market_concentration(
    store: Any, *, geo_level: str = "state",
    classification: Optional[str] = None, min_providers: int = 5,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """HHI per (geography × specialty), using each organization's captive-
    provider share as a revenue proxy. Independent providers (no affiliation)
    are singleton firms. Returns markets ranked most-concentrated first.

    HHI = Σ (firm_share)² × 10000, scored against DOJ/FTC bands.
    """
    pm = _provider_market_sql(geo_level, entity_type=1)  # individuals form the roster
    # Assign each individual to its best (highest-confidence) organization,
    # else to a singleton firm keyed by its own NPI.
    sql = f"""
        WITH pm AS ({pm}),
        best AS (
            SELECT individual_npi, organization_npi,
                   ROW_NUMBER() OVER (
                       PARTITION BY individual_npi
                       ORDER BY confidence DESC, organization_npi) rn
            FROM bridge_provider_affiliation
        ),
        firm AS (
            SELECT pm.geo AS geo,
                   COALESCE(pm.classification,'(unclassified)') AS classification,
                   COALESCE(b.organization_npi, 'INDEP:'||pm.npi) AS firm_id
            FROM pm
            LEFT JOIN best b ON b.individual_npi = pm.npi AND b.rn = 1
        ),
        firm_counts AS (
            SELECT geo, classification, firm_id, COUNT(*) AS n
            FROM firm GROUP BY geo, classification, firm_id
        ),
        market AS (
            SELECT geo, classification,
                   SUM(n) AS total_providers,
                   COUNT(*) AS firm_count,
                   SUM(n*n) AS sum_sq,
                   MAX(n) AS largest_firm
            FROM firm_counts GROUP BY geo, classification
        )
        SELECT geo, classification, total_providers, firm_count,
               CAST(10000.0*sum_sq/(total_providers*total_providers) AS REAL) AS hhi,
               CAST(100.0*largest_firm/total_providers AS REAL) AS top_firm_share_pct
        FROM market
        WHERE total_providers >= ?
        {"AND classification = ?" if classification else ""}
        ORDER BY hhi DESC LIMIT ?
    """
    args: List[Any] = [int(min_providers)]
    if classification:
        args.append(classification)
    args.append(int(limit))
    with store.connect() as con:
        rows = con.execute(sql, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["hhi"] = round(d["hhi"], 1)
        d["top_firm_share_pct"] = round(d["top_firm_share_pct"], 1)
        d["concentration_band"] = _hhi_band(d["hhi"])
        out.append(d)
    return out


def fragmentation_scan(
    store: Any, *, geo_level: str = "state",
    classification: Optional[str] = None, max_independent_size: int = 3,
    min_providers: int = 10, limit: int = 100,
) -> List[Dict[str, Any]]:
    """Roll-up hunting: markets with many sub-scale independent organizations.
    A high independent-share + low HHI flags a fragmented market ripe for a
    platform + add-on thesis. Returns a roll-up score (independent share ×
    firm count, normalized) descending."""
    conc = market_concentration(store, geo_level=geo_level,
                                classification=classification,
                                min_providers=min_providers, limit=10_000)
    pm = _provider_market_sql(geo_level, entity_type=1)
    # independents = individuals with no affiliation at all
    sql = f"""
        WITH pm AS ({pm})
        SELECT pm.geo AS geo,
               COALESCE(pm.classification,'(unclassified)') AS classification,
               SUM(CASE WHEN aff.individual_npi IS NULL THEN 1 ELSE 0 END) AS independents,
               COUNT(*) AS total
        FROM pm
        LEFT JOIN (SELECT DISTINCT individual_npi FROM bridge_provider_affiliation) aff
             ON aff.individual_npi = pm.npi
        GROUP BY pm.geo, pm.classification
    """
    with store.connect() as con:
        indep = {(r["geo"], r["classification"]): (r["independents"], r["total"])
                 for r in con.execute(sql).fetchall()}
    out = []
    for m in conc:
        key = (m["geo"], m["classification"])
        ind, tot = indep.get(key, (0, m["total_providers"]))
        if not tot:
            continue
        indep_share = ind / tot
        # Roll-up score: fragmented (low HHI) + high independent share +
        # enough firms to consolidate. Scaled 0..100.
        score = indep_share * (1 - min(m["hhi"], 10000) / 10000) * \
            min(m["firm_count"] / 20.0, 1.0) * 100
        out.append({
            "geo": m["geo"], "classification": m["classification"],
            "total_providers": tot, "firm_count": m["firm_count"],
            "independent_providers": ind,
            "independent_share_pct": round(100 * indep_share, 1),
            "hhi": m["hhi"], "concentration_band": m["concentration_band"],
            "rollup_score": round(score, 1),
        })
    out.sort(key=lambda d: d["rollup_score"], reverse=True)
    return out[:limit]


# Year extracted from an NPPES date, tolerant of both the file's native
# MM/DD/YYYY and the API's YYYY-MM-DD. Used for growth cohorts.
_YEAR_EXPR = ("CASE WHEN instr({c},'/')>0 "
              "THEN substr({c}, length({c})-3, 4) ELSE substr({c},1,4) END")


def enumeration_trend(
    store: Any, *, geo_level: str = "state", geo: Optional[str] = None,
    classification: Optional[str] = None, since_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Provider-growth cohort: new NPI enumerations vs. deactivations per
    year for a market, with net growth — the "is this market growing?" CDD
    signal. Returns one row per year, oldest-first."""
    geo_c = _geo_col(geo_level)
    enum_year = _YEAR_EXPR.format(c="p.enumeration_date")
    deact_year = _YEAR_EXPR.format(c="p.deactivation_date")
    where = [f"{geo_c} IS NOT NULL", f"{geo_c} <> ''"]
    args: List[Any] = []
    join_taxo = ""
    if classification:
        join_taxo = (" JOIN bridge_provider_taxonomy bt ON bt.npi=p.npi AND bt.primary_flag=1"
                     " JOIN dim_taxonomy t ON t.taxonomy_code=bt.taxonomy_code")
        where.append("t.classification = ?"); args.append(classification)
    if geo:
        where.append(f"{geo_c} = ?"); args.append(geo)
    wsql = " AND ".join(where)
    sql = f"""
        WITH scoped AS (
            SELECT p.npi,
                   {enum_year} AS enum_year,
                   CASE WHEN p.deactivation_date IS NOT NULL
                             AND p.deactivation_date <> ''
                        THEN {deact_year} ELSE NULL END AS deact_year
            FROM dim_provider p
            JOIN dim_provider_address a
                 ON a.npi=p.npi AND a.address_purpose='practice'
            {join_taxo}
            WHERE {wsql}
        ),
        enrolled AS (
            SELECT enum_year AS year, COUNT(*) AS new_providers
            FROM scoped WHERE enum_year GLOB '[12][0-9][0-9][0-9]' GROUP BY enum_year
        ),
        retired AS (
            SELECT deact_year AS year, COUNT(*) AS deactivated
            FROM scoped WHERE deact_year GLOB '[12][0-9][0-9][0-9]' GROUP BY deact_year
        )
        SELECT COALESCE(e.year, r.year) AS year,
               COALESCE(e.new_providers, 0) AS new_providers,
               COALESCE(r.deactivated, 0) AS deactivated
        FROM enrolled e
        LEFT JOIN retired r ON r.year = e.year
        UNION
        SELECT r.year, 0, r.deactivated FROM retired r
        WHERE r.year NOT IN (SELECT year FROM enrolled)
        ORDER BY year
    """
    with store.connect() as con:
        rows = con.execute(sql, args).fetchall()
    out = []
    cumulative = 0
    for r in rows:
        if since_year and int(r["year"]) < since_year:
            continue
        net = r["new_providers"] - r["deactivated"]
        cumulative += net
        out.append({"year": r["year"], "new_providers": r["new_providers"],
                    "deactivated": r["deactivated"], "net_growth": net,
                    "cumulative_net": cumulative})
    return out


def roster_integrity(
    store: Any, *, geo_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Deactivation / reactivation exposure — the terminated-provider risk to
    a target's revenue base. Optionally broken out by geography."""
    with store.connect() as con:
        total = con.execute("SELECT COUNT(*) c FROM dim_provider").fetchone()["c"]
        deact = con.execute(
            "SELECT COUNT(*) c FROM dim_provider WHERE status='deactivated'").fetchone()["c"]
        react = con.execute(
            "SELECT COUNT(*) c FROM dim_provider "
            "WHERE reactivation_date IS NOT NULL AND reactivation_date<>''").fetchone()["c"]
        by_geo = []
        if geo_level:
            geo = _geo_col(geo_level)
            rows = con.execute(f"""
                SELECT {geo} AS geo,
                       COUNT(DISTINCT p.npi) AS providers,
                       SUM(CASE WHEN p.status='deactivated' THEN 1 ELSE 0 END) AS deactivated
                FROM dim_provider p
                JOIN dim_provider_address a
                     ON a.npi=p.npi AND a.address_purpose='practice'
                WHERE {geo} IS NOT NULL AND {geo}<>''
                GROUP BY {geo} ORDER BY deactivated DESC LIMIT 100
            """).fetchall()
            for r in rows:
                d = dict(r)
                d["deactivation_rate_pct"] = round(
                    100 * d["deactivated"] / d["providers"], 2) if d["providers"] else 0.0
                by_geo.append(d)
    return {
        "total_providers": total,
        "deactivated": deact,
        "reactivated": react,
        "deactivation_rate_pct": round(100 * deact / total, 2) if total else 0.0,
        "by_geo": by_geo,
    }


def affiliation_footprint(
    store: Any, *, min_confidence: float = 0.5, limit: int = 50,
) -> List[Dict[str, Any]]:
    """Organizations ranked by captive provider count (referral / captive-
    volume proxy; a platform-scale indicator). Only counts affiliations at or
    above ``min_confidence`` so weak co-location noise doesn't inflate."""
    sql = """
        SELECT b.organization_npi AS npi,
               p.organization_name AS organization_name,
               COUNT(DISTINCT b.individual_npi) AS captive_providers,
               ROUND(AVG(b.confidence), 3) AS avg_confidence
        FROM bridge_provider_affiliation b
        JOIN dim_provider p ON p.npi = b.organization_npi
        WHERE b.confidence >= ?
        GROUP BY b.organization_npi
        ORDER BY captive_providers DESC LIMIT ?
    """
    with store.connect() as con:
        rows = con.execute(sql, (float(min_confidence), int(limit))).fetchall()
    return [dict(r) for r in rows]


def rollup_targets(
    store: Any, *, classification: Optional[str] = None,
    geo_level: str = "state", geo: Optional[str] = None,
    max_captive: int = 3, limit: int = 100,
) -> List[Dict[str, Any]]:
    """Sub-scale independent organizations that fit an add-on thesis: a
    Type-2 org in the target market with few captive providers. Returns
    candidate org NPIs with their captive count and location."""
    geo_c = _geo_col(geo_level)
    args: List[Any] = []
    where = ["p.entity_type = 2", "p.status = 'active'"]
    join_taxo = ""
    if classification:
        join_taxo = (" JOIN bridge_provider_taxonomy bt ON bt.npi=p.npi AND bt.primary_flag=1"
                     " JOIN dim_taxonomy t ON t.taxonomy_code=bt.taxonomy_code")
        where.append("t.classification = ?"); args.append(classification)
    if geo:
        where.append(f"{geo_c} = ?"); args.append(geo)
    wsql = " AND ".join(where)
    sql = f"""
        SELECT p.npi, p.organization_name, {geo_c} AS geo,
               COALESCE(fc.captive,0) AS captive_providers
        FROM dim_provider p
        JOIN dim_provider_address a
             ON a.npi=p.npi AND a.address_purpose='practice'
        {join_taxo}
        LEFT JOIN (
            SELECT organization_npi, COUNT(DISTINCT individual_npi) captive
            FROM bridge_provider_affiliation GROUP BY organization_npi
        ) fc ON fc.organization_npi = p.npi
        WHERE {wsql} AND COALESCE(fc.captive,0) <= ?
        ORDER BY captive_providers DESC, p.organization_name LIMIT ?
    """
    args += [int(max_captive), int(limit)]
    with store.connect() as con:
        rows = con.execute(sql, args).fetchall()
    return [dict(r) for r in rows]
