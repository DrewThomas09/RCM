"""Map raw QPP payloads → the canonical clinician/organization/benchmark rows.

The connector hands over uniform raw records —
``{"kind": "eligibility"|"benchmark", "npi"/"year", "payload": {...}}`` —
and the mappers here are *defensive*: the QPP API versions its response
shape via Accept headers, so every field access is a ``.get`` and the
full payload is kept verbatim in each row's ``raw`` column. Normalized
columns are the stable read path; ``raw`` is the honest fallback.

Cross-cutting derivations done here:
  * ``npi_year`` / ``org_key`` / ``benchmark_key`` are composed
    idempotency keys, so multi-year history upserts cleanly.
  * an eligibility payload fans out into ONE ``qpp_clinician`` row plus
    one ``qpp_organization`` row per practice organization.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .endpoints import EndpointSpec


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an NPI roster + audit side-channel."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    npis: Set[str] = field(default_factory=set)
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


def _raw(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _clinician_row(npi: str, year: str, data: Dict[str, Any]) -> Dict[str, Any]:
    spec_info = data.get("specialty") if isinstance(data.get("specialty"), dict) else {}
    orgs = data.get("organizations") if isinstance(data.get("organizations"), list) else []
    return {
        "npi_year": f"{npi}:{year}",
        "npi": npi,
        "year": year,
        "first_name": _clean(data.get("firstName")),
        "middle_name": _clean(data.get("middleName")),
        "last_name": _clean(data.get("lastName")),
        "npi_type": _clean(data.get("nationalProviderIdentifierType")),
        "newly_enrolled": _clean(data.get("newlyEnrolled")),
        "specialty_description": _clean(spec_info.get("specialtyDescription")),
        "specialty_type": _clean(spec_info.get("typeDescription")),
        "specialty_category": _clean(spec_info.get("categoryReference")),
        "is_maqi": _clean(data.get("isMaqi")),
        "n_organizations": str(len(orgs)),
        "raw": _raw(data),
        "source_endpoint": "eligibility",
    }


def _organization_rows(npi: str, year: str, data: Dict[str, Any]
                       ) -> List[Dict[str, Any]]:
    orgs = data.get("organizations")
    if not isinstance(orgs, list):
        return []
    rows: List[Dict[str, Any]] = []
    for idx, org in enumerate(orgs):
        if not isinstance(org, dict):
            continue
        apms = org.get("apms") if isinstance(org.get("apms"), list) else []
        vgs = (org.get("virtualGroups")
               if isinstance(org.get("virtualGroups"), list) else [])
        rows.append({
            "org_key": f"{npi}:{year}:{idx}",
            "npi": npi,
            "year": year,
            "org_idx": str(idx),
            "org_name": _clean(org.get("prvdrOrgName") or org.get("orgName")),
            "facility_based": _clean(org.get("isFacilityBased")),
            "apms_count": str(len(apms)),
            "virtual_groups_count": str(len(vgs)),
            "raw": _raw(org),
            "source_endpoint": "organizations",
        })
    return rows


def _benchmark_row(year: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    measure_id = _clean(payload.get("measureId"))
    if not measure_id:
        return None
    perf_year = _clean(payload.get("performanceYear")) or year
    bench_year = _clean(payload.get("benchmarkYear"))
    method = _clean(payload.get("submissionMethod"))
    deciles = payload.get("deciles")
    return {
        "benchmark_key": f"{perf_year}:{measure_id}:{method}:{bench_year}",
        "measure_id": measure_id,
        "performance_year": perf_year,
        "benchmark_year": bench_year,
        "submission_method": method,
        "status": _clean(payload.get("status")),
        "is_topped_out": _clean(payload.get("isToppedOut")),
        "is_inverse": _clean(payload.get("isInverse")),
        "deciles": json.dumps(deciles) if isinstance(deciles, list) else "",
        "raw": _raw(payload),
        "source_endpoint": "benchmarks",
    }


_KNOWN_ELIGIBILITY_KEYS = {
    "npi", "firstName", "middleName", "lastName",
    "nationalProviderIdentifierType", "newlyEnrolled", "specialty",
    "isMaqi", "organizations", "qpStatus", "amsMipsEligibleClinician",
}


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw records for one endpoint into canonical rows.

    An eligibility record fans out into the clinician row AND its
    organization rows regardless of which of the two dataset specs drove
    the fetch — the payload is the same, and writing both keeps a single
    pull complete.
    """
    res = NormalizeResult()
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        payload = rec.get("payload")
        if not isinstance(payload, dict):
            continue
        year = str(rec.get("year") or "")
        if rec.get("kind") == "benchmark" or spec.kind == "benchmarks":
            row = _benchmark_row(year, payload)
            if row is not None:
                res.add("qpp_benchmark", row)
            continue
        npi = str(rec.get("npi") or payload.get("npi") or "").strip()
        if not npi:
            continue
        res.add("qpp_clinician", _clinician_row(npi, year, payload))
        for org_row in _organization_rows(npi, year, payload):
            res.add("qpp_organization", org_row)
        res.npis.add(npi)
        res.note_unmapped(
            [k for k in payload.keys() if k not in _KNOWN_ELIGIBILITY_KEYS])
    return res
