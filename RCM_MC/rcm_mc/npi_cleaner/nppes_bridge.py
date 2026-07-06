"""Cross-use the app's existing CMS / NPPES connection from the NPI cleaner.

The uploaded v48 package carried its own raw ``requests``-based NPPES/CMS
clients (``vendor_v48/npi_recovery/clients.py``), but the recovery orchestrator
that drove them (``pipeline`` / ``enrich`` / ``recovery_model``) was missing
from the zip. Rather than resurrect a raw client, this bridge wires the
cleaner's live-lookup features to the connection the rest of PE Desk already
uses: ``rcm_mc.data_public.nppes_api_client`` — same NPPES registry, but with
the app's shared disk cache, error handling and record parsing.

Two live features, both **opt-in** (the page checkbox) and fully guarded so the
offline cleaner never depends on them:

  * **Verify** — look each distinct NPI up in NPPES. Present in the registry →
    ``active`` (with the canonical name / taxonomy / state); absent → the NPI
    is unassigned or deactivated, a stronger signal than any stale seed file.
  * **Recover** — for rows whose billing NPI is missing or malformed but which
    carry a provider/organization name (+ state), search NPPES by name and
    propose the matching NPI. This is the "recovery" half of the tool, run
    through our own CMS connection.

Network calls are bounded: distinct NPIs only, capped per run, and the shared
cache means a repeat file is nearly free. If the client is unavailable or the
network is blocked, every function degrades to an empty/partial result with a
note — it never raises into the pipeline.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional


# Cap live calls per run so a huge upload can't fan out into thousands of
# requests. The page surfaces when the cap truncated coverage.
_MAX_VERIFY = 40
_MAX_RECOVER = 15


def available() -> bool:
    """True when the shared NPPES client imports."""
    try:
        from ..data_public import nppes_api_client  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _digits(v: object) -> str:
    return "".join(ch for ch in str(v) if ch.isdigit())


def verify_npis(npis: List[str], *, cap: int = _MAX_VERIFY) -> Dict[str, object]:
    """Look distinct 10-digit NPIs up in NPPES via the shared client.

    Returns a summary dict: counts plus a per-NPI verdict for the ones checked.
    Never raises — a network failure yields ``{"error": ...}`` with whatever was
    resolved before the failure.
    """
    out: Dict[str, object] = {
        "checked": 0, "active": 0, "not_found": 0, "errors": 0,
        "capped": False, "records": {}, "note": "",
    }
    try:
        from ..data_public import nppes_api_client as nppes
    except Exception:  # noqa: BLE001
        out["note"] = "NPPES client unavailable."
        return out

    seen: List[str] = []
    for raw in npis:
        d = _digits(raw)
        if len(d) == 10 and d not in seen:
            seen.append(d)
    if len(seen) > cap:
        out["capped"] = True
        seen = seen[:cap]

    records: Dict[str, Dict[str, object]] = {}
    for npi in seen:
        try:
            prov = nppes.fetch_by_npi(npi)
        except Exception as exc:  # noqa: BLE001
            out["errors"] = int(out["errors"]) + 1
            records[npi] = {"status": "lookup_error", "detail": str(exc)[:80]}
            continue
        out["checked"] = int(out["checked"]) + 1
        if prov is None:
            out["not_found"] = int(out["not_found"]) + 1
            records[npi] = {"status": "not_found"}
        else:
            out["active"] = int(out["active"]) + 1
            records[npi] = {
                "status": "active",
                "name": prov.name,
                "entity_type": prov.entity_type,
                "taxonomy": prov.taxonomy_label or prov.taxonomy_code,
                "state": prov.state,
            }
    out["records"] = records
    _checked = int(out["checked"])
    _errs = int(out["errors"])
    if seen and _checked == 0 and _errs:
        # Every lookup failed: this is a connectivity/outage signature, not a
        # data problem. Say so plainly so the panel reads "couldn't reach
        # NPPES" instead of an alarming "0 verified, N errors" — offline
        # cleaning already stands on its own.
        out["degraded"] = True
        out["note"] = (
            f"Could not reach the live NPPES registry — all {_errs} NPI "
            "lookups failed (network/connectivity). Present NPIs were not "
            "verified; offline cleaning is unaffected.")
        return out
    parts = [f"{_checked} NPIs verified against the live NPPES registry"]
    if out["not_found"]:
        parts.append(f"{out['not_found']} not found (unassigned or deactivated)")
    if out["capped"]:
        parts.append(f"checked the first {cap} distinct NPIs")
    if _errs:
        parts.append(f"{_errs} lookup errors (skipped; the rest verified)")
    out["note"] = "; ".join(parts) + "."
    return out


def _clean_name(v: object) -> str:
    s = re.sub(r"\s+", " ", str(v or "").strip())
    return s


def recover_candidates(
    queries: List[Dict[str, str]], *, cap: int = _MAX_RECOVER,
) -> Dict[str, object]:
    """Propose NPIs for rows with a missing/bad billing NPI but a name (+ state).

    ``queries`` is a list of ``{"row", "name", "state"}`` dicts. Uses NPPES
    organization search (trailing-wildcard) via the shared client. Returns a
    summary with up to a few candidate NPIs per distinct name. Guarded; never
    raises.
    """
    out: Dict[str, object] = {
        "searched": 0, "resolved": 0, "errors": 0, "capped": False,
        "matches": [], "note": "",
    }
    try:
        from ..data_public import nppes_api_client as nppes
    except Exception:  # noqa: BLE001
        out["note"] = "NPPES client unavailable."
        return out

    # Distinct (name, state) so we don't search the same provider twice.
    seen = set()
    distinct: List[Dict[str, str]] = []
    for q in queries:
        name = _clean_name(q.get("name"))
        state = (q.get("state") or "").strip().upper()[:2]
        if len(name) < 3:
            continue
        key = (name.lower(), state)
        if key in seen:
            continue
        seen.add(key)
        distinct.append({"row": q.get("row", ""), "name": name, "state": state})

    if len(distinct) > cap:
        out["capped"] = True
        distinct = distinct[:cap]

    matches: List[Dict[str, object]] = []
    for q in distinct:
        term = q["name"]
        # NPPES supports a trailing wildcard on name searches.
        search_term = term if term.endswith("*") else term + "*"
        try:
            results = nppes.search_by_organization(
                search_term, state=q["state"], limit=5)
        except Exception:  # noqa: BLE001
            # A failed search was previously silent — the count of names
            # "searched" simply didn't advance, so a network outage looked
            # like "nothing to recover". Count it so partial success is legible.
            out["errors"] = int(out["errors"]) + 1
            continue
        out["searched"] = int(out["searched"]) + 1
        cands = [{"npi": p.npi, "name": p.name, "state": p.state} for p in results[:3]]
        if cands:
            out["resolved"] = int(out["resolved"]) + 1
        matches.append({
            "row": q["row"], "query": term, "state": q["state"],
            "candidates": cands,
        })
    out["matches"] = matches
    _searched = int(out["searched"])
    _errs = int(out["errors"])
    if distinct and _searched == 0 and _errs:
        out["degraded"] = True
        out["note"] = (
            f"Could not reach the live NPPES registry — all {_errs} provider "
            "searches failed (network/connectivity). No NPIs were recovered; "
            "offline cleaning is unaffected.")
        return out
    parts = [f"{_searched} provider names searched in NPPES",
             f"{out['resolved']} resolved to at least one candidate NPI"]
    if _errs:
        parts.append(f"{_errs} searches failed (skipped)")
    if out["capped"]:
        parts.append(f"searched the first {cap} distinct names")
    out["note"] = "; ".join(parts) + "."
    return out
