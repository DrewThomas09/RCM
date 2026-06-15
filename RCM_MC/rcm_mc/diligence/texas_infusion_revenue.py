"""Texas infusion · code-level revenue build + competitor benchmark.

The data-room reconciliation a deal team runs on an infusion target:
reconstruct revenue bottom-up from CPT administration units × the
Medicare rate, then benchmark the platform against the Texas
competitive set.

* **CPT units & revenue by code** — modeled annual Texas units for each
  PFS infusion-administration code, priced at the real CY2025 national
  non-facility amount (``PFS_ADMIN_CODES``). Units are built from the
  therapy patient pools (real population × published treated-prevalence)
  × a documented per-therapy annual-infusion frequency × the CPT coding
  stack each therapy bills — so every unit traces to a pool, a
  frequency and a code. Pure home-pump therapies (TPN, inotropes) bill
  an HIT per-diem, not a chair CPT, and are excluded from the chair-code
  build with a note.

* **Buy-and-bill context** — administration is only ~10–20% of an
  infusion platform's gross; the drug (Part B ASP+6, sequestered to
  ~ASP+4.3%) is the rest. The build grosses the admin revenue up at a
  documented administration share so the code-level number sits next to
  a realistic platform revenue.

* **Texas competitor benchmark** — the named operator shares (the HHI
  base), the fragmentation verdict, and the channel/ownership map of the
  platforms competing in Texas.

Everything recomputes from :mod:`rcm_mc.diligence.texas_infusion` and the
workforce therapy layer — no number is typed in.
"""
from __future__ import annotations

import functools
from typing import Any

from .texas_infusion_continued import PFS_ADMIN_CODES, PFS_SOURCE_NOTE
from .texas_infusion_workforce import texas_therapy_mix

#: Per-therapy CPT coding + annual-infusion frequency. ``stack`` is the
#: CPT administration codes a single visit bills (multiplicity matters —
#: add-on hours repeat); ``annual`` is the modeled infusions per patient
#: per year with its clinical basis. ``None`` stack = home-pump therapy
#: that bills an HIT per-diem, not a chair CPT (excluded from the build).
_THERAPY_CPT: dict[str, dict[str, Any]] = {
    "ig": {"stack": ("96365", "96366", "96366", "96366"), "annual": 14,
           "basis": "IVIG ~q4wk, 4-hr therapeutic infusion"},
    "biologic": {"stack": ("96413", "96375"), "annual": 8,
                 "basis": "complex-biologic maintenance ~q6–8wk + pre-med "
                          "push"},
    "rare": {"stack": ("96365", "96366"), "annual": 26,
             "basis": "enzyme-replacement / factor ~q2wk"},
    "opat": {"stack": ("96365",), "annual": 15,
             "basis": "office-administered OPAT course (~15 encounters)"},
    "tpn": {"stack": None, "annual": 0,
            "basis": "home parenteral nutrition — HIT per-diem, not chair "
                     "CPT"},
    "inotrope": {"stack": None, "annual": 0,
                 "basis": "home continuous inotrope — not chair CPT"},
}

#: Administration is a documented minority of infusion gross revenue; the
#: drug (buy-and-bill) is the balance. MedPAC / channel economics put
#: admin at ~10–20% of gross — we gross up at the mid-point.
_ADMIN_SHARE_OF_GROSS = 0.15


