"""Map raw NLM ICD-10 records → the canonical ``dim_icd10_code`` row.

One mapper, parameterised by the endpoint's ``code_type`` — CM and PCS
rows share a table and differ only in derivations. Each raw record is a
dict of the requested ``df`` fields (``code``, ``name`` and, where
present, ``long_name``) that the connector already assembled; the mapper
is *defensive* and never assumes a field exists.

Cross-cutting derivations done here:
  * ``code_key`` is the idempotency key ``{code_type}:{code}``.
  * ``chapter`` is the first character of the code (the ICD-10-CM
    chapter letter; for PCS the section character).
  * ``category`` is the code up to the first three characters (before
    the decimal point for CM, e.g. ``E11.65`` → ``E11``).
  * ``billable`` is left blank — the NLM search endpoint does not expose
    a reliable billable flag, so it stays ``''`` until derivable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .endpoints import EndpointSpec


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus a code roster + audit side-channel."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    codes: Set[str] = field(default_factory=set)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


_KNOWN_KEYS = {"code", "name", "long_name", "code_type"}


def chapter_of(code: str) -> str:
    """First character of an ICD-10 code (CM chapter / PCS section)."""
    code = str(code or "").strip()
    return code[0] if code else ""


def category_of(code: str) -> str:
    """The 3-char category — before the decimal point for CM."""
    code = str(code or "").strip()
    base = code.split(".", 1)[0]
    return base[:3]


def _icd10_row(rec: Dict[str, Any], spec: EndpointSpec) -> Optional[Dict[str, Any]]:
    code = rec.get("code")
    if not code:
        return None
    code = str(code).strip()
    ct = spec.code_type
    return {
        "code_key": f"{ct}:{code}",
        "code_type": ct,
        "code": code,
        "name": _clean(rec.get("name")),
        "long_name": _clean(rec.get("long_name")),
        "chapter": chapter_of(code),
        "category": category_of(code),
        "billable": "",                     # not derivable from the search API
        "source_endpoint": spec.key,
    }


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    res = NormalizeResult()
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        row = _icd10_row(rec, spec)
        if row is None:
            continue
        res.add(spec.target_table, row)
        res.codes.add(row["code"])
        res.note_unmapped([k for k in rec.keys() if k not in _KNOWN_KEYS])
    return res


def _clean(value: Any) -> str:
    return " ".join(str(value).split()) if value not in (None, "") else ""
