"""Map raw NIH RePORTER records → canonical rows.

One mapper per endpoint family. Each is *defensive*: it reaches for
fields with :func:`dig`/:func:`coalesce` and never assumes a path exists
(subprojects omit organization detail; ``covid_response`` is usually
``null``). Anything present on the record that the mapper does not place
— and is not on the *deliberately dropped* list — is recorded as an
unmapped key so the pipeline can log schema drift.

Cross-cutting normalizations done here:
  * projects key on the native ``appl_id`` (RePORTER's globally unique
    application id — subprojects get their own), so re-ingesting is
    idempotent;
  * ``pub_key`` composes ``{pmid}:{applid}`` because a publication row is
    a *link edge* (one paper ↔ one application) — the same PMID appears
    once per supporting application and both sides are needed for
    uniqueness;
  * nested ``organization`` / ``agency_ic_admin`` / ``geo_lat_lon``
    objects are flattened to scalar columns; person lists
    (``principal_investigators``, ``program_officers``) are joined to
    stable ``"; "``-delimited name strings so they stay LIKE-queryable.

Deliberately dropped (bulky blobs, redundant splits — documented in the
README, excluded from the drift audit): ``abstract_text``, ``phr_text``,
``pref_terms``, ``terms``, ``spending_categories`` (internal numeric
ids), ``project_num_split`` (redundant with ``project_num``),
``agency_ic_fundings`` (per-IC breakdown; ``award_amount`` +
``direct/indirect_cost_amt`` carry the totals).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .endpoints import EndpointSpec
from .flatten import coalesce, dig, join_list, join_people, unmapped_keys


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an unmapped-field audit."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


# Mapped fields + deliberately-dropped blobs (see module docstring); any
# NEW top-level field RePORTER starts returning will show up in the audit.
_PROJECT_KNOWN = {
    "appl_id", "project_num", "core_project_num", "subproject_id",
    "project_serial_num", "fiscal_year", "project_title", "activity_code",
    "award_type", "agency_code", "agency_ic_admin", "funding_mechanism",
    "mechanism_code_dc", "cfda_code", "opportunity_number",
    "full_study_section", "organization", "organization_type", "cong_dist",
    "geo_lat_lon", "contact_pi_name", "principal_investigators",
    "program_officers", "award_amount", "direct_cost_amt",
    "indirect_cost_amt", "award_notice_date", "project_start_date",
    "project_end_date", "budget_start", "budget_end", "is_active", "is_new",
    "arra_funded", "covid_response", "date_added", "project_detail_url",
    "spending_categories_desc",
    # deliberately dropped:
    "abstract_text", "phr_text", "pref_terms", "terms",
    "spending_categories", "project_num_split", "agency_ic_fundings",
}
_PUBLICATION_KNOWN = {"coreproject", "pmid", "applid"}


def _pub_key(pmid: Any, applid: Any) -> str:
    return f"{pmid}:{applid if applid not in (None, '') else ''}"


# ── per-endpoint mappers ───────────────────────────────────────────────
def _project(rec: Dict[str, Any], res: NormalizeResult,
             spec: EndpointSpec) -> None:
    appl_id = dig(rec, "appl_id")
    if appl_id in (None, ""):
        return
    # contact_pi_name arrives padded ("ABALLAY, ALEJANDRO ") — trim it.
    contact_pi = dig(rec, "contact_pi_name")
    res.add("nih_projects", {
        "appl_id": appl_id,
        "project_num": coalesce(rec, ["project_num"]),
        "core_project_num": coalesce(rec, ["core_project_num"]),
        "subproject_id": coalesce(rec, ["subproject_id"]),
        "project_serial_num": coalesce(rec, ["project_serial_num"]),
        "fiscal_year": coalesce(rec, ["fiscal_year"]),
        "project_title": coalesce(rec, ["project_title"]),
        "activity_code": coalesce(rec, ["activity_code"]),
        "award_type": coalesce(rec, ["award_type"]),
        "agency_code": coalesce(rec, ["agency_code"]),
        "agency_ic_admin": coalesce(rec, ["agency_ic_admin.abbreviation",
                                          "agency_ic_admin.code"]),
        "agency_ic_admin_name": coalesce(rec, ["agency_ic_admin.name"]),
        "funding_mechanism": coalesce(rec, ["funding_mechanism"]),
        "mechanism_code_dc": coalesce(rec, ["mechanism_code_dc"]),
        "cfda_code": coalesce(rec, ["cfda_code"]),
        "opportunity_number": coalesce(rec, ["opportunity_number"]),
        "full_study_section": coalesce(rec, ["full_study_section.name",
                                             "full_study_section.srg_code"]),
        "org_name": coalesce(rec, ["organization.org_name"]),
        "org_city": coalesce(rec, ["organization.org_city",
                                   "organization.city"]),
        "org_state": coalesce(rec, ["organization.org_state"]),
        "org_country": coalesce(rec, ["organization.org_country",
                                      "organization.country"]),
        "org_zipcode": coalesce(rec, ["organization.org_zipcode"]),
        "org_dept_type": coalesce(rec, ["organization.dept_type"]),
        "org_uei": coalesce(rec, ["organization.primary_uei"]),
        "org_duns": coalesce(rec, ["organization.primary_duns"]),
        "org_ipf_code": coalesce(rec, ["organization.org_ipf_code"]),
        "organization_type": coalesce(rec, ["organization_type.name"]),
        "cong_dist": coalesce(rec, ["cong_dist"]),
        "org_latitude": coalesce(rec, ["geo_lat_lon.lat"]),
        "org_longitude": coalesce(rec, ["geo_lat_lon.lon"]),
        "contact_pi_name": str(contact_pi).strip() if contact_pi else None,
        "pi_names": join_people(rec.get("principal_investigators")) or None,
        "pi_profile_ids": join_list(
            [dig(p, "profile_id") for p in rec.get("principal_investigators") or []
             if isinstance(p, dict)]) or None,
        "program_officer_names": join_people(rec.get("program_officers")) or None,
        "award_amount": coalesce(rec, ["award_amount"]),
        "direct_cost_amt": coalesce(rec, ["direct_cost_amt"]),
        "indirect_cost_amt": coalesce(rec, ["indirect_cost_amt"]),
        "award_notice_date": coalesce(rec, ["award_notice_date"]),
        "project_start_date": coalesce(rec, ["project_start_date"]),
        "project_end_date": coalesce(rec, ["project_end_date"]),
        "budget_start": coalesce(rec, ["budget_start"]),
        "budget_end": coalesce(rec, ["budget_end"]),
        "is_active": dig(rec, "is_active"),
        "is_new": dig(rec, "is_new"),
        "arra_funded": coalesce(rec, ["arra_funded"]),
        "covid_response": join_list(rec.get("covid_response")) or None,
        "spending_categories_desc": coalesce(rec, ["spending_categories_desc"]),
        "date_added": coalesce(rec, ["date_added"]),
        "project_detail_url": coalesce(rec, ["project_detail_url"]),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _PROJECT_KNOWN))


def _publication(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    pmid = dig(rec, "pmid")
    if pmid in (None, ""):
        return
    applid = dig(rec, "applid")
    res.add("nih_publications", {
        "pub_key": _pub_key(pmid, applid),
        "pmid": pmid,
        "appl_id": applid,
        "core_project_num": coalesce(rec, ["coreproject"]),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _PUBLICATION_KNOWN))


_MAPPERS = {
    "projects": _project,
    "publications": _publication,
}


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    res = NormalizeResult()
    mapper = _MAPPERS.get(spec.key)
    if mapper is None:
        raise KeyError(
            f"no normalizer for endpoint {spec.key!r}; known: {sorted(_MAPPERS)}")
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec)
    return res
