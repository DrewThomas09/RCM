"""340B Drug Pricing Analyzer.

Critical for PE platforms with DSH / FQHC / SCH / CAH covered-entity exposure,
oncology practices, and community health platforms. Models:

- Covered entity eligibility (DSH, FQHC, SCH, RRC, CAH, PED, STD clinics,
  Ryan White, Title X family planning)
- Ceiling price vs WAC spread
- Contract pharmacy networks
- Medicaid "carve-in / carve-out" (duplicate-discount prevention)
- Part B drug eligibility
- Program integrity audits / 340B Drug Pricing Program HRSA audits
- Manufacturer restrictions (340B covered-entity pushback)
- Margin capture ($ savings to covered entity)

Key constraints: child sites must pass OPA registration; contract pharmacy
arrangements must pass program integrity audits; carve-out for Medicaid
prevents duplicate discounts; GPO-prohibition for DSH.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Covered entity benchmarks
# ---------------------------------------------------------------------------

_ENTITY_TYPES = {
    "DSH":  {"dsh_pct_min": 11.75, "ceiling_discount": 0.52, "gpo_prohibition": True,  "typical_size_mm": 125},
    "SCH":  {"dsh_pct_min": 8.0,   "ceiling_discount": 0.48, "gpo_prohibition": False, "typical_size_mm": 42},
    "RRC":  {"dsh_pct_min": 8.0,   "ceiling_discount": 0.48, "gpo_prohibition": False, "typical_size_mm": 35},
    "CAH":  {"dsh_pct_min": 0,     "ceiling_discount": 0.44, "gpo_prohibition": False, "typical_size_mm": 8},
    "PED":  {"dsh_pct_min": 0,     "ceiling_discount": 0.55, "gpo_prohibition": True,  "typical_size_mm": 28},
    "FQHC": {"dsh_pct_min": 0,     "ceiling_discount": 0.58, "gpo_prohibition": False, "typical_size_mm": 12},
    "Ryan White": {"dsh_pct_min": 0, "ceiling_discount": 0.62, "gpo_prohibition": False, "typical_size_mm": 9},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CoveredEntity:
    entity_id: str
    entity_type: str
    name: str
    annual_drug_spend_mm: float
    ceiling_price_spread_mm: float
    contract_pharmacy_count: int
    child_sites: int
    program_margin_mm: float
    audit_risk_score: int
    compliance_status: str


@dataclass
class DrugCategory:
    category: str
    annual_volume_units: int
    wac_per_unit: float
    ceiling_price_per_unit: float
    discount_pct: float
    annual_savings_mm: float
    share_of_spend_pct: float


@dataclass
class ContractPharmacy:
    pharmacy_type: str
    location_count: int
    claims_per_month: int
    avg_spread_per_claim: float
    monthly_margin_k: float
    annual_margin_mm: float
    integrity_risk: str


@dataclass
class ComplianceAudit:
    audit_area: str
    finding_severity: str
    exposure_mm: float
    remediation_days: int
    last_hrsa_visit: str
    status: str


@dataclass
class ManufacturerRestriction:
    manufacturer: str
    restricted_products: int
    restriction_type: str
    annual_impact_mm: float
    workaround_available: bool


@dataclass
class MedicaidInteraction:
    state: str
    carve_status: str
    avg_mac_rate: float
    duplicate_discount_risk: str
    gross_margin_mm: float


@dataclass
class Drug340BResult:
    total_covered_entities: int
    total_drug_spend_mm: float
    total_program_savings_mm: float
    total_margin_mm: float
    program_margin_pct: float
    contract_pharmacy_network_size: int
    entities: List[CoveredEntity]
    drugs: List[DrugCategory]
    pharmacies: List[ContractPharmacy]
    audits: List[ComplianceAudit]
    manufacturers: List[ManufacturerRestriction]
    medicaid: List[MedicaidInteraction]
    audit_risk_weighted: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 84):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        deals = _SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_entities(platform_type: str, total_entities: int) -> List[CoveredEntity]:
    import hashlib
    # Platform-specific entity mix
    if platform_type == "Health System":
        mix = [("DSH", 0.20), ("SCH", 0.15), ("RRC", 0.10), ("CAH", 0.20), ("PED", 0.10), ("FQHC", 0.20), ("Ryan White", 0.05)]
    elif platform_type == "FQHC Network":
        mix = [("FQHC", 0.85), ("Ryan White", 0.10), ("PED", 0.05)]
    elif platform_type == "Oncology Group":
        mix = [("PED", 0.40), ("DSH", 0.30), ("SCH", 0.15), ("RRC", 0.15)]
    else:
        mix = [("DSH", 0.30), ("SCH", 0.20), ("FQHC", 0.30), ("CAH", 0.20)]

    rows = []
    compliance_states = ["clean", "clean", "clean", "minor finding", "monitoring"]
    idx = 0
    for etype, share in mix:
        count = max(1, int(total_entities * share))
        bench = _ENTITY_TYPES[etype]
        for i in range(count):
            idx += 1
            h = int(hashlib.md5(f"{etype}{i}".encode()).hexdigest()[:6], 16)
            drug_spend = bench["typical_size_mm"] * (0.75 + (h % 70) / 100)
            spread_mm = drug_spend * bench["ceiling_discount"] * (0.90 + (h % 20) / 100)
            child_sites = (h % 8) + 1 if etype in ("DSH", "FQHC", "PED") else 0
            contract_pharma = (h % 12) + 2 if etype != "CAH" else (h % 4)
            margin = spread_mm * 0.72   # After admin, drug give-back
            audit_risk = 20 + (h % 60)
            compliance = compliance_states[h % len(compliance_states)]
            rows.append(CoveredEntity(
                entity_id=f"CE-{idx:03d}",
                entity_type=etype,
                name=f"{etype} Site {i + 1}",
                annual_drug_spend_mm=round(drug_spend, 2),
                ceiling_price_spread_mm=round(spread_mm, 2),
                contract_pharmacy_count=contract_pharma,
                child_sites=child_sites,
                program_margin_mm=round(margin, 2),
                audit_risk_score=audit_risk,
                compliance_status=compliance,
            ))
    return rows


def _build_drugs(total_spend_mm: float) -> List[DrugCategory]:
    import hashlib
    categories = [
        ("Oncology Biologics", 0.28, 4850, 2280),
        ("Immunology / Biosimilars", 0.18, 3420, 1680),
        ("Antivirals (HIV/Hepatitis)", 0.12, 1850, 820),
        ("Insulin & Diabetes", 0.08, 485, 220),
        ("Respiratory / COPD", 0.07, 320, 148),
        ("Ophthalmology Injectables", 0.09, 2100, 980),
        ("Vaccines", 0.05, 220, 105),
        ("Rare Disease / Orphan", 0.08, 12500, 5850),
        ("Blood Products", 0.03, 1850, 860),
        ("Chronic Mental Health", 0.02, 420, 195),
    ]
    rows = []
    for cat, share, wac, ceiling in categories:
        h = int(hashlib.md5(cat.encode()).hexdigest()[:6], 16)
        spend_in_cat = total_spend_mm * share
        # Volume = spend / wac
        volume = int(spend_in_cat * 1000000 / wac) if wac else 0
        discount = (wac - ceiling) / wac if wac else 0
        savings = volume * (wac - ceiling) / 1000000
        rows.append(DrugCategory(
            category=cat,
            annual_volume_units=volume,
            wac_per_unit=round(wac, 2),
            ceiling_price_per_unit=round(ceiling, 2),
            discount_pct=round(discount, 4),
            annual_savings_mm=round(savings, 2),
            share_of_spend_pct=round(share, 3),
        ))
    return rows


def _build_pharmacies(entity_count: int) -> List[ContractPharmacy]:
    import hashlib
    types = [
        ("Chain (CVS/Walgreens)", 0.35, 680, 48, "low"),
        ("Specialty Pharmacy", 0.20, 320, 185, "medium"),
        ("Independent Community", 0.25, 120, 32, "low"),
        ("Mail-Order", 0.08, 480, 62, "low"),
        ("Oncology TPA-Directed", 0.12, 85, 245, "high"),
    ]
    rows = []
    for ptype, share, claims, spread, risk in types:
        locs = max(1, int(entity_count * share * 4))
        claims_total = claims * locs
        monthly_margin = claims_total * spread / 1000
        annual = monthly_margin * 12 / 1000
        rows.append(ContractPharmacy(
            pharmacy_type=ptype,
            location_count=locs,
            claims_per_month=claims_total,
            avg_spread_per_claim=round(spread, 2),
            monthly_margin_k=round(monthly_margin, 1),
            annual_margin_mm=round(annual, 2),
            integrity_risk=risk,
        ))
    return rows


def _build_audits() -> List[ComplianceAudit]:
    return [
        ComplianceAudit("OPA Registration Currency", "clean", 0, 0, "2024-09-15", "current"),
        ComplianceAudit("Child Site Eligibility Docs", "minor", 180.0, 45, "2024-09-15", "in remediation"),
        ComplianceAudit("Contract Pharmacy Self-Audit", "moderate", 440.0, 90, "2023-11-02", "open"),
        ComplianceAudit("Medicaid Carve-Out Claims", "minor", 125.0, 30, "2024-05-18", "closed"),
        ComplianceAudit("Duplicate Discount Prevention", "clean", 0, 0, "2024-09-15", "current"),
        ComplianceAudit("GPO Prohibition (DSH)", "moderate", 680.0, 60, "2024-02-08", "open"),
        ComplianceAudit("Diversion Risk (340B to Non-Eligible)", "severe", 1240.0, 180, "2023-06-22", "mediating"),
        ComplianceAudit("Manufacturer Dispute Filings", "minor", 85.0, 30, "2024-07-14", "closed"),
    ]


def _build_manufacturers() -> List[ManufacturerRestriction]:
    return [
        ManufacturerRestriction("Eli Lilly", 8, "contract pharmacy ship-to limit", 2.85, True),
        ManufacturerRestriction("Sanofi", 6, "claims-data certification required", 1.92, True),
        ManufacturerRestriction("Novartis", 5, "single contract pharmacy per CE", 2.20, True),
        ManufacturerRestriction("Merck", 4, "340B ID verification", 1.35, True),
        ManufacturerRestriction("Bristol Myers Squibb", 7, "orphan drug exclusion", 3.40, False),
        ManufacturerRestriction("AstraZeneca", 3, "contract pharmacy limit", 1.08, True),
        ManufacturerRestriction("Boehringer Ingelheim", 2, "single CP, no specialty", 0.75, True),
        ManufacturerRestriction("AbbVie", 4, "contract pharmacy limit", 2.65, True),
    ]


def _build_medicaid() -> List[MedicaidInteraction]:
    return [
        MedicaidInteraction("California", "carve-in (actual acquisition cost)", 0.28, "low", 4.85),
        MedicaidInteraction("Texas", "carve-out", 0.52, "low", 8.95),
        MedicaidInteraction("New York", "carve-in (FFP-only)", 0.35, "medium", 3.20),
        MedicaidInteraction("Florida", "carve-out", 0.48, "low", 7.45),
        MedicaidInteraction("Illinois", "carve-in", 0.32, "medium", 2.85),
        MedicaidInteraction("Pennsylvania", "carve-out", 0.46, "low", 5.20),
        MedicaidInteraction("Ohio", "carve-in", 0.30, "high", 1.95),
        MedicaidInteraction("North Carolina", "carve-out", 0.44, "low", 4.15),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_drug_pricing_340b(
    platform_type: str = "Health System",
    total_entities: int = 25,
) -> Drug340BResult:
    corpus = _load_corpus()

    entities = _build_entities(platform_type, total_entities)
    total_spend = sum(e.annual_drug_spend_mm for e in entities)
    drugs = _build_drugs(total_spend)
    pharmacies = _build_pharmacies(len(entities))
    audits = _build_audits()
    manufacturers = _build_manufacturers()
    medicaid = _build_medicaid()

    total_savings = sum(e.ceiling_price_spread_mm for e in entities)
    total_margin = sum(e.program_margin_mm for e in entities)
    total_cp = sum(p.location_count for p in pharmacies)
    audit_risk_wt = sum(e.audit_risk_score * e.annual_drug_spend_mm for e in entities) / total_spend if total_spend else 0

    return Drug340BResult(
        total_covered_entities=len(entities),
        total_drug_spend_mm=round(total_spend, 2),
        total_program_savings_mm=round(total_savings, 2),
        total_margin_mm=round(total_margin, 2),
        program_margin_pct=round(total_margin / total_spend, 4) if total_spend else 0,
        contract_pharmacy_network_size=total_cp,
        entities=entities,
        drugs=drugs,
        pharmacies=pharmacies,
        audits=audits,
        manufacturers=manufacturers,
        medicaid=medicaid,
        audit_risk_weighted=round(audit_risk_wt, 1),
        corpus_deal_count=len(corpus),
    )
