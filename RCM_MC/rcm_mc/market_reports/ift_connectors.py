"""IFT data-connector estate map — every public-data hook the study can pull.

The IFT study rests on GOV/SOURCED anchors, but most of the deep public data
(the ambulance supplier universe, the aging-demand catchment, the facility
origin/destination universe, chronic-disease severity, rural mileage add-ons,
hospital-capacity occupancy, coverage policy) lives behind the network-gated
connector estate (:mod:`rcm_mc.data_public.connector_estate`, 16 connectors /
200+ datasets). :mod:`ift_analytics` already wired three of these hooks
(Part B ambulance utilization, NEMT coverage, BLS employment); this module is
the *complete* map — one declarative registry of every IFT-relevant connector,
each probed degrade-safe.

The contract mirrors the rest of the IFT spine:

* every probe **degrades, never raises** — offline it reads ``network-gated``
  and cites an honest GOV/ACADEMIC fallback, never a fabricated number;
* the wiring is **real** — each ``dataset_id`` is a registered estate dataset
  (verified against :func:`connector_estate.dataset_owner`), so the same probe
  flips to ``SOURCED`` the moment the estate is ingested;
* honesty **travels** — every record carries what it yields for IFT, its
  status, and its source-or-fallback citation.

The output feeds the workbook's "Data connectors & estate" sheet and the
interactive pages' live-estate section, so a partner sees exactly which signals
are live vs ingest-ready and where each one comes from.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── NUCC transportation taxonomies — the ambulance/NEMT supplier fingerprints ─
# NUCC Health Care Provider Taxonomy (Transportation Services §3416/§3438/§3439).
# These are DATA values (passed as filters), not connector constants — the
# supplier universe is enumerated in CMS NPPES against them.
_AMBULANCE_TAXONOMIES: Tuple[str, ...] = (
    "341600000X",   # Ambulance
    "3416L0300X",   # Ambulance — Land Transport
    "3416A0800X",   # Ambulance — Air Transport
    "3416S0300X",   # Ambulance — Water Transport
)
_NEMT_TAXONOMIES: Tuple[str, ...] = (
    "343900000X",   # Non-emergency Medical Transport (VAN)
    "343800000X",   # Secured Medical Transport (VAN)
)

# CDC Chronic Disease Indicators topics that generate interfacility transport.
_IFT_CDI_TOPICS: Tuple[str, ...] = (
    "Cardiovascular Disease", "Diabetes", "Chronic Kidney Disease",
)

# CMS Market Saturation service-type literals (verified at ingest; degrade to the
# GOV citation if the label misses).
_AMBULANCE_SERVICE_TYPES: Tuple[str, ...] = (
    "Ambulance (Emergency)", "Ambulance (Non-Emergency)",
)


# ── the estate-probe wrapper (degrade-never-raise) ───────────────────────────
def _estate_probe(dataset_id: str, group_by: Any,
                  filters: Optional[Dict[str, Any]] = None,
                  metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    """Wrap ``connector_estate.aggregate`` and return its payload (offline it
    reports count=0 / rows=[]). Never raises — one degrade-safe path for every
    hook, exactly like :func:`ift_analytics._estate_probe`."""
    try:
        from ..data_public import connector_estate as ce
        kwargs: Dict[str, Any] = {}
        if metrics:
            kwargs["metrics"] = list(metrics)
        return ce.aggregate(dataset_id, group_by=group_by,
                            filters=filters or None, **kwargs)
    except Exception:  # noqa: BLE001
        return {"count": 0, "rows": []}


def _cli_hint(dataset_id: str) -> str:
    """Copy-ready CLI one-liner that queries the ingested db for this dataset,
    or '' offline. Never raises."""
    try:
        from ..data_public import connector_estate as ce
        return ce.cli_query_hint(dataset_id)
    except Exception:  # noqa: BLE001
        return ""


# ── the probe spec + result records ──────────────────────────────────────────
@dataclass(frozen=True)
class _ProbeSpec:
    """A declarative connector probe. ``group_by`` / ``filters`` / ``metrics``
    are the estate query the probe runs once ingested; offline they are inert
    (the probe degrades to the fallback citation)."""
    key: str
    title: str
    connector: str
    dataset_id: str
    category: str          # Supply | Demand | Facilities | Reimbursement |
                           # Coverage | Clinical | Rural
    tier: int              # 1 strongest … 3 supporting
    ift_signal: str        # what SOURCED signal it yields for IFT
    sourced_label: str     # the SOURCED source_label once ingested
    fallback_citation: str # the honest GOV/ACADEMIC citation offline
    group_by: Any = "state"
    # A MULTI-VALUE filter MUST use the estate grammar's ``field__in`` key — a
    # plain ``{"code": [list]}`` compiles to ``WHERE code = '[...]'`` (equality
    # against the list's repr) and matches ZERO rows even after ingest, so the
    # hook would stay 'network-gated' forever. Scalars use a plain key.
    filters: Optional[Dict[str, Any]] = None
    metrics: Optional[Tuple[str, ...]] = None
    note: str = ""


@dataclass(frozen=True)
class ConnectorProbe:
    """A probed connector — SOURCED (rows present) or network-gated (fallback)."""
    key: str
    title: str
    connector: str
    dataset_id: str
    category: str
    tier: int
    ift_signal: str
    available: bool
    n_rows: int
    status: str            # human status string
    basis: str             # SOURCED | CONNECTOR (network-gated)
    source_label: str      # the live source_label OR the fallback citation
    fallback_citation: str
    note: str
    group_by: str
    cli_hint: str


# ── the registry — every IFT-relevant connector, declaratively ───────────────
# dataset_ids are all registered (checked against connector_estate.dataset_owner),
# so each probe is SOURCED-when-ingested; offline they cite the GOV/ACADEMIC
# fallback. Ordered by category then tier for a readable estate map.
_SPECS: Tuple[_ProbeSpec, ...] = (
    # ── Supply: who can run the transports ──
    _ProbeSpec(
        key="ambulance_suppliers", title="Ambulance supplier universe (NPPES)",
        connector="npi_registry", dataset_id="npi_provider_taxonomy",
        category="Supply", tier=1,
        ift_signal="Active ambulance suppliers per state + land/air/water modality "
                   "mix — the supplier-side TAM and fragmentation map (pairs with "
                   "BLS 621910 establishments for a supplier ÷ establishment check).",
        group_by="state",
        filters={"code__in": list(_AMBULANCE_TAXONOMIES), "is_primary": "1"},
        sourced_label="SOURCED · CMS NPPES provider taxonomy (NUCC §341600000X "
                      "Ambulance land/air/water)",
        fallback_citation="GOV · NUCC Health Care Provider Taxonomy v24.1, "
                          "Transportation §341600000X (Ambulance) + CMS NPPES "
                          "(NPI Final Rule, 45 CFR 162.406)",
        note="Land ambulance (3416L0300X) is the IFT-relevant modality; the "
             "supplier count is the fragmentation denominator behind the moat.",
    ),
    _ProbeSpec(
        key="nemt_van_suppliers", title="NEMT van-transport suppliers (NPPES)",
        connector="npi_registry", dataset_id="npi_provider_taxonomy",
        category="Supply", tier=2,
        ift_signal="Non-emergency van / secured-transport supplier count per state "
                   "— the ADJACENT (not substitute) NEMT field that a whole-"
                   "ambulance number wrongly folds into the IFT prize.",
        group_by="state",
        filters={"code__in": list(_NEMT_TAXONOMIES), "is_primary": "1"},
        sourced_label="SOURCED · CMS NPPES provider taxonomy (NUCC §3439/§3438 "
                      "NEMT van)",
        fallback_citation="GOV · NUCC Taxonomy §343900000X (Non-emergency Medical "
                          "Transport, VAN) / §343800000X (Secured Medical Transport) "
                          "— a separate Medicaid benefit, EXCLUDED from IFT TAM",
        note="Surfaced to make the IFT-vs-NEMT boundary auditable, not to add it "
             "to the ambulance market.",
    ),
    _ProbeSpec(
        key="ambulance_market_saturation",
        title="Ambulance market saturation (CMS)",
        connector="cms_open_data",
        dataset_id="cms_open_data_market_saturation_state_county",
        category="Supply", tier=1,
        ift_signal="County/state ambulance provider counts, FFS user counts, "
                   "penetration % and Medicare payment — the best geographic "
                   "supply-vs-demand + fraud-moratorium lens for non-emergent IFT.",
        group_by=["state", "type_of_service"],
        filters={"type_of_service__in": list(_AMBULANCE_SERVICE_TYPES)},
        metrics=("sum:number_of_providers", "sum:number_of_users",
                 "sum:total_payment"),
        sourced_label="SOURCED · CMS Market Saturation & Utilization, Ambulance "
                      "(Emergency/Non-Emergency)",
        fallback_citation="GOV · CMS Market Saturation & Utilization "
                          "(data.cms.gov) — Ambulance service-type provider counts, "
                          "FFS penetration & payment; fraud-moratorium 42 CFR 424.570",
        note="The moratorium history is highly material to non-emergent ambulance "
             "markets — a diligence red-flag screen.",
    ),
    _ProbeSpec(
        key="ambulance_enrollment", title="Ambulance supplier enrollment (PECOS)",
        connector="cms_open_data",
        dataset_id="cms_open_data_ffs_provider_enrollment",
        category="Supply", tier=2,
        ift_signal="Medicare-enrolled ambulance suppliers by state — an "
                   "enrollment cross-check on the NPPES count; NPPES–PECOS "
                   "divergence is itself a diligence signal.",
        group_by="state_cd",
        filters={"provider_type_desc": "AMBULANCE SERVICE SUPPLIER"},
        sourced_label="SOURCED · CMS Medicare FFS Public Provider Enrollment "
                      "(PECOS), Ambulance Service Supplier",
        fallback_citation="GOV · CMS Medicare FFS Public Provider Enrollment "
                          "(PECOS), provider type Ambulance Service Supplier "
                          "(42 CFR 424 Subpart P)",
    ),
    _ProbeSpec(
        key="ambulance_employment", title="Ambulance employment & wages (BLS)",
        connector="bls_qcew", dataset_id="bls_qcew_industry_area",
        category="Supply", tier=2,
        ift_signal="Establishments, employment and total wages for NAICS 621910 "
                   "(Ambulance Services) — labor is ~69% of ground cost (GADCS), "
                   "the binding constraint behind IFT unit economics.",
        group_by="industry_code", filters={"industry_code": "621910"},
        sourced_label="SOURCED · BLS QCEW NAICS 621910 (Ambulance Services)",
        fallback_citation="GOV · BLS Quarterly Census of Employment and Wages, "
                          "NAICS 621910 (Ambulance Services) — establishment / "
                          "employment / total wages",
    ),
    # ── Demand: who needs to move ──
    _ProbeSpec(
        key="aging_demand", title="Aging catchment (Census ACS 65+)",
        connector="census_acs", dataset_id="census_acs_county_profile",
        category="Demand", tier=1,
        ift_signal="65+ population and 65+ share by county/state/CBSA — the "
                   "primary structural demand driver for discharge, SNF↔hospital "
                   "and dialysis transports.",
        group_by="state_fips",
        metrics=("sum:pop_65_plus", "sum:total_pop"),
        sourced_label="SOURCED · U.S. Census ACS 5-year, table S0101 age 65+",
        fallback_citation="GOV · U.S. Census Bureau ACS 5-year (2023 vintage), "
                          "table S0101 age 65+ (var S0101_C01_030E)",
        note="Estate carries 65+ only (no 85+ variable) — the oldest-old cut "
             "would need a new ACS variable; do not promise 85+.",
    ),
    _ProbeSpec(
        key="dialysis_demand", title="Dialysis demand (ESRD beneficiaries)",
        connector="cms_open_data",
        dataset_id="cms_open_data_medicare_monthly_enrollment",
        category="Demand", tier=2,
        ift_signal="ESRD beneficiary population by state — thrice-weekly dialysis "
                   "transport is one of the largest recurring non-emergent IFT/"
                   "NEMT demand pools.",
        # the monthly-enrollment table names its state column bene_state_abrvtn
        # (no plain `state`), so grouping on `state` would QueryError and the
        # probe would never light up once ingested.
        group_by="bene_state_abrvtn",
        metrics=("sum:aged_esrd_benes", "sum:dsbld_esrd_and_esrd_only_benes"),
        sourced_label="SOURCED · CMS Medicare Monthly Enrollment (ESRD "
                      "beneficiaries)",
        fallback_citation="GOV · CMS Medicare Monthly Enrollment — ESRD "
                          "beneficiaries; ESRD PPS 42 CFR 413 Subpart H",
    ),
    _ProbeSpec(
        key="hospital_service_area",
        title="Hospital catchment / patient flow (CMS)",
        connector="cms_open_data",
        dataset_id="cms_open_data_hospital_service_area",
        category="Demand", tier=2,
        ift_signal="Hospital→patient-ZIP flow matrix — the catchment that "
                   "determines IFT trip distances and inter-hospital transfer "
                   "corridors.",
        group_by="medicare_prov_num", metrics=("sum:total_cases",),
        sourced_label="SOURCED · CMS Hospital Service Area File (provider × "
                      "patient ZIP)",
        fallback_citation="GOV · CMS Hospital Service Area File (data.cms.gov) — "
                          "Medicare FFS discharges by provider × patient ZIP",
    ),
    # ── Facilities: the origin/destination universe ──
    _ProbeSpec(
        key="hospital_universe", title="Hospital universe (origins)",
        connector="provider_data", dataset_id="provider_data_hospital_general",
        category="Facilities", tier=1,
        ift_signal="Hospitals by state/type and which have EDs — the IFT origin "
                   "universe; ED-less hospitals are especially transfer-generative.",
        group_by=["state", "hospital_type"],
        sourced_label="SOURCED · CMS Care Compare Hospital General Information",
        fallback_citation="GOV · CMS Provider Data Catalog / Care Compare "
                          "(data.cms.gov/provider-data) — Hospital General "
                          "Information; facility CCN universe",
    ),
    _ProbeSpec(
        key="postacute_universe",
        title="Post-acute universe (SNF/IRF/LTCH/hospice/HHA)",
        connector="provider_data",
        dataset_id="provider_data_nursing_home_provider_info",
        category="Facilities", tier=1,
        ift_signal="SNF (and IRF/LTCH/hospice/HHA) node counts by state — the "
                   "post-acute destination universe; the transfer EDGES between "
                   "these nodes and hospitals ARE the IFT volume.",
        group_by="state",
        sourced_label="SOURCED · CMS Care Compare Nursing Home / IRF / LTCH / "
                      "Hospice / HHA provider files",
        fallback_citation="GOV · CMS Provider Data Catalog — Nursing Home / IRF / "
                          "LTCH / Hospice / Home-Health provider files",
        note="Companion datasets: provider_data_irf_general, "
             "provider_data_ltch_general, provider_data_hospice_general, "
             "provider_data_home_health_agencies.",
    ),
    _ProbeSpec(
        key="dialysis_facilities", title="Dialysis facilities (destinations)",
        connector="provider_data",
        dataset_id="provider_data_dialysis_facilities",
        category="Facilities", tier=2,
        ift_signal="Dialysis-center density by state — the recurring "
                   "non-emergent-transport destination pool.",
        group_by="state",
        sourced_label="SOURCED · CMS Care Compare Dialysis Facilities",
        fallback_citation="GOV · CMS Provider Data Catalog — Dialysis Facility "
                          "file (data.cms.gov/provider-data)",
    ),
    _ProbeSpec(
        key="hospital_capacity",
        title="Hospital inpatient occupancy (HHS Protect)",
        connector="healthdata_gov",
        dataset_id="healthdata_gov_hospital_capacity_state_ts",
        category="Facilities", tier=2,
        ift_signal="State/facility inpatient bed occupancy at CCN grain — the "
                   "same transfer-demand engine the study computes from HCRIS, "
                   "here joinable to the facility universe.",
        group_by="state", metrics=("avg:inpatient_beds_utilization",),
        sourced_label="SOURCED · HHS Protect / healthdata.gov hospital capacity "
                      "(inpatient bed occupancy)",
        fallback_citation="GOV · HHS Protect Unified Hospital Data / "
                          "healthdata.gov hospital capacity — inpatient occupancy "
                          "as transfer-demand proxy (archive frozen 2024-04)",
        note="Vintage: the HHS-Protect series is a frozen archive (2020-01 → "
             "2024-04) — label the vintage; not current.",
    ),
    # ── Reimbursement ──
    _ProbeSpec(
        key="part_b_ambulance",
        title="Medicare Part B ambulance utilization",
        connector="cms_open_data",
        dataset_id="cms_open_data_physician_supplier_procedure_summary",
        category="Reimbursement", tier=1,
        ift_signal="Line-level ambulance-HCPCS utilization & spend (A0426-A0436) "
                   "— the SOURCED spine of the TAM build once ingested; A0426/"
                   "A0428 non-emergent + A0434 SCT are the interfacility "
                   "fingerprints.",
        group_by="hcpcs_cd",
        filters={"hcpcs_cd__in": ["A0426", "A0427", "A0428", "A0429", "A0433",
                                  "A0434", "A0430", "A0431", "A0425", "A0435",
                                  "A0436"]},
        sourced_label="SOURCED · CMS Medicare Part B physician/supplier procedure "
                      "summary (ambulance HCPCS A0426-A0436)",
        fallback_citation="GOV · CMS Medicare Ambulance Fee Schedule (A0426-A0436, "
                          "42 CFR 414.601-617) + MedPAC ambulance chapter (~$4.0B "
                          "Medicare FFS, 2023) + CMS GADCS (BBA 2018 §50203)",
    ),
    _ProbeSpec(
        key="nemt_managed_care",
        title="Medicaid managed-care penetration (NEMT proxy)",
        connector="medicaid_data",
        dataset_id="medicaid_data_managed_care_by_state_2024",
        category="Reimbursement", tier=3,
        ift_signal="Managed-care penetration by state — the best in-estate proxy "
                   "for where NEMT brokerage economics concentrate (NEMT is "
                   "delivered overwhelmingly via MCO/broker contracts).",
        group_by="state",
        sourced_label="SOURCED · CMS Medicaid Managed Care enrollment by state",
        fallback_citation="GOV · CMS Medicaid Managed Care enrollment "
                          "(data.medicaid.gov); NEMT via MCO/broker under "
                          "42 CFR 440.170(a)(4) & 42 CFR 438. NEMT itself is a "
                          "federal Medicaid mandate (42 CFR 431.53), EXCLUDED "
                          "from ambulance IFT",
    ),
    # ── Coverage / regulatory ──
    _ProbeSpec(
        key="ambulance_coverage",
        title="Ambulance coverage policy (LCD/NCD)",
        connector="cms_coverage", dataset_id="cms_coverage_local_lcd",
        category="Coverage", tier=2,
        ift_signal="Local coverage determinations for ambulance services by MAC "
                   "(+ the governing NCD) — the reimbursement-risk screen for the "
                   "highest-denial repetitive scheduled-transport segment.",
        group_by="document_type",
        sourced_label="SOURCED · CMS Medicare Coverage Database — Ambulance LCDs",
        fallback_citation="GOV · CMS Medicare Coverage Database — Ambulance LCDs "
                          "(e.g. L35162) + IOM Pub.100-02 Ch.10; medical-necessity "
                          "coverage rules",
        note="No ambulance-specific registry slice — a title scan over the "
             "coverage documents, not a pinned filter.",
    ),
    # ── Clinical / severity ──
    _ProbeSpec(
        key="chronic_disease",
        title="Chronic-disease & mortality prevalence (CDC)",
        connector="cdc_data", dataset_id="cdc_data_chronic_disease_indicators",
        category="Clinical", tier=2,
        ift_signal="County/state prevalence of the conditions that generate IFT "
                   "(cardiac, diabetes, CKD) — the severity layer under demand; "
                   "CKD prevalence maps to recurring dialysis transport.",
        group_by="locationabbr", filters={"topic__in": list(_IFT_CDI_TOPICS)},
        sourced_label="SOURCED · CDC U.S. Chronic Disease Indicators",
        fallback_citation="GOV · CDC U.S. Chronic Disease Indicators (hksd-2xuw) "
                          "+ PLACES county CKD (KIDNEY measure) — demand-severity "
                          "basis for IFT",
    ),
    _ProbeSpec(
        key="icd10_validation", title="ICD-10-CM code validation",
        connector="icd10", dataset_id="icd10_cm",
        category="Clinical", tier=3,
        ift_signal="Validates that the clinical condition codes in the "
                   "medical-necessity narrative (N18 CKD, I63 stroke, Z99.2 "
                   "dialysis-dependence) are real ICD-10-CM codes — a "
                   "coding-integrity check, not a market number.",
        group_by="code",
        sourced_label="SOURCED · NLM Clinical Tables ICD-10-CM",
        fallback_citation="GOV · NLM Clinical Tables ICD-10-CM (FY2025); code "
                          "validation for ambulance medical-necessity",
    ),
    # ── Rural ──
    _ProbeSpec(
        key="rural_access", title="Rural mileage add-on basis (HRSA HPSA/MUA)",
        connector="hrsa_data", dataset_id="hrsa_data_hpsa_primary_care",
        category="Rural", tier=2,
        ift_signal="Rural-designation density by state — underpins the rural / "
                   "super-rural mileage add-on the fee schedule prices; rural "
                   "share moves blended revenue per transport.",
        group_by=["common_state_abbreviation", "rural_status"],
        filters={"hpsa_status": "Designated"},
        sourced_label="SOURCED · HRSA Data Warehouse HPSA / MUA designations",
        fallback_citation="GOV · HRSA Data Warehouse HPSA/MUA (data.hrsa.gov); "
                          "Medicare ground-ambulance rural + super-rural mileage "
                          "add-ons 42 CFR 414.610(c)(5) (SSA §1834(l))",
    ),
)


# ── public API ───────────────────────────────────────────────────────────────
def _run(spec: _ProbeSpec) -> ConnectorProbe:
    """Probe one connector; SOURCED with rows, else network-gated + fallback."""
    payload = _estate_probe(spec.dataset_id, spec.group_by, spec.filters,
                            list(spec.metrics) if spec.metrics else None)
    rows = payload.get("rows") or []
    n = len(rows)
    available = bool(rows)
    gb = (", ".join(spec.group_by) if isinstance(spec.group_by, (list, tuple))
          else str(spec.group_by))
    return ConnectorProbe(
        key=spec.key, title=spec.title, connector=spec.connector,
        dataset_id=spec.dataset_id, category=spec.category, tier=spec.tier,
        ift_signal=spec.ift_signal, available=available, n_rows=n,
        status=("available (SOURCED)" if available else "network-gated offline"),
        basis=("SOURCED" if available else "CONNECTOR"),
        source_label=(spec.sourced_label if available else spec.fallback_citation),
        fallback_citation=spec.fallback_citation, note=spec.note, group_by=gb,
        cli_hint=_cli_hint(spec.dataset_id))


def connector_estate_map() -> List[ConnectorProbe]:
    """Every IFT-relevant connector, probed degrade-safe, in reading order
    (category → tier). Never raises — a failed probe still lists network-gated."""
    out: List[ConnectorProbe] = []
    for spec in _SPECS:
        try:
            out.append(_run(spec))
        except Exception:  # noqa: BLE001 — never let one probe drop the map
            out.append(ConnectorProbe(
                key=spec.key, title=spec.title, connector=spec.connector,
                dataset_id=spec.dataset_id, category=spec.category,
                tier=spec.tier, ift_signal=spec.ift_signal, available=False,
                n_rows=0, status="network-gated offline", basis="CONNECTOR",
                source_label=spec.fallback_citation,
                fallback_citation=spec.fallback_citation, note=spec.note,
                group_by="", cli_hint=""))
    return out


@dataclass(frozen=True)
class EstateSummary:
    total: int
    available: int
    gated: int
    by_category: Tuple[Tuple[str, int], ...]
    connectors: Tuple[str, ...]
    n_connectors: int


def estate_summary(probes: Optional[List[ConnectorProbe]] = None) -> EstateSummary:
    """Roll up the estate map for a KPI strip / headline. Never raises."""
    probes = probes if probes is not None else connector_estate_map()
    avail = sum(1 for p in probes if p.available)
    cats: Dict[str, int] = {}
    conns: List[str] = []
    for p in probes:
        cats[p.category] = cats.get(p.category, 0) + 1
        if p.connector not in conns:
            conns.append(p.connector)
    # Category order matches the registry's reading order.
    order = ["Supply", "Demand", "Facilities", "Reimbursement", "Coverage",
             "Clinical", "Rural"]
    by_cat = tuple((c, cats[c]) for c in order if c in cats)
    return EstateSummary(
        total=len(probes), available=avail, gated=len(probes) - avail,
        by_category=by_cat, connectors=tuple(conns), n_connectors=len(conns))
