"""Live public-data connectors for the NPI cleaner's online mode.

Cross-uses the connectors PE Desk already ships in ``rcm_mc.data_public`` —
NPPES, RxNorm/RxNav, openFDA — plus the shared public-API catalog, rather than
standing up new clients. Everything here is **opt-in** (the page's online-mode
box), **bounded** (distinct values only, capped per run), and **guarded**: a
missing module or a blocked network degrades to a note, never an exception into
the pipeline. Every network entry point accepts an ``opener`` so tests inject a
fake transport and never touch the internet.

Connectors, by the column they light up:

  * **RxNorm / RxNav** — NDC and drug-name columns → RxCUI + normalized
    ingredient/brand (``rxcui``, ``name``, ``tty``). The join that turns a raw
    NDC or free-text drug into a stable concept.
  * **openFDA** — NDC → drug product label (brand / generic / labeler).
  * **NPPES** — NPI columns → verify (active vs. deactivated) + recover a
    candidate NPI from a provider/org name (delegated to ``nppes_bridge``).

``catalog()`` also exposes the full ~19-source public-data catalog so the page
can show every connection available for wiring.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

# Per-run caps so a huge file can't fan out into thousands of calls.
_MAX_RXNORM = 40
_MAX_OPENFDA = 20


def available() -> bool:
    try:
        from ..data_public import public_api_clients  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


# Sources that actually DO something in a cleaning run today. NPPES,
# RxNorm and openFDA fire in enrich mode (see engine._enrich_via_nppes +
# connectors.resolve_drugs); OIG LEIE screens offline once its pack is
# installed; PECOS runs behind the deep flag. Everything else in the
# catalog is reachable elsewhere in PE Desk but is NOT wired to a claims
# clean — the panel used to imply all of them were, which is misleading
# on a compliance-adjacent surface.
_CLEANING_WIRED = frozenset({
    "nppes", "rxnorm", "rxnav", "openfda", "oig_leie", "pecos",
})


def catalog() -> List[dict]:
    """Every public-data source PE Desk can reach, for the connections
    panel. ``cleaning_wired`` is the honest per-source claim for THIS
    tool; ``is_wired`` is the platform-wide "has a client" flag."""
    try:
        from ..data_public import public_api_catalog as cat
    except Exception:  # noqa: BLE001
        return []
    out = []
    for s in cat.all_sources():
        out.append({
            "id": s.id, "name": s.name, "operator": s.operator,
            "category": getattr(s, "category", ""),
            "cost": getattr(s, "cost", ""),
            "docs_url": getattr(s, "docs_url", ""),
            "status": getattr(s, "status", ""),
            "is_wired": bool(getattr(s, "is_wired", False)),
            "cleaning_wired": s.id in _CLEANING_WIRED,
        })
    # Wired-for-cleaning first, then alphabetical — the sources that act
    # on a run should lead the panel.
    out.sort(key=lambda d: (not d["cleaning_wired"], d["name"].lower()))
    return out


def _distinct(values: List[str], cap: int) -> tuple:
    """Distinct non-empty, order-preserving, with a truncation flag."""
    seen: List[str] = []
    for v in values:
        s = str(v or "").strip()
        if s and s not in seen:
            seen.append(s)
    return (seen[:cap], len(seen) > cap)


def resolve_drugs(
    ndcs: List[str], names: List[str], *,
    opener: Optional[Callable] = None,
    rxnorm_cap: int = _MAX_RXNORM, openfda_cap: int = _MAX_OPENFDA,
) -> List[dict]:
    """Run the drug connectors (RxNorm, openFDA) over distinct NDCs/names.

    Returns a list of connector-result dicts (one per connector that had
    inputs), each with counts + a small sample, ready for the UI.
    """
    results: List[dict] = []
    try:
        from ..data_public import public_api_clients as pac
    except Exception:  # noqa: BLE001
        return results

    ndc_list, ndc_trunc = _distinct(ndcs, rxnorm_cap)
    name_list, name_trunc = _distinct(names, rxnorm_cap)

    # ---- RxNorm / RxNav: NDC → concept, and drug name → concept ----
    if ndc_list or name_list:
        resolved, unresolved, sample = 0, 0, []
        errors = 0
        for ndc in ndc_list:
            try:
                concept = pac.rxnorm_normalize(ndc, by="ndc", opener=opener)
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            if concept:
                resolved += 1
                if len(sample) < 12:
                    sample.append({"input": ndc, "kind": "NDC",
                                   "rxcui": concept.get("rxcui", ""),
                                   "name": concept.get("name", ""),
                                   "tty": concept.get("tty", "")})
            else:
                unresolved += 1
        for nm in name_list:
            try:
                concept = pac.rxnorm_normalize(nm, by="name", opener=opener)
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            if concept:
                resolved += 1
                if len(sample) < 12:
                    sample.append({"input": nm, "kind": "name",
                                   "rxcui": concept.get("rxcui", ""),
                                   "name": concept.get("name", ""),
                                   "tty": concept.get("tty", "")})
            else:
                unresolved += 1
        note = (f"{resolved} of {len(ndc_list) + len(name_list)} distinct "
                f"drug values resolved to an RxNorm concept")
        if ndc_trunc or name_trunc:
            note += f" (capped at {rxnorm_cap} each)"
        if errors:
            note += f"; {errors} lookup errors"
        results.append({
            "id": "rxnorm", "label": "RxNorm / RxNav",
            "source": "rxnav.nlm.nih.gov via data_public.public_api_clients",
            "queried": len(ndc_list) + len(name_list),
            "resolved": resolved, "unresolved": unresolved,
            "sample": sample, "note": note + ".",
        })

    # ---- openFDA: NDC → drug label (brand / generic / labeler) ----
    ofda_list, ofda_trunc = _distinct(ndcs, openfda_cap)
    if ofda_list:
        labeled, sample, errors = 0, [], 0
        for ndc in ofda_list:
            try:
                key = "".join(c for c in ndc if c.isdigit() or c == "-")
                # openfda_search returns the results list directly.
                res = pac.openfda_search(
                    "drug", "ndc", search=f'package_ndc:"{key}"', limit=1,
                    opener=opener)
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            rec = res[0] if isinstance(res, list) and res else None
            if rec:
                labeled += 1
                if len(sample) < 12:
                    sample.append({
                        "ndc": ndc,
                        "brand": rec.get("brand_name", ""),
                        "generic": rec.get("generic_name", ""),
                        "labeler": rec.get("labeler_name", ""),
                    })
        note = f"{labeled} of {len(ofda_list)} NDCs matched an openFDA label"
        if ofda_trunc:
            note += f" (capped at {openfda_cap})"
        if errors:
            note += f"; {errors} lookup errors"
        results.append({
            "id": "openfda", "label": "openFDA drug label",
            "source": "api.fda.gov via data_public.public_api_clients",
            "queried": len(ofda_list), "resolved": labeled,
            "unresolved": len(ofda_list) - labeled,
            "sample": sample, "note": note + ".",
        })

    return results
