"""Enriched lookup handlers: ``/v1/lookup/marketplace-plan/{plan_id}`` &
``/v1/lookup/county-plans/{fips}``.

These fan one key out across the canonical Marketplace tables to return
the full picture:

  * :func:`lookup_marketplace_plan` — everything keyed to a QHP plan id
    (either a 14-char standard component id like ``21989AK0030001`` or a
    variant id like ``21989AK0030001-01``): every plan-attribute
    variant, the quality star ratings, a premium sample from the Rate
    PUF, and the benefit rows.
  * :func:`lookup_county_plans` — the Marketplace offer picture for one
    county FIPS: the service areas that cover it (explicitly by county
    or via statewide coverage) joined to the plans sold in them.

They are provided as **plain callables** plus a router-agnostic handler
map (:func:`v1_handlers`) so a router that supports plugin registration
can mount them *without editing its core*.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from .tables import HealthcareGovStore

_RATES_LIMIT = 100
_BENEFITS_LIMIT = 200
_PLANS_LIMIT = 200
_MAX_AREA_PAIRS = 100    # cap the issuer/service-area OR fan-out


def lookup_marketplace_plan(store: HealthcareGovStore, plan_id: str,
                            *, limit: int = _RATES_LIMIT) -> Dict[str, Any]:
    """Everything keyed to a Marketplace plan id.

    The Rate/Quality PUFs key on the 14-char standard component id while
    Plan Attributes keys on the variant id (``...-01``), so we derive
    the standard component from whichever form the caller passed and
    fan out with it.
    """
    pid = str(plan_id).strip()
    std = pid.split("-", 1)[0]
    lim = max(1, min(int(limit), 1000))
    variants = _rows(
        store,
        "SELECT * FROM healthcare_gov_plan_attributes "
        "WHERE standardcomponentid = ? OR planid = ? "
        "ORDER BY planid ASC", (std, pid))
    quality = _rows(
        store,
        "SELECT * FROM healthcare_gov_plan_quality WHERE planid = ?", (std,))
    rates = _rows(
        store,
        "SELECT planid, ratingareaid, tobacco, age, individualrate, "
        "individualtobaccorate, couple, rateeffectivedate, rateexpirationdate "
        "FROM healthcare_gov_rates WHERE planid = ? "
        "ORDER BY ratingareaid ASC, age ASC LIMIT ?", (std, lim))
    rates_total = store.count("healthcare_gov_rates", "planid = ?", (std,))
    benefits = _rows(
        store,
        "SELECT planid, benefitname, iscovered, isehb, copayinntier1, "
        "coinsinntier1, quantlimitonsvc, limitqty, limitunit "
        "FROM healthcare_gov_benefits_cost_sharing "
        "WHERE planid = ? OR planid LIKE ? "
        "ORDER BY benefitname ASC LIMIT ?", (pid, f"{std}-%", _BENEFITS_LIMIT))
    benefits_total = store.count(
        "healthcare_gov_benefits_cost_sharing",
        "planid = ? OR planid LIKE ?", (pid, f"{std}-%"))
    return {
        "plan_id": pid,
        "standard_component_id": std,
        "found": bool(variants or quality or rates or benefits),
        "plan_variants": {"count": len(variants), "rows": variants},
        "quality_ratings": quality[0] if quality else None,
        "rates": {"count": rates_total, "sample": rates},
        "benefits": {"count": benefits_total, "sample": benefits},
    }


def lookup_county_plans(store: HealthcareGovStore, fips: str,
                        *, limit: int = _PLANS_LIMIT) -> Dict[str, Any]:
    """Marketplace plans offered in a county (5-digit FIPS).

    Service Area PUF rows name covered counties by FIPS; statewide
    service areas carry ``coverentirestate='Yes'`` with an empty county,
    so we first resolve the county's state from its explicit rows and
    then include that state's statewide areas too. Plans join back on
    ``(statecode, issuerid, serviceareaid)``.
    """
    county = str(fips).strip()
    lim = max(1, min(int(limit), 1000))
    county_areas = _rows(
        store,
        "SELECT * FROM healthcare_gov_service_areas WHERE county = ? "
        "ORDER BY statecode, issuerid, serviceareaid", (county,))
    states = sorted({r["statecode"] for r in county_areas
                     if r.get("statecode")})
    statewide: List[Dict[str, Any]] = []
    if states:
        placeholders = ", ".join("?" for _ in states)
        statewide = _rows(
            store,
            f"SELECT * FROM healthcare_gov_service_areas "
            f"WHERE coverentirestate = 'Yes' AND statecode IN ({placeholders}) "
            f"ORDER BY statecode, issuerid, serviceareaid", tuple(states))
    pairs = _area_pairs(county_areas + statewide)
    plans: List[Dict[str, Any]] = []
    plans_total = 0
    if pairs:
        clause = " OR ".join(
            "(statecode = ? AND issuerid = ? AND serviceareaid = ?)"
            for _ in pairs)
        args: List[str] = [v for p in pairs for v in p]
        plans = _rows(
            store,
            f"SELECT planid, standardcomponentid, planmarketingname, "
            f"issuerid, issuermarketplacemarketingname, statecode, "
            f"metallevel, plantype, marketcoverage, dentalonlyplan, "
            f"serviceareaid FROM healthcare_gov_plan_attributes "
            f"WHERE {clause} ORDER BY planid ASC LIMIT ?",
            (*args, lim))
        plans_total = store.count(
            "healthcare_gov_plan_attributes", clause, tuple(args))
    return {
        "county_fips": county,
        "states": states,
        "service_areas": {
            "county_rows": len(county_areas),
            "statewide_rows": len(statewide),
            "issuer_area_pairs": len(pairs),
        },
        "plans": {"count": plans_total, "sample": plans},
    }


def _area_pairs(areas: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """Distinct (state, issuer, service-area) triples, order-stable, capped.

    The cap keeps the OR fan-out bounded — a county is covered by a
    handful of issuers in practice, so 100 triples is generous.
    """
    seen: Dict[Tuple[str, str, str], None] = {}
    for r in areas:
        key = (str(r.get("statecode") or ""), str(r.get("issuerid") or ""),
               str(r.get("serviceareaid") or ""))
        if all(key):
            seen.setdefault(key, None)
    return list(seen)[:_MAX_AREA_PAIRS]


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: HealthcareGovStore) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the template's path parameter as its leading
    positional argument; trailing keyword parameters have defaults and
    bind from the query string. Kept deliberately framework-free so it
    binds to any router shape.
    """
    return {
        "/v1/lookup/marketplace-plan/{plan_id}":
            lambda plan_id, limit=_RATES_LIMIT:
                lookup_marketplace_plan(store, plan_id, limit=limit),
        "/v1/lookup/county-plans/{fips}":
            lambda fips, limit=_PLANS_LIMIT:
                lookup_county_plans(store, fips, limit=limit),
    }


def _rows(store: HealthcareGovStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
