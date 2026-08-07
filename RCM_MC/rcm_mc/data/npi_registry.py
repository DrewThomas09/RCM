"""Organization NPIs from the bundled NPPES cache.

What this is, and what it is not
--------------------------------
NPPES holds roughly eight million NPIs. The full dissemination file is
a ~9GB CSV that :mod:`nppes_ingest` is built to stream, and this
environment cannot reach ``download.cms.gov`` to fetch it. What it
*can* reach is a set of NPPES extracts already vendored in this
repository for the ambulance workstream:

  ==============================  ======  ====================================
  file                             NPIs   what it carries
  ==============================  ======  ====================================
  nppes_ambulance_roster          20,401  legal name, d/b/a, city/state/ZIP,
                                          taxonomy, enumeration date
  npi_full_enrichment             13,520  legal name, multi-valued d/b/a,
                                          authorised official, subpart flag
  pecos_ambulance_registry        10,314  PECOS Associate Control ID —
                                          the enrolment grouping key
  ==============================  ======  ====================================

Union: 20,563 organization NPIs, all in the ambulance / EMS taxonomy
family (3416*, 3418*, 3439*). This is a slice of NPPES, not NPPES.
Every number this module reports is scoped to that slice and says so;
none of them should be read as national NPI coverage.

Why it is still worth having
----------------------------
It is the only real NPPES data available offline, and it exercises
exactly the machinery the full ingest will need:

  - **d/b/a matching.** 5,852 of these NPIs carry a d/b/a, and the
    brand lives only there for many of them. Matching legal name alone
    finds 335 systems; adding the d/b/a finds 88 more, a 26% lift.
  - **The PECOS group.** ``PECOS_ASCT_CNTL_ID`` groups NPIs under one
    enrolled organization. It is CMS's own grouping, not an inference,
    and it is the only identifier here that survives a rebrand.
  - **Geography without an address.** These records carry no county,
    so county comes from the ZIP mapping learned in
    :mod:`provider_crosswalk` — which then carries a CBSA.

Precision
---------
A national NPI roster is a much harsher test of a name pattern than
6,123 hospitals are, and matching it naively produces confident
nonsense: eight unrelated ambulance companies named MedStar, a fire
district in Aurora IL, Grady County's board of commissioners. The two
guards in :func:`nppes_ingest.match_organization` — civil-body names
and system footprint — reject 56 of 423 raw matches here, and every
one of the 56 is wrong.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from .nppes_ingest import match_organization

_CACHE = (Path(__file__).resolve().parent.parent / "market_reports"
          / "reference" / "ift_v3_cache")

_ROSTER = "nppes_ambulance_roster"
_ENRICHMENT = "npi_full_enrichment"
_PECOS = "pecos_ambulance_registry"

#: NPPES writes this where a d/b/a was queried and none exists.
_UNAVAILABLE = "<UNAVAIL>"


@dataclass(frozen=True)
class NpiRecord:
    """One organization NPI, merged across the three cached extracts."""

    npi: str
    legal_name: str
    dbas: Tuple[str, ...]
    city: str
    state: str
    zip5: str
    taxonomy_code: str
    enumeration_date: str
    status: str
    #: PECOS Associate Control ID — CMS's own grouping of NPIs under one
    #: enrolled organization. Empty when the NPI is not in the PECOS file.
    pecos_group: str
    provider_type: str

    @property
    def dba(self) -> str:
        """The first d/b/a, which is what a single-value matcher wants."""
        return self.dbas[0] if self.dbas else ""


def _read(name: str) -> Any:
    path = _CACHE / f"{name}.json.gz"
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _split_dbas(*values: Any) -> Tuple[str, ...]:
    """Flatten the d/b/a fields, which are semicolon-delimited lists.

    "LYNCH AMBULANCE;LYNCH EMS" is two names for one organization, and
    either may be the one that carries the brand.
    """
    out: List[str] = []
    for value in values:
        for part in str(value or "").split(";"):
            name = part.strip()
            if name and name != _UNAVAILABLE and name not in out:
                out.append(name)
    return tuple(out)


@lru_cache(maxsize=1)
def load_npi_registry() -> Dict[str, NpiRecord]:
    """NPI -> record, merged across the cached extracts. Empty if absent."""
    roster = _read(_ROSTER)
    if not isinstance(roster, list):
        return {}
    enrichment = {str(r.get("npi") or ""): r
                  for r in (_read(_ENRICHMENT) or [])
                  if isinstance(r, dict)}
    pecos = {str(r.get("NPI") or ""): r
             for r in (_read(_PECOS) or [])
             if isinstance(r, dict)}

    out: Dict[str, NpiRecord] = {}
    for row in roster:
        if not isinstance(row, dict):
            continue
        npi = str(row.get("npi") or "").strip()
        if not npi:
            continue
        extra = enrichment.get(npi, {})
        enrolled = pecos.get(npi, {})
        out[npi] = NpiRecord(
            npi=npi,
            legal_name=str(row.get("org_name")
                           or extra.get("legal_name") or "").strip(),
            dbas=_split_dbas(row.get("dba"), extra.get("dbas")),
            city=str(row.get("city") or extra.get("location_city") or "").strip(),
            state=str(row.get("state")
                      or extra.get("location_state") or "").strip().upper(),
            zip5=str(row.get("zip5") or "").strip()[:5],
            taxonomy_code=str(row.get("primary_taxonomy")
                              or extra.get("primary_taxonomy") or "").strip(),
            enumeration_date=str(row.get("enumeration_date") or "").strip(),
            status=str(extra.get("status") or "").strip(),
            pecos_group=str(enrolled.get("PECOS_ASCT_CNTL_ID") or "").strip(),
            provider_type=str(enrolled.get("PROVIDER_TYPE_DESC") or "").strip(),
        )
    return out


NPI_COLUMNS: Tuple[str, ...] = (
    "npi", "legal_name", "dba", "dba_count", "city", "state", "zip5",
    "taxonomy_code", "enumeration_date", "status",
    "pecos_group", "provider_type",
    "system_id", "system_name", "system_match",
    "county_fips", "cbsa_code", "cbsa_title", "cbsa_type",
)


def _assign() -> pd.DataFrame:
    from .health_systems import UNMAPPED_ID, UNMAPPED_NAME, get_system
    from .provider_crosswalk import _county_by_zip, cbsa_for_county

    registry = load_npi_registry()
    if not registry:
        return pd.DataFrame(columns=list(NPI_COLUMNS))

    zip_to_county = _county_by_zip()
    rows: List[Dict[str, Any]] = []
    for rec in registry.values():
        system_id, basis = match_organization(
            rec.legal_name, rec.dba, rec.state)
        # A record can carry several d/b/a names; the first one is not
        # necessarily the one with the brand on it.
        if not system_id:
            for alt in rec.dbas[1:]:
                system_id, basis = match_organization("", alt, rec.state)
                if system_id:
                    break
        sysdef = get_system(system_id) if system_id else None
        fips = zip_to_county.get(rec.zip5, "")
        cbsa = cbsa_for_county(fips) or {}
        rows.append({
            "npi": rec.npi,
            "legal_name": rec.legal_name,
            "dba": rec.dba,
            "dba_count": len(rec.dbas),
            "city": rec.city,
            "state": rec.state,
            "zip5": rec.zip5,
            "taxonomy_code": rec.taxonomy_code,
            "enumeration_date": rec.enumeration_date,
            "status": rec.status,
            "pecos_group": rec.pecos_group,
            "provider_type": rec.provider_type,
            "system_id": sysdef.system_id if sysdef else UNMAPPED_ID,
            "system_name": sysdef.name if sysdef else UNMAPPED_NAME,
            "system_match": basis if sysdef else "",
            "county_fips": fips,
            "cbsa_code": cbsa.get("cbsa_code", ""),
            "cbsa_title": cbsa.get("cbsa_title", ""),
            "cbsa_type": cbsa.get("cbsa_type", ""),
        })
    return pd.DataFrame(rows, columns=list(NPI_COLUMNS))


@lru_cache(maxsize=1)
def _assigned_cached() -> pd.DataFrame:
    return _assign()


def assign_npi_registry() -> pd.DataFrame:
    """Every cached organization NPI with system, county and CBSA attached."""
    return _assigned_cached().copy()


def npi_registry_coverage() -> List[Tuple[str, int, int]]:
    """``(identifier, resolved, total)`` over the cached NPI slice.

    Deliberately not folded into :func:`provider_crosswalk.crosswalk_coverage`.
    These NPIs carry no CCN, so they are not rows of that crosswalk, and
    reporting them there would turn "0% of hospitals have an NPI" into a
    number that looks better without a single hospital gaining one.
    """
    frame = assign_npi_registry()
    total = len(frame)
    if not total:
        return []

    def filled(col: str) -> int:
        return int(frame[col].astype(str).str.strip().ne("").sum())

    return [
        ("NPI", total, total),
        ("Taxonomy", filled("taxonomy_code"), total),
        ("D/B/A", int((frame["dba_count"] > 0).sum()), total),
        ("PECOS group", filled("pecos_group"), total),
        ("County FIPS", filled("county_fips"), total),
        ("CBSA / MSA", filled("cbsa_code"), total),
        ("Health system", int((frame["system_id"] != "_unmapped").sum()), total),
    ]


def pecos_groups(min_size: int = 2) -> pd.DataFrame:
    """NPIs sharing a PECOS Associate Control ID, largest group first.

    The only ownership grouping in this data that CMS asserts rather
    than we infer. Most groups are a single NPI — the interesting ones
    are the operators running the same enrolment across several NPIs
    and, often, several states.
    """
    frame = assign_npi_registry()
    named = frame[frame["pecos_group"].astype(str).str.strip().ne("")]
    if named.empty:
        return pd.DataFrame(columns=["pecos_group", "npis", "states",
                                     "legal_name", "system_name"])
    out = named.groupby("pecos_group", as_index=False).agg(
        npis=("npi", "size"),
        states=("state", "nunique"),
        legal_name=("legal_name", "first"),
        system_name=("system_name", "first"),
    )
    out = out[out["npis"] >= max(1, int(min_size))]
    return out.sort_values(["npis", "pecos_group"],
                           ascending=[False, True]).reset_index(drop=True)


def _clear_cache() -> None:
    """Test hook."""
    load_npi_registry.cache_clear()
    _assigned_cached.cache_clear()
