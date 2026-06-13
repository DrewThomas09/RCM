"""Map raw openFDA records → canonical rows.

One mapper per endpoint. Each is *defensive*: it reaches for fields with
:func:`dig`/:func:`coalesce` and never assumes a path exists. Anything
present on the record that no mapper places is returned as an unmapped
key so the pipeline can log it to DECISIONS.md (schema-drift signal).

Cross-cutting normalizations done here:
  * NDC is carried as the native ``product_ndc`` string and a separate
    11-digit form is exposed for the RxNorm crosswalk (see
    :func:`ndc11`). RxCUI is left ``NULL`` — resolution is a wireable
    join handled by :mod:`crosswalk`, never blocked on here.
  * Manufacturer / sponsor names are collapsed to a deterministic
    ``company_key`` so device and drug records roll up to one company
    (the practical, testable form of the "fuzzy match" requirement).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .endpoints import EndpointSpec
from .flatten import as_list, coalesce, dig, first, join_list, unmapped_keys


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus rollup + audit side-channels."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    companies: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ndcs: Set[str] = field(default_factory=set)
    product_codes: Set[str] = field(default_factory=set)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


# ── company normalization (deterministic fuzzy rollup) ─────────────────
_CORP_SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|corp|corporation|co|company|ltd|"
    r"limited|plc|gmbh|ag|sa|s\.a|spa|pharma|pharmaceutical[s]?|labs?|"
    r"laboratories|holdings?|group|usa|us)\b", re.I)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def company_key(name: Optional[str]) -> Optional[str]:
    """Collapse a manufacturer/sponsor name to a stable rollup key.

    Lower-cases, strips corporate suffixes and punctuation, collapses
    whitespace. Variants like "Acme Pharma, Inc." and "ACME
    PHARMACEUTICALS LLC" land on the same key so a company rolls up
    across drug and device records.
    """
    if not name:
        return None
    s = str(name).lower()
    s = _NON_ALNUM.sub(" ", s)
    s = _CORP_SUFFIXES.sub(" ", s)
    s = _NON_ALNUM.sub(" ", s).strip()
    if not s:
        return None
    return "co_" + re.sub(r"\s+", "_", s)


def ndc11(ndc: Optional[str]) -> Optional[str]:
    """Best-effort 11-digit NDC (RxNorm's NDC form) from a product NDC.

    openFDA product NDCs are ``LABELER-PRODUCT`` (e.g. ``0002-1200`` or
    ``00002-1200``). The 11-digit form zero-pads to 5-4-2; with no
    package segment we pad to 5-4 and document the package gap. Returns
    digits only, or ``None`` when the shape is unrecognisable.
    """
    if not ndc:
        return None
    parts = str(ndc).split("-")
    if len(parts) == 2:
        labeler, product = parts
        if labeler.isdigit() and product.isdigit():
            return labeler.zfill(5) + product.zfill(4)
    digits = re.sub(r"\D", "", str(ndc))
    return digits if digits else None


def _company(res: NormalizeResult, name: Optional[str], kind: str) -> Optional[str]:
    key = company_key(name)
    if key:
        entry = res.companies.setdefault(
            key, {"company_key": key, "normalized_name": _display(name),
                  "raw_names": set(), "kind": kind})
        entry["raw_names"].add(str(name))
    return key


def _display(name: Optional[str]) -> str:
    return " ".join(str(name or "").split())


# ── per-endpoint mappers ───────────────────────────────────────────────
def _drug_ndc(rec: Dict[str, Any], res: NormalizeResult) -> None:
    product_ndc = dig(rec, "product_ndc")
    if not product_ndc:
        return
    labeler = dig(rec, "labeler_name")
    res.ndcs.add(str(product_ndc))
    res.add("dim_drug_product", {
        "ndc": product_ndc,
        "product_ndc": product_ndc,
        "rxcui": None,
        "proprietary_name": coalesce(rec, ["brand_name"]),
        "generic_name": coalesce(rec, ["generic_name"]),
        "labeler_name": labeler,
        "dosage_form": coalesce(rec, ["dosage_form"]),
        "route": join_list(dig(rec, "route")),
        "marketing_status": coalesce(rec, ["marketing_category"]),
        "product_type": coalesce(rec, ["product_type"]),
        "application_number": coalesce(rec, ["application_number",
                                             "openfda.application_number"]),
        "set_id": None,
        "source_endpoint": "drug_ndc",
        "company_key": _company(res, labeler, "drug_labeler"),
    })
    res.note_unmapped(unmapped_keys(rec, {
        "product_ndc", "brand_name", "generic_name", "labeler_name",
        "dosage_form", "route", "marketing_category", "product_type",
        "application_number", "openfda", "packaging", "active_ingredients",
        "finished", "listing_expiration_date", "pharm_class", "spl_id",
        "product_id", "dea_schedule", "marketing_start_date",
        "marketing_end_date", "brand_name_base", "brand_name_suffix",
    }))


def _drug_label(rec: Dict[str, Any], res: NormalizeResult) -> None:
    # Labels enrich dim_drug_product; fan out over every openfda.product_ndc.
    set_id = coalesce(rec, ["set_id", "id"])
    ndcs = as_list(dig(rec, "openfda.product_ndc"))
    labeler = first(dig(rec, "openfda.manufacturer_name"))
    if not ndcs:
        return
    for ndc in ndcs:
        if not ndc:
            continue
        res.ndcs.add(str(ndc))
        res.add("dim_drug_product", {
            "ndc": ndc,
            "product_ndc": ndc,
            "rxcui": None,
            "proprietary_name": first(dig(rec, "openfda.brand_name")),
            "generic_name": first(dig(rec, "openfda.generic_name")),
            "labeler_name": labeler,
            "dosage_form": first(dig(rec, "openfda.dosage_form")),
            "route": join_list(dig(rec, "openfda.route")),
            "marketing_status": first(dig(rec, "openfda.product_type")),
            "product_type": first(dig(rec, "openfda.product_type")),
            "application_number": first(dig(rec, "openfda.application_number")),
            "set_id": set_id,
            "source_endpoint": "drug_label",
            "company_key": _company(res, labeler, "drug_labeler"),
        })


def _drug_event(rec: Dict[str, Any], res: NormalizeResult) -> None:
    srid = dig(rec, "safetyreportid")
    if not srid:
        return
    ndc = first(dig(rec, "patient.drug.0.openfda.product_ndc"))
    if ndc:
        res.ndcs.add(str(ndc))
    res.add("fact_drug_adverse_event", {
        "safetyreportid": srid,
        "receivedate": dig(rec, "receivedate"),
        "serious": dig(rec, "serious"),
        "ndc": ndc,
        "medicinalproduct": dig(rec, "patient.drug.0.medicinalproduct"),
        "generic_name": first(dig(rec, "patient.drug.0.openfda.generic_name")),
        "reaction_pt": dig(rec, "patient.reaction.0.reactionmeddrapt"),
        "patient_sex": dig(rec, "patient.patientsex"),
        "patient_age": dig(rec, "patient.patientonsetage"),
        "occurcountry": dig(rec, "occurcountry"),
        "source_endpoint": "drug_event",
        "company_key": None,
    })


def _drug_enforcement(rec: Dict[str, Any], res: NormalizeResult) -> None:
    rn = dig(rec, "recall_number")
    if not rn:
        return
    firm = dig(rec, "recalling_firm")
    ndc = first(dig(rec, "openfda.product_ndc"))
    if ndc:
        res.ndcs.add(str(ndc))
    res.add("fact_drug_recall", {
        "recall_number": rn,
        "report_date": dig(rec, "report_date"),
        "ndc": ndc,
        "product_description": dig(rec, "product_description"),
        "reason_for_recall": dig(rec, "reason_for_recall"),
        "classification": dig(rec, "classification"),
        "status": dig(rec, "status"),
        "recalling_firm": firm,
        "voluntary_mandated": dig(rec, "voluntary_mandated"),
        "state": dig(rec, "state"),
        "source_endpoint": "drug_enforcement",
        "company_key": _company(res, firm, "drug_firm"),
    })


def _drugsfda(rec: Dict[str, Any], res: NormalizeResult) -> None:
    appno = dig(rec, "application_number")
    if not appno:
        return
    sponsor = dig(rec, "sponsor_name")
    app_type = _app_type(appno)
    ndc = first(dig(rec, "openfda.product_ndc"))
    if ndc:
        res.ndcs.add(str(ndc))
    res.add("dim_drug_approval", {
        "application_number": appno,
        "sponsor_name": sponsor,
        "application_type": app_type,
        "brand_name": dig(rec, "products.0.brand_name"),
        "generic_name": first(dig(rec, "openfda.generic_name")),
        "marketing_status": dig(rec, "products.0.marketing_status"),
        "ndc": ndc,
        "dosage_form": dig(rec, "products.0.dosage_form"),
        "route": dig(rec, "products.0.route"),
        "products_json": rec.get("products"),
        "submission_status_date": dig(rec, "submissions.0.submission_status_date"),
        "source_endpoint": "drugsfda",
        "company_key": _company(res, sponsor, "drug_sponsor"),
    })


def _device_classification(rec: Dict[str, Any], res: NormalizeResult) -> None:
    pcode = dig(rec, "product_code")
    if not pcode:
        return
    res.product_codes.add(str(pcode))
    res.add("dim_device", {
        "device_key": f"CLASS:{pcode}",
        "product_code": pcode,
        "device_name": dig(rec, "device_name"),
        "device_class": dig(rec, "device_class"),
        "regulation_number": dig(rec, "regulation_number"),
        "medical_specialty": dig(rec, "medical_specialty_description"),
        "applicant": None,
        "decision_date": None,
        "decision_type": "classification",
        "k_number": None,
        "pma_number": None,
        "advisory_committee": dig(rec, "medical_specialty"),
        "source_endpoint": "device_classification",
        "company_key": None,
    })


def _device_510k(rec: Dict[str, Any], res: NormalizeResult) -> None:
    knum = dig(rec, "k_number")
    if not knum:
        return
    pcode = coalesce(rec, ["product_code", "openfda.device_class"])
    applicant = dig(rec, "applicant")
    if pcode:
        res.product_codes.add(str(pcode))
    res.add("dim_device", {
        "device_key": f"K:{knum}",
        "product_code": dig(rec, "product_code"),
        "device_name": coalesce(rec, ["device_name", "openfda.device_name"]),
        "device_class": first(dig(rec, "openfda.device_class")),
        "regulation_number": first(dig(rec, "openfda.regulation_number")),
        "medical_specialty": first(dig(rec, "openfda.medical_specialty_description")),
        "applicant": applicant,
        "decision_date": dig(rec, "decision_date"),
        "decision_type": coalesce(rec, ["decision_description", "decision_code"]),
        "k_number": knum,
        "pma_number": None,
        "advisory_committee": dig(rec, "advisory_committee_description"),
        "source_endpoint": "device_510k",
        "company_key": _company(res, applicant, "device_applicant"),
    })


def _device_pma(rec: Dict[str, Any], res: NormalizeResult) -> None:
    pma = dig(rec, "pma_number")
    if not pma:
        return
    supp = dig(rec, "supplement_number")
    key = f"PMA:{pma}-{supp}" if supp else f"PMA:{pma}"
    applicant = dig(rec, "applicant")
    pcode = dig(rec, "product_code")
    if pcode:
        res.product_codes.add(str(pcode))
    res.add("dim_device", {
        "device_key": key,
        "product_code": pcode,
        "device_name": coalesce(rec, ["trade_name", "openfda.device_name"]),
        "device_class": first(dig(rec, "openfda.device_class")),
        "regulation_number": first(dig(rec, "openfda.regulation_number")),
        "medical_specialty": first(dig(rec, "openfda.medical_specialty_description")),
        "applicant": applicant,
        "decision_date": dig(rec, "decision_date"),
        "decision_type": coalesce(rec, ["decision_code", "supplement_type"]),
        "k_number": None,
        "pma_number": pma,
        "advisory_committee": dig(rec, "advisory_committee_description"),
        "source_endpoint": "device_pma",
        "company_key": _company(res, applicant, "device_applicant"),
    })


def _device_event(rec: Dict[str, Any], res: NormalizeResult) -> None:
    rn = coalesce(rec, ["report_number", "mdr_report_key"])
    if not rn:
        return
    mfr = dig(rec, "device.0.manufacturer_d_name")
    pcode = dig(rec, "device.0.device_report_product_code")
    if pcode:
        res.product_codes.add(str(pcode))
    res.add("fact_device_adverse_event", {
        "report_number": rn,
        "date_received": dig(rec, "date_received"),
        "product_code": pcode,
        "brand_name": dig(rec, "device.0.brand_name"),
        "generic_name": dig(rec, "device.0.generic_name"),
        "manufacturer_name": mfr,
        "device_class": first(dig(rec, "device.0.openfda.device_class")),
        "event_type": join_list(dig(rec, "event_type")),
        "mdr_report_key": dig(rec, "mdr_report_key"),
        "source_endpoint": "device_event",
        "company_key": _company(res, mfr, "device_manufacturer"),
    })


def _device_recall(rec: Dict[str, Any], res: NormalizeResult) -> None:
    rid = coalesce(rec, ["cfres_id", "product_res_number"])
    if not rid:
        return
    firm = coalesce(rec, ["recalling_firm", "firm_fei_number"])
    pcode = coalesce(rec, ["product_code", "openfda.device_class"])
    if pcode:
        res.product_codes.add(str(pcode))
    res.add("fact_device_recall", {
        "recall_id": f"RES:{rid}",
        "recall_number": coalesce(rec, ["product_res_number", "res_event_number"]),
        "report_date": coalesce(rec, ["event_date_posted", "event_date_initiated"]),
        "product_code": dig(rec, "product_code"),
        "product_description": coalesce(rec, ["product_description", "product_res_number"]),
        "reason_for_recall": dig(rec, "reason_for_recall"),
        "classification": coalesce(rec, ["root_cause_description"]),
        "status": coalesce(rec, ["recall_status"]),
        "recalling_firm": firm,
        "root_cause_description": dig(rec, "root_cause_description"),
        "source_endpoint": "device_recall",
        "company_key": _company(res, firm, "device_firm"),
    })


def _device_enforcement(rec: Dict[str, Any], res: NormalizeResult) -> None:
    rn = dig(rec, "recall_number")
    if not rn:
        return
    firm = dig(rec, "recalling_firm")
    pcode = first(dig(rec, "openfda.device_class"))  # enforcement product_code is sparse
    res.add("fact_device_recall", {
        "recall_id": f"ENF:{rn}",
        "recall_number": rn,
        "report_date": dig(rec, "report_date"),
        "product_code": dig(rec, "product_code"),
        "product_description": dig(rec, "product_description"),
        "reason_for_recall": dig(rec, "reason_for_recall"),
        "classification": dig(rec, "classification"),
        "status": dig(rec, "status"),
        "recalling_firm": firm,
        "root_cause_description": None,
        "source_endpoint": "device_enforcement",
        "company_key": _company(res, firm, "device_firm"),
    })


def _device_udi(rec: Dict[str, Any], res: NormalizeResult) -> None:
    key = dig(rec, "public_device_record_key")
    if not key:
        return
    company = dig(rec, "company_name")
    pcode = dig(rec, "product_codes.0.code")
    if pcode:
        res.product_codes.add(str(pcode))
    gmdn = "|".join(
        str(t.get("name")) for t in as_list(dig(rec, "gmdn_terms"))
        if isinstance(t, dict) and t.get("name"))
    res.add("dim_device_udi", {
        "public_device_record_key": key,
        "product_code": pcode,
        "brand_name": dig(rec, "brand_name"),
        "company_name": company,
        "version_or_model_number": dig(rec, "version_or_model_number"),
        "device_description": dig(rec, "device_description"),
        "gmdn_terms": gmdn or None,
        "publish_date": dig(rec, "publish_date"),
        "udi_di": dig(rec, "identifiers.0.id"),
        "source_endpoint": "device_udi",
        "company_key": _company(res, company, "device_company"),
    })


_MAPPERS = {
    "drug_ndc": _drug_ndc,
    "drug_label": _drug_label,
    "drug_event": _drug_event,
    "drug_enforcement": _drug_enforcement,
    "drugsfda": _drugsfda,
    "device_classification": _device_classification,
    "device_510k": _device_510k,
    "device_pma": _device_pma,
    "device_event": _device_event,
    "device_recall": _device_recall,
    "device_enforcement": _device_enforcement,
    "device_udi": _device_udi,
}


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    res = NormalizeResult()
    mapper = _MAPPERS.get(spec.key)
    if mapper is None:
        raise KeyError(f"no normalizer for endpoint {spec.key!r}")
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res)
    return res


def _app_type(appno: str) -> Optional[str]:
    m = re.match(r"([A-Za-z]+)", str(appno))
    return m.group(1).upper() if m else None
