"""Map resolved RxNav records → the canonical concept + crosswalk rows.

The connector hands over uniform records — ``{"kind": "ndc"|"name"|
"concept", <identifier fields>, "concept": {...}}`` — and every record
fans out into TWO writes: the dataset's own crosswalk grain AND the
shared ``dim_rxnorm_concept`` row, because resolving any identifier
always yields its concept. That keeps one NDC sweep from leaving the
drug dimension empty.

Cross-cutting derivations done here:
  * ``name_key`` lower-cases the query string so a name crosswalk is
    case-insensitive and idempotent across differently-cased extracts.
  * ingredient and class lists become ``; ``-joined TEXT with a count
    alongside (``n_ingredients``), so single-ingredient products are
    filterable without parsing.
  * ``class_source`` records whether the classes came from ATC or the
    DailyMed fallback — an ATC class and a DailyMed class are not the
    same taxonomy and must not be silently pooled.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .endpoints import EndpointSpec

_JOIN = "; "


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an RxCUI roster + audit channel."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    rxcuis: Set[str] = field(default_factory=set)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


def _clean(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return " ".join(str(value).split()) if value not in (None, "") else ""


def _raw(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return ""


_KNOWN_PROPERTY_KEYS = {"rxcui", "name", "tty", "synonym", "language",
                        "suppress", "umlscui"}


def _concept_row(concept: Dict[str, Any], source_endpoint: str
                 ) -> Optional[Dict[str, Any]]:
    rxcui = _clean(concept.get("rxcui"))
    if not rxcui:
        return None
    ingredients = [str(i) for i in (concept.get("ingredients") or []) if i]
    classes = [str(c) for c in (concept.get("classes") or []) if c]
    source = _clean(concept.get("class_source")).upper()
    # ATC and DailyMed are different taxonomies — keep them in their own
    # columns rather than pooling them into one ambiguous "class" field.
    atc = _JOIN.join(classes) if source == "ATC" else ""
    dailymed = _JOIN.join(classes) if source == "DAILYMED" else ""
    return {
        "rxcui": rxcui,
        "name": _clean(concept.get("name")),
        "tty": _clean(concept.get("tty")),
        "synonym": _clean(concept.get("synonym")),
        "ingredients": _JOIN.join(ingredients),
        "n_ingredients": str(len(ingredients)),
        "atc_classes": atc,
        "dailymed_classes": dailymed,
        "class_source": source,
        "raw": _raw(concept.get("properties") or {}),
        "source_endpoint": source_endpoint,
    }


def _ndc_row(rec: Dict[str, Any], concept: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ndc": _clean(rec.get("ndc")),
        "ndc_digits": _clean(rec.get("ndc_digits")),
        "rxcui": _clean(rec.get("rxcui")),
        "resolved_name": _clean(concept.get("name")),
        "raw": _raw({"ndc": rec.get("ndc"), "rxcui": rec.get("rxcui")}),
        "source_endpoint": "ndc",
    }


def _name_row(rec: Dict[str, Any], concept: Dict[str, Any]) -> Dict[str, Any]:
    query = _clean(rec.get("query_name"))
    return {
        "name_key": query.lower(),
        "query_name": query,
        "rxcui": _clean(rec.get("rxcui")),
        "resolved_name": _clean(concept.get("name")),
        "matched_on": _clean(rec.get("matched_on")),
        "match_type": _clean(rec.get("match_type")) or "exact",
        "raw": _raw({"query": query, "rxcui": rec.get("rxcui")}),
        "source_endpoint": "name",
    }


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize resolved records for one endpoint into canonical rows.

    Every record contributes its concept row; ``ndc`` and ``name``
    records additionally contribute their crosswalk row.
    """
    res = NormalizeResult()
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        concept = rec.get("concept")
        if not isinstance(concept, dict):
            concept = {}
        kind = rec.get("kind") or spec.kind

        crow = _concept_row(concept, spec.key)
        if crow is not None:
            res.add("dim_rxnorm_concept", crow)
            res.rxcuis.add(crow["rxcui"])
            res.note_unmapped([
                k for k in (concept.get("properties") or {})
                if k not in _KNOWN_PROPERTY_KEYS])

        if kind == "ndc":
            if _clean(rec.get("ndc")) and _clean(rec.get("rxcui")):
                res.add("xwalk_ndc_rxcui", _ndc_row(rec, concept))
        elif kind == "name":
            if _clean(rec.get("query_name")) and _clean(rec.get("rxcui")):
                res.add("xwalk_name_rxcui", _name_row(rec, concept))
    return res
