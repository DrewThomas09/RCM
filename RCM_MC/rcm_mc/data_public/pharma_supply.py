"""Pharmaceutical manufacturing, pricing & distribution reference data.

Sourced national/industry reference figures for the pharma supply side:
IRA negotiated Maximum Fair Prices, the gross-to-net bubble, 340B program
size, the Big Three wholesalers, drug-development cost estimates, and
therapy-area net spend. These are *public, named-source* figures (IQVIA,
CMS, Drug Channels Institute, JAMA/Tufts) — NOT this portfolio's data — so
the page discloses its basis with a source/purpose header and flags the
genuinely contested ranges (drug-development cost; market-size definitions).

Figures are static reference values keyed to a vintage; update the vintage
and the values together when a new IQVIA / CMS / Drug Channels release lands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


VINTAGE = "2024–2026 releases (IQVIA Institute, CMS, Drug Channels Institute)"


@dataclass
class NegotiatedDrug:
    """An IRA first-cycle Part D drug with its negotiated Maximum Fair Price.

    ``mfp_discount_pct`` is the announced discount off list (HHS/CMS, Aug 15
    2024); the published band across the 10 drugs is 38%–79%.
    """
    drug: str
    indication: str
    gross_part_d_cost_b: float
    mfp_discount_pct: float


@dataclass
class Wholesaler:
    name: str
    fy_revenue_b: float
    adj_gross_margin_pct: float
    op_margin_pct: float
    note: str


@dataclass
class GrossToNetComponent:
    """One step of the WAC→net bridge (a waterfall). ``value_b`` is positive
    for the starting list value and negative for each reduction; the final
    ``Net`` row is the residual."""
    label: str
    value_b: float
    kind: str  # "start" | "reduction" | "net"


@dataclass
class DevCostEstimate:
    study: str
    year: int
    low_m: float
    point_m: float
    high_m: float


@dataclass
class TherapyArea:
    name: str
    net_spend_b: float


@dataclass
class PharmaSupplyResult:
    vintage: str
    # Headline KPIs
    global_spend_t: float
    us_net_spend_b: float
    us_net_growth_pct: float
    us_list_spend_t: float
    gross_to_net_bubble_b: float
    b340_purchases_b: float
    b340_growth_pct: float
    big_three_revenue_b: float
    specialty_share_pct: float
    negotiated: List[NegotiatedDrug] = field(default_factory=list)
    wholesalers: List[Wholesaler] = field(default_factory=list)
    gross_to_net: List[GrossToNetComponent] = field(default_factory=list)
    dev_costs: List[DevCostEstimate] = field(default_factory=list)
    therapy_areas: List[TherapyArea] = field(default_factory=list)


def compute_pharma_supply() -> PharmaSupplyResult:
    negotiated = [
        NegotiatedDrug("Eliquis", "Anticoagulant (AFib / VTE)", 16.5, 56.0),
        NegotiatedDrug("Jardiance", "Diabetes / heart failure", 7.1, 66.0),
        NegotiatedDrug("Xarelto", "Anticoagulant", 6.0, 62.0),
        NegotiatedDrug("Januvia", "Diabetes (DPP-4)", 4.1, 79.0),
        NegotiatedDrug("Farxiga", "Diabetes / CKD / HF", 3.3, 68.0),
        NegotiatedDrug("Entresto", "Heart failure", 2.9, 53.0),
        NegotiatedDrug("Enbrel", "Autoimmune (TNF)", 2.8, 67.0),
        NegotiatedDrug("Imbruvica", "Blood cancers (BTK)", 2.7, 38.0),
        NegotiatedDrug("Stelara", "Autoimmune (IL-12/23)", 2.6, 66.0),
        NegotiatedDrug("Fiasp / NovoLog", "Insulin aspart", 2.6, 76.0),
    ]
    wholesalers = [
        Wholesaler("McKesson", 309.0, 3.30, 0.70,
                   "FY2024 consolidated revenue ~$309B (+12%)."),
        Wholesaler("Cencora (AmerisourceBergen)", 262.2, 3.19, 0.50,
                   "FY2023 revenue $262.2B (+9.9%); GLP-1 mix pressures margin."),
        Wholesaler("Cardinal Health", 205.0, 3.40, 0.80,
                   "Lost OptumRx (~16% of revenue) in 2023–24."),
    ]
    # WAC→net bridge — illustrative of routine 40–60% branded specialty
    # spreads; the aggregate gross-to-net bubble was $356B in 2024 (DCI).
    gross_to_net = [
        GrossToNetComponent("WAC list value", 100.0, "start"),
        GrossToNetComponent("Rebates to payers/PBMs", -33.0, "reduction"),
        GrossToNetComponent("340B discounts", -10.0, "reduction"),
        GrossToNetComponent("Medicaid rebates", -8.0, "reduction"),
        GrossToNetComponent("Distribution / returns / PAP", -4.0, "reduction"),
        GrossToNetComponent("Net price", 45.0, "net"),
    ]
    dev_costs = [
        DevCostEstimate("DiMasi / Tufts (capitalized + post-approval)", 2014, 2558.0, 2870.0, 2870.0),
        DevCostEstimate("Wouters et al. (JAMA, median)", 2020, 314.0, 985.0, 2800.0),
        DevCostEstimate("Health Affairs replication", 2020, 500.0, 868.0, 2000.0),
        DevCostEstimate("DiMasi / Tufts (prior, 2000$)", 2003, 802.0, 802.0, 802.0),
    ]
    therapy_areas = [
        TherapyArea("Oncology", 250.0),
        TherapyArea("Immunology", 198.0),
        TherapyArea("Antidiabetics", 138.0),
    ]
    return PharmaSupplyResult(
        vintage=VINTAGE,
        global_spend_t=1.6,
        us_net_spend_b=487.0,
        us_net_growth_pct=11.4,
        us_list_spend_t=1.0,
        gross_to_net_bubble_b=356.0,
        b340_purchases_b=81.4,
        b340_growth_pct=23.0,
        big_three_revenue_b=776.0,
        specialty_share_pct=53.0,
        negotiated=negotiated,
        wholesalers=wholesalers,
        gross_to_net=gross_to_net,
        dev_costs=dev_costs,
        therapy_areas=therapy_areas,
    )
