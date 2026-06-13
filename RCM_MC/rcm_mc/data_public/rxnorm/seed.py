"""Representative offline seed for the RxNorm slice.

Why a seed exists: this environment's network policy blocks outbound calls to
``rxnav.nlm.nih.gov`` (verified — HTTP 403), so a live bulk backfill cannot run
here. Rather than ship an empty, unverifiable pipeline, we seed a small but
*representative* slice that exercises every edge case the DQ tests care about:

  * NDC format drift — the same molecule reached via 4-4-2, 5-3-2 and
    already-11-digit NDCs (round-trip normalization).
  * A retired→remapped RxCUI whose remap target is an active concept
    (so the resolver can prove stale codes don't drop records).
  * Drug-class grouping spanning all three class types (ATC / therapeutic /
    mechanism-of-action) so class coverage is meaningful.
  * The exact ``package_ndc`` values openFDA's vendored drug-shortage snapshot
    carries, so the read-only openFDA join test reports a real match rate.

The structured dicts below are the source of truth; :func:`seed_opener` renders
them into RxNav-native JSON so the *connector* parses the same shapes it would
see live. Swapping the seed opener for the real ``urllib`` opener is all that
stands between this and a live run. See DECISIONS.md and STATE.md.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlsplit

RELEASE_VERSION = "seed-2026-06 (offline representative slice)"

# rxcui -> (name, tty, status, remapped_to)
SEED_CONCEPTS: Dict[str, Dict[str, str]] = {
    "1191":   {"name": "aspirin", "tty": "IN", "status": "active", "remap": ""},
    "243670": {"name": "aspirin 81 MG Oral Tablet", "tty": "SCD",
               "status": "active", "remap": ""},
    "215568": {"name": "Bayer aspirin 81 MG Oral Tablet", "tty": "SBD",
               "status": "active", "remap": ""},
    "83367":  {"name": "atorvastatin", "tty": "IN", "status": "active", "remap": ""},
    "617312": {"name": "atorvastatin 10 MG Oral Tablet", "tty": "SCD",
               "status": "active", "remap": ""},
    "617318": {"name": "Lipitor 10 MG Oral Tablet", "tty": "SBD",
               "status": "active", "remap": ""},
    "7052":   {"name": "morphine", "tty": "IN", "status": "active", "remap": ""},
    "6902":   {"name": "methylprednisolone", "tty": "IN", "status": "active",
               "remap": ""},
    # Retired + remapped → resolves to active atorvastatin (83367).
    "9999999": {"name": "atorvastatin (obsolete concept)", "tty": "IN",
                "status": "remapped", "remap": "83367"},
}

# rxcui -> list of raw NDC strings (mixed formats on purpose).
SEED_NDCS: Dict[str, List[str]] = {
    "243670": ["0363-0160-01", "00363016001"],          # 5-3-2 and 11-digit
    "617312": ["0071-0155-23"],                          # 4-4-2
    "7052":   ["0409-1896-20"],                          # openFDA shortage NDC
    "6902":   ["55150-313-01"],                          # openFDA shortage NDC
}

# rxcui -> [(related_rxcui, tty)]
SEED_RELATED: Dict[str, List[List[str]]] = {
    "83367":  [["617312", "SCD"], ["617318", "SBD"]],
    "617312": [["83367", "IN"], ["617318", "SBD"]],
    "1191":   [["243670", "SCD"], ["215568", "SBD"]],
}

# rxcui -> [(class_id, class_name, classType)]  classType is RxClass-native.
SEED_CLASSES: Dict[str, List[List[str]]] = {
    "83367": [
        ["C10AA", "HMG CoA reductase inhibitors", "ATC1-4"],
        ["N0000175573", "Hydroxymethylglutaryl-CoA Reductase Inhibitor", "MOA"],
        ["ANTILIPEMIC AGENTS", "ANTILIPEMIC AGENTS", "VA"],
    ],
    "1191": [
        ["B01AC", "Platelet aggregation inhibitors excl. heparin", "ATC1-4"],
        ["N0000000160", "Cyclooxygenase Inhibitors", "MOA"],
        ["NONOPIOID ANALGESICS", "NONOPIOID ANALGESICS", "VA"],
    ],
    "7052": [
        ["N02AA", "Natural opium alkaloids", "ATC1-4"],
        ["N0000175693", "Full Opioid Agonists", "MOA"],
    ],
    "6902": [
        ["H02AB", "Glucocorticoids", "ATC1-4"],
        ["GLUCOCORTICOIDS", "GLUCOCORTICOIDS", "VA"],
    ],
}


# ── RxNav-native payload builders ──────────────────────────────────────────

def _allconcepts_payload(tty_param: str) -> Dict[str, Any]:
    wanted = set(t.upper() for t in tty_param.replace(" ", "+").split("+") if t)
    concepts = [
        {"rxcui": rx, "name": c["name"], "tty": c["tty"]}
        for rx, c in SEED_CONCEPTS.items()
        if not wanted or c["tty"].upper() in wanted
    ]
    return {"minConceptGroup": {"minConcept": concepts}}


def _properties_payload(rxcui: str) -> Dict[str, Any]:
    c = SEED_CONCEPTS.get(rxcui)
    if not c:
        return {"properties": {}}
    return {"properties": {"rxcui": rxcui, "name": c["name"], "tty": c["tty"]}}


def _historystatus_payload(rxcui: str) -> Dict[str, Any]:
    c = SEED_CONCEPTS.get(rxcui, {})
    status = c.get("status", "active").capitalize() if c else "Active"
    hist: Dict[str, Any] = {"rxcuiStatusHistory": {"metaData": {"status": status}}}
    if c.get("remap"):
        hist["rxcuiStatusHistory"]["derivedConcepts"] = {
            "remappedConcept": [{"remappedRxCui": c["remap"],
                                 "remappedName": SEED_CONCEPTS.get(
                                     c["remap"], {}).get("name", "")}]
        }
    return hist


def _allrelated_payload(rxcui: str) -> Dict[str, Any]:
    groups: Dict[str, List[Dict[str, str]]] = {}
    for related_rxcui, tty in SEED_RELATED.get(rxcui, []):
        groups.setdefault(tty, []).append({
            "rxcui": related_rxcui,
            "name": SEED_CONCEPTS.get(related_rxcui, {}).get("name", ""),
            "tty": tty,
        })
    concept_group = [{"tty": tty, "conceptProperties": props}
                     for tty, props in groups.items()]
    return {"allRelatedGroup": {"conceptGroup": concept_group}}


def _ndcs_payload(rxcui: str) -> Dict[str, Any]:
    return {"ndcGroup": {"ndcList": {"ndc": SEED_NDCS.get(rxcui, [])}}}


def _rxcui_by_ndc_payload(ndc: str) -> Dict[str, Any]:
    from .normalize import normalize_ndc
    try:
        target = normalize_ndc(ndc)
    except Exception:
        return {"idGroup": {}}
    for rxcui, ndcs in SEED_NDCS.items():
        for raw in ndcs:
            try:
                if normalize_ndc(raw) == target:
                    return {"idGroup": {"rxnormId": [rxcui]}}
            except Exception:
                continue
    return {"idGroup": {}}


def _ndcproperties_payload(ndc: str) -> Dict[str, Any]:
    from .normalize import normalize_ndc
    try:
        target = normalize_ndc(ndc)
    except Exception:
        return {"ndcPropertyList": {}}
    for rxcui, ndcs in SEED_NDCS.items():
        for raw in ndcs:
            try:
                if normalize_ndc(raw) == target:
                    return {"ndcPropertyList": {"ndcProperty": [{
                        "ndcItem": raw, "ndc11": target, "rxcui": rxcui,
                        "ndcStatus": "ACTIVE",
                        "propertyConceptList": {"propertyConcept": [
                            {"propName": "LABELER", "propValue": "Seed Labeler"},
                            {"propName": "PACKAGE", "propValue": "tablet, 30"},
                        ]},
                    }]}}
            except Exception:
                continue
    return {"ndcPropertyList": {}}


def _rxclass_payload(rxcui: str) -> Dict[str, Any]:
    infos = [{"rxclassMinConceptItem": {"classId": cid, "className": cname,
                                        "classType": ctype}}
             for cid, cname, ctype in SEED_CLASSES.get(rxcui, [])]
    return {"rxclassDrugInfoList": {"rxclassDrugInfo": infos}}


def seed_opener(url: str, headers: Dict[str, str], timeout_s: int) -> bytes:
    """An :data:`connector.Opener` that serves RxNav-native JSON from the seed.

    Lets the connector run its full fetch/parse/paginate path offline. Raises
    on an unrecognised URL so a test can't silently pass against a typo.
    """
    parts = urlsplit(url)
    path = parts.path
    qs = parse_qs(parts.query)

    def _one(key: str) -> str:
        v = qs.get(key, [""])
        return v[0] if v else ""

    payload: Any
    if path.endswith("/allconcepts.json"):
        payload = _allconcepts_payload(_one("tty"))
    elif path.endswith("/properties.json"):
        payload = _properties_payload(_rxcui_from_path(path))
    elif path.endswith("/historystatus.json"):
        payload = _historystatus_payload(_rxcui_from_path(path))
    elif path.endswith("/allrelated.json"):
        payload = _allrelated_payload(_rxcui_from_path(path))
    elif path.endswith("/ndcs.json"):
        payload = _ndcs_payload(_rxcui_from_path(path))
    elif path.endswith("/rxcui.json"):
        payload = _rxcui_by_ndc_payload(_one("id"))
    elif path.endswith("/ndcproperties.json"):
        payload = _ndcproperties_payload(_one("id"))
    elif path.endswith("/byRxcui.json"):
        payload = _rxclass_payload(_one("rxcui"))
    else:
        raise ValueError(f"seed_opener: no fixture for {url!r}")
    return json.dumps(payload).encode("utf-8")


def _rxcui_from_path(path: str) -> str:
    """Extract {rxcui} from /rxcui/{rxcui}/<resource>.json."""
    segs = [s for s in path.split("/") if s]
    for i, s in enumerate(segs):
        if s == "rxcui" and i + 1 < len(segs):
            return segs[i + 1]
    return ""
