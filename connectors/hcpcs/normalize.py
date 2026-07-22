"""Map raw NLM HCPCS records → the canonical ``dim_hcpcs_code`` row.

Each raw record is a dict of the requested ``df`` fields (``code``,
``display`` and, where present, ``short_desc``/``long_desc``/``obsolete``)
that the connector already assembled; the mapper is *defensive* and never
assumes a field exists.

Cross-cutting derivations done here:
  * ``code_key`` is the idempotency key ``{code_type}:{code}``.
  * ``section`` is the leading letter of the code — the HCPCS Level II
    code family (``A`` transport/supplies, ``E`` DME, ``J`` drugs,
    ``L`` orthotics/prosthetics, ``G``/``Q``/``S``/``T`` temporary, …).
  * ``category`` is the first three characters (letter + two digits),
    the natural grouping grain between section and full code.
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


_KNOWN_KEYS = {"code", "display", "short_desc", "long_desc", "obsolete",
               "code_type"}


def section_of(code: str) -> str:
    """Leading letter of a HCPCS Level II code (the code family)."""
    code = str(code or "").strip()
    return code[0] if code else ""


def category_of(code: str) -> str:
    """The 3-char category (letter + first two digits, e.g. ``J9`` drugs
    chemo range ``J90``)."""
    code = str(code or "").strip()
    return code[:3]


def _hcpcs_row(rec: Dict[str, Any], spec: EndpointSpec) -> Optional[Dict[str, Any]]:
    code = rec.get("code")
    if not code:
        return None
    code = str(code).strip().upper()
    ct = spec.code_type
    return {
        "code_key": f"{ct}:{code}",
        "code_type": ct,
        "code": code,
        "display": _clean(rec.get("display")),
        "short_desc": _clean(rec.get("short_desc")),
        "long_desc": _clean(rec.get("long_desc")),
        "obsolete": _clean(rec.get("obsolete")),
        "section": section_of(code),
        "category": category_of(code),
        "source_endpoint": spec.key,
    }


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    res = NormalizeResult()
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        row = _hcpcs_row(rec, spec)
        if row is None:
            continue
        res.add(spec.target_table, row)
        res.codes.add(row["code"])
        res.note_unmapped([k for k in rec.keys() if k not in _KNOWN_KEYS])
    return res


def _clean(value: Any) -> str:
    return " ".join(str(value).split()) if value not in (None, "") else ""