@functools.lru_cache(maxsize=1)
def cpt_units_and_revenue() -> dict[str, Any]:
    """CPT administration units and revenue by code for the Texas
    infusion market — the bottom-up revenue reconstruction. Cached
    because every input is deterministic."""
    mix = {t["key"]: t for t in texas_therapy_mix()["therapies"]}
    by_code = {c["code"]: c for c in PFS_ADMIN_CODES}

    # Accumulate units per CPT code from each addressable therapy.
    units: dict[str, float] = {c["code"]: 0.0 for c in PFS_ADMIN_CODES}
    therapy_rows: list[dict[str, Any]] = []
    for key, spec in _THERAPY_CPT.items():
        t = mix.get(key)
        if not t:
            continue
        patients = t.get("estimated_patients") or 0
        if not spec["stack"]:
            therapy_rows.append({
                "therapy": t["therapy"], "patients": patients,
                "annual_infusions": 0, "annual_visits": 0,
                "stack": "—", "basis": spec["basis"], "addressable": False})
            continue
        annual_visits = patients * spec["annual"]
        for code in spec["stack"]:
            units[code] += annual_visits
        therapy_rows.append({
            "therapy": t["therapy"], "patients": patients,
            "annual_infusions": spec["annual"],
            "annual_visits": round(annual_visits),
            "stack": " + ".join(spec["stack"]), "basis": spec["basis"],
            "addressable": True})

    code_rows: list[dict[str, Any]] = []
    admin_revenue = 0.0
    for c in PFS_ADMIN_CODES:
        u = units[c["code"]]
        rev = u * c["nonfac"]
        admin_revenue += rev
        code_rows.append({
            "code": c["code"], "family": c["family"],
            "descriptor": c["descriptor"], "role": c["role"],
            "rate_nonfac": c["nonfac"], "rate_2026": c["nonfac_2026"],
            "units": round(u), "revenue": round(rev)})
    code_rows.sort(key=lambda r: -r["revenue"])

    gross_revenue = (admin_revenue / _ADMIN_SHARE_OF_GROSS
                     if _ADMIN_SHARE_OF_GROSS else admin_revenue)
    total_units = sum(units.values())
    return {
        "codes": code_rows,
        "therapies": therapy_rows,
        "totals": {
            "admin_units": round(total_units),
            "admin_revenue": round(admin_revenue),
            "drug_revenue_implied": round(gross_revenue - admin_revenue),
            "gross_revenue_implied": round(gross_revenue),
            "admin_share_of_gross": _ADMIN_SHARE_OF_GROSS,
        },
        "rate_source": PFS_SOURCE_NOTE,
        "method_note": (
            "Units are MODELED: therapy patient pool (real population × "
            "published treated-prevalence) × the per-therapy annual "
            "infusion frequency × the CPT coding stack. Priced at the "
            "real CY2025 national non-facility PFS amount. Home-pump "
            "therapies (TPN, inotropes) bill an HIT per-diem and are "
            "excluded from the chair-code build. Gross revenue grosses "
            "the admin total up at a 15% administration share of gross "
            "(buy-and-bill drug is the balance)."),
    }


@functools.lru_cache(maxsize=1)
def texas_competitor_benchmark() -> dict[str, Any]:
    """The Texas infusion competitive set: named-operator shares (the
    HHI base), the fragmentation read, the operator detail map, and the
    channel split — the benchmark a sponsor sizes a roll-up against."""
    from .texas_infusion import (
        US_POPULATION_2024,
        _chains,
        _hhi_named,
        infusion_players,
        texas_provider_landscape,
    )
    from .texas_infusion_geo import tx_county_universe

    chains = _chains()
    # Texas competitive set only — drop operators with no Texas footprint.
    players = [p for p in infusion_players() if p.get("tx")]
    tx_pop = sum(r["population"] for r in tx_county_universe())
    landscape = texas_provider_landscape(tx_pop / US_POPULATION_2024)

    # HHI over the NAMED operators only — the fragmented independent pool
    # is atomized, not one 59% firm. Reuses the model's own function so
    # this benchmark can never disagree with the main page's HHI.
    hhi = _hhi_named(chains)
    band = ("highly concentrated" if hhi >= 2500 else
            "moderately concentrated" if hhi >= 1500 else
            "unconcentrated / fragmented")
    named = [c for c in chains if c.get("named")]
    top = max(named, key=lambda c: c["share"]) if named else None
    independents = next((c for c in chains if not c.get("named")), None)

    # Channel split across the named operators.
    channels: dict[str, int] = {}
    for p in players:
        channels[p["channel"]] = channels.get(p["channel"], 0) + 1

    return {
        "chains": chains,
        "players": players,
        "landscape": landscape,
        "hhi": hhi,
        "hhi_band": band,
        "top_operator": top["org"] if top else None,
        "top_operator_share": top["share"] if top else None,
        "independent_share": independents["share"] if independents else None,
        "channel_counts": channels,
        "note": (
            "Operator shares are national infusion-market estimates from "
            "public disclosures (directional); the HHI recomputes from "
            "them. Every named platform competes in Texas (no Certificate "
            "of Need, no Medicaid expansion). The 59% regional / "
            "independent pool is the roll-up target set."),
    }
