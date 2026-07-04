"""Map raw NPPES records → canonical rows.

One record fans out into up to three canonical rows:

  * ``dim_provider`` — one row keyed by NPI, with the **primary practice
    (LOCATION) address** and the **primary taxonomy** flattened on, so
    the common "who/where/what specialty" query needs no join.
  * ``fact_provider_taxonomy`` — one row per taxonomy, key
    ``{npi}:{code}``.
  * ``fact_provider_address`` — one row per address, key
    ``{npi}:{address_purpose}``.

Every accessor is *defensive*: an NPI-1 (individual) record carries
``first_name``/``last_name`` in ``basic``; an NPI-2 (organization) record
carries ``organization_name`` and ``authorized_official_*`` instead.
:func:`dig`/:func:`first_where`/:func:`coalesce` never assume a path.
Anything present on the record that no mapper places is recorded as an
unmapped key so schema drift surfaces instead of silently dropping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .endpoints import EndpointSpec
from .flatten import (as_bool_text, coalesce, dig, first_where, unmapped_keys)


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an unmapped-field audit."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    npis: Set[str] = field(default_factory=set)
    taxonomy_codes: Set[str] = field(default_factory=set)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


# Top-level keys the provider mapper knows how to place.
_KNOWN_TOP_KEYS = {
    "number", "enumeration_type", "created_epoch", "last_updated_epoch",
    "basic", "addresses", "taxonomies", "identifiers", "other_names",
    "endpoints", "practiceLocations",
}


def _is_location(addr: Dict[str, Any]) -> bool:
    return str(addr.get("address_purpose", "")).upper() == "LOCATION"


def _is_primary_taxonomy(tax: Dict[str, Any]) -> bool:
    val = tax.get("primary")
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes", "primary")


def _provider_row(rec: Dict[str, Any], source_endpoint: str) -> Optional[Dict[str, Any]]:
    npi = dig(rec, "number")
    if not npi:
        return None
    npi = str(npi)
    basic = rec.get("basic") or {}
    loc = first_where(rec.get("addresses"), _is_location, {}) or {}
    prim = first_where(rec.get("taxonomies"), _is_primary_taxonomy, {}) or {}
    return {
        "npi": npi,
        "enumeration_type": coalesce(rec, ["enumeration_type"]),
        "status": dig(basic, "status"),
        "first_name": dig(basic, "first_name"),
        "last_name": dig(basic, "last_name"),
        "credential": dig(basic, "credential"),
        "organization_name": dig(basic, "organization_name"),
        "sole_proprietor": dig(basic, "sole_proprietor"),
        "gender": dig(basic, "gender"),
        "enumeration_date": dig(basic, "enumeration_date"),
        "last_updated": dig(basic, "last_updated"),
        "primary_taxonomy_code": dig(prim, "code"),
        "primary_taxonomy_desc": dig(prim, "desc"),
        "primary_license": dig(prim, "license"),
        "primary_license_state": dig(prim, "state"),
        "city": dig(loc, "city"),
        "state": dig(loc, "state"),
        "postal_code": dig(loc, "postal_code"),
        "country_code": dig(loc, "country_code"),
        "telephone": dig(loc, "telephone_number"),
        "source_endpoint": source_endpoint,
    }


def _taxonomy_rows(rec: Dict[str, Any], npi: str, source_endpoint: str
                   ) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for tax in rec.get("taxonomies") or []:
        if not isinstance(tax, dict):
            continue
        code = tax.get("code")
        if not code:
            continue
        code = str(code)
        key = f"{npi}:{code}"
        if key in seen:  # dedupe repeated codes within one record
            continue
        seen.add(key)
        out.append({
            "taxonomy_key": key,
            "npi": npi,
            "code": code,
            "desc": tax.get("desc"),
            "is_primary": as_bool_text(tax.get("primary")),
            "state": tax.get("state"),
            "license": tax.get("license"),
            "source_endpoint": source_endpoint,
        })
    return out


def _address_rows(rec: Dict[str, Any], npi: str, source_endpoint: str
                  ) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for addr in rec.get("addresses") or []:
        if not isinstance(addr, dict):
            continue
        purpose = str(addr.get("address_purpose") or "UNKNOWN").upper()
        key = f"{npi}:{purpose}"
        if key in seen:  # keep the first of a repeated purpose
            continue
        seen.add(key)
        out.append({
            "address_key": key,
            "npi": npi,
            "address_purpose": purpose,
            "address_1": addr.get("address_1"),
            "address_2": addr.get("address_2"),
            "city": addr.get("city"),
            "state": addr.get("state"),
            "postal_code": addr.get("postal_code"),
            "country_code": addr.get("country_code"),
            "telephone_number": addr.get("telephone_number"),
            "source_endpoint": source_endpoint,
        })
    return out


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]) -> NormalizeResult:
    """Normalize a batch of raw NPI records into canonical rows.

    ``spec.key`` becomes each row's ``source_endpoint`` so a re-run of the
    same seeded crawl upserts over itself.
    """
    res = NormalizeResult()
    source_endpoint = spec.key
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        prov = _provider_row(rec, source_endpoint)
        if prov is None:
            continue
        npi = prov["npi"]
        res.npis.add(npi)
        res.add("dim_provider", prov)
        for trow in _taxonomy_rows(rec, npi, source_endpoint):
            res.taxonomy_codes.add(trow["code"])
            res.add("fact_provider_taxonomy", trow)
        for arow in _address_rows(rec, npi, source_endpoint):
            res.add("fact_provider_address", arow)
        res.note_unmapped(unmapped_keys(rec, _KNOWN_TOP_KEYS))
    return res
