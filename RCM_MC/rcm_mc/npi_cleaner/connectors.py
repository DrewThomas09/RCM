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


# The connector "recommendation engine": given the shape of THIS file (which
# roles were detected, how blank the NPIs are, how drug-heavy it is), decide
# which of the wired connectors should fire and say why in plain language.
# Surfaced on the Live-connectors tab so a run that only lights 2 of the
# catalog is legible ("openFDA — no NDC/J-code column in this file") instead of
# looking broken. ``mode`` gates *when* it runs: offline always, network in
# enrich mode, deep behind the deep flag.
def plan(signals: Dict[str, object]) -> List[dict]:
    """Return an ordered recommendation for each wired connector.

    ``signals`` keys (all optional): ``has_npi``, ``has_billing``,
    ``blank_npi_pct`` (0-100), ``has_ndc``, ``has_drug_name``,
    ``jcode_pct`` (0-100 of HCPCS rows that are J-codes), ``has_hcpcs``,
    ``has_dx``, ``has_taxonomy``, ``rows``.
    """
    s = signals or {}
    has_npi = bool(s.get("has_npi"))
    has_billing = bool(s.get("has_billing"))
    blank = float(s.get("blank_npi_pct") or 0.0)
    has_ndc = bool(s.get("has_ndc"))
    has_drug = bool(s.get("has_drug_name"))
    jcode = float(s.get("jcode_pct") or 0.0)
    drug_signal = has_ndc or has_drug or jcode > 0
    out: List[dict] = []

    def add(cid, name, applies, mode, reason):
        out.append({"id": cid, "name": name, "applies": bool(applies),
                    "mode": mode, "reason": reason})

    # --- NPPES: verify every NPI; recover blanks when the file is gappy ---
    if has_npi:
        if blank >= 1.0:
            add("nppes", "NPPES NPI Registry", True, "network",
                f"{blank:.1f}% of billing NPIs are blank — verify present "
                "NPIs and recover the blanks from provider name + state.")
        else:
            add("nppes", "NPPES NPI Registry", True, "network",
                "Verify each distinct NPI is active (not deactivated).")
    else:
        add("nppes", "NPPES NPI Registry", False, "network",
            "No NPI column detected in this file.")

    # --- Drug connectors: NDC, free-text drug name, or J-codes ---
    why_drug = []
    if has_ndc:
        why_drug.append("NDC column")
    if has_drug:
        why_drug.append("drug-name column")
    if jcode > 0:
        why_drug.append(f"{jcode:.0f}% J-codes")
    drug_reason = (", ".join(why_drug) + " → resolve to RxNorm concepts."
                   if drug_signal else
                   "No NDC, drug-name, or J-code column in this file.")
    add("rxnorm", "RxNorm / RxNav", drug_signal, "network", drug_reason)
    add("rxnav", "RxNav interactions", drug_signal, "network", drug_reason)
    add("openfda", "openFDA drug label", (has_ndc or jcode > 0), "network",
        ("Match NDC / J-code drugs to an FDA product label."
         if (has_ndc or jcode > 0) else
         "No NDC or J-code column to label."))

    # --- Compliance: billing NPI screens ---
    add("oig_leie", "OIG LEIE exclusions", has_billing, "offline",
        ("Screen billing NPIs against the OIG exclusions list."
         if has_billing else "No billing NPI column to screen."))
    add("pecos", "Medicare PECOS enrollment", has_billing, "deep",
        ("Confirm Medicare enrollment / opt-out for billing NPIs "
         "(deep mode)." if has_billing else "No billing NPI column."))
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
    hcpcs: Optional[List[str]] = None,
    opener: Optional[Callable] = None,
    rxnorm_cap: int = _MAX_RXNORM, openfda_cap: int = _MAX_OPENFDA,
) -> List[dict]:
    """Run the drug connectors (RxNorm, openFDA) over distinct NDCs, drug
    names, and HCPCS/J-codes.

    J-codes are HCPCS Level II drug codes (``J1745`` = infliximab): an
    infusion-pharmacy or oncology extract is often *all* J-codes with no NDC
    and no free-text drug name, so resolving them through RxNav's
    ``idtype=HCPCS`` crosswalk is the difference between the drug connectors
    firing and sitting idle. Returns a list of connector-result dicts (one per
    connector that had inputs), each with counts + a small sample.
    """
    results: List[dict] = []
    try:
        from ..data_public import public_api_clients as pac
    except Exception:  # noqa: BLE001
        return results

    ndc_list, ndc_trunc = _distinct(ndcs, rxnorm_cap)
    name_list, name_trunc = _distinct(names, rxnorm_cap)
    hcpcs_list, hcpcs_trunc = _distinct(hcpcs or [], rxnorm_cap)

    # ---- RxNorm / RxNav: NDC / drug name / HCPCS J-code → concept ----
    if ndc_list or name_list or hcpcs_list:
        resolved, unresolved, sample = 0, 0, []
        errors = 0
        for value, by, kind in (
                [(v, "ndc", "NDC") for v in ndc_list]
                + [(v, "name", "name") for v in name_list]
                + [(v, "hcpcs", "J-code") for v in hcpcs_list]):
            try:
                concept = pac.rxnorm_normalize(value, by=by, opener=opener)
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            if concept:
                resolved += 1
                if len(sample) < 12:
                    sample.append({"input": value, "kind": kind,
                                   "rxcui": concept.get("rxcui", ""),
                                   "name": concept.get("name", ""),
                                   "tty": concept.get("tty", "")})
            else:
                unresolved += 1
        queried = len(ndc_list) + len(name_list) + len(hcpcs_list)
        if queried and errors == queried:
            # Every lookup failed → connectivity/outage, not unresolvable
            # inputs. Say so plainly instead of "0 of N resolved".
            note = (f"Could not reach RxNorm/RxNav — all {errors} drug "
                    "lookups failed (network/connectivity)")
        else:
            note = (f"{resolved} of {queried} distinct drug values "
                    "resolved to an RxNorm concept")
            if ndc_trunc or name_trunc or hcpcs_trunc:
                note += f" (capped at {rxnorm_cap} each)"
            if errors:
                note += f"; {errors} lookup errors (skipped)"
        results.append({
            "id": "rxnorm", "label": "RxNorm / RxNav",
            "source": "rxnav.nlm.nih.gov via data_public.public_api_clients",
            "queried": queried,
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
        if ofda_list and errors == len(ofda_list):
            note = (f"Could not reach openFDA — all {errors} NDC lookups "
                    "failed (network/connectivity)")
        else:
            note = f"{labeled} of {len(ofda_list)} NDCs matched an openFDA label"
            if ofda_trunc:
                note += f" (capped at {openfda_cap})"
            if errors:
                note += f"; {errors} lookup errors (skipped)"
        results.append({
            "id": "openfda", "label": "openFDA drug label",
            "source": "api.fda.gov via data_public.public_api_clients",
            "queried": len(ofda_list), "resolved": labeled,
            "unresolved": len(ofda_list) - labeled,
            "sample": sample, "note": note + ".",
        })

    return results
