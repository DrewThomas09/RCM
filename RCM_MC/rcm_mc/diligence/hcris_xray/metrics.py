"""Derived-metric engine for HCRIS hospital records.

The raw HCRIS dataset ships per-hospital per-year rows with 24
fields (bed count, payer-day breakouts, gross / net patient
revenue, operating expenses, net income).  Partners benchmark on
*derived* ratios — not raw fields — because the raw fields have
wildly different scale across a 25-bed critical-access hospital
and a 1,200-bed academic medical center.

This module computes ~20 derived metrics that map 1:1 to the
PE-diligence questions partners ask during a hospital deal
walkthrough:

    * Revenue-cycle performance — contractual-allowance rate,
      net-to-gross, net revenue per bed, revenue per patient day
    * Cost structure — operating expense per bed, per patient
      day, per discharge-equivalent
    * Margin — operating margin on NPR, net-income margin,
      expense coverage ratio
    * Mix — Medicare day %, Medicaid day %, payer-diversity
      index (1 - HHI of day mix)
    * Utilization — occupancy rate, avg length of stay proxy,
      bed-turnover velocity

Output is a dataclass ready for peer benchmarking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


@dataclass
class HospitalMetrics:
    """Derived HCRIS metrics for one hospital-year filing."""
    # Identity
    ccn: str
    name: str
    state: str
    city: str = ""
    county: str = ""
    fiscal_year: int = 0
    beds: int = 0

    # Size / utilization
    bed_days_available: float = 0.0
    total_patient_days: float = 0.0
    occupancy_rate: float = 0.0            # patient_days / bed_days_available
    medicare_days: float = 0.0
    medicaid_days: float = 0.0
    medicare_day_pct: float = 0.0
    medicaid_day_pct: float = 0.0
    other_day_pct: float = 0.0             # commercial + self-pay

    # Revenue cycle
    gross_patient_revenue: float = 0.0
    contractual_allowances: float = 0.0
    net_patient_revenue: float = 0.0
    contractual_allowance_rate: float = 0.0   # allowances / gross
    net_to_gross_ratio: float = 0.0           # NPR / gross
    net_revenue_per_bed: float = 0.0
    net_revenue_per_patient_day: float = 0.0

    # Cost / margin
    operating_expenses: float = 0.0
    net_income: float = 0.0
    operating_margin_on_npr: float = 0.0      # (NPR - opex) / NPR
    net_income_margin_on_npr: float = 0.0     # net_income / NPR
    opex_per_bed: float = 0.0
    opex_per_patient_day: float = 0.0

    # Diversification
    payer_diversity_index: float = 0.0        # 1 - HHI of day mix
    is_medicare_heavy: bool = False           # > 50% medicare days
    is_medicaid_heavy: bool = False           # > 30% medicaid days

    # Flags derived for cohorting
    size_cohort: str = ""                     # MICRO / COMMUNITY / REGIONAL / ACADEMIC
    margin_band: str = ""                     # NEGATIVE / THIN / HEALTHY / STRONG

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn,
            "name": self.name,
            "state": self.state,
            "city": self.city,
            "county": self.county,
            "fiscal_year": self.fiscal_year,
            "beds": self.beds,
            "bed_days_available": self.bed_days_available,
            "total_patient_days": self.total_patient_days,
            "occupancy_rate": self.occupancy_rate,
            "medicare_days": self.medicare_days,
            "medicaid_days": self.medicaid_days,
            "medicare_day_pct": self.medicare_day_pct,
            "medicaid_day_pct": self.medicaid_day_pct,
            "other_day_pct": self.other_day_pct,
            "gross_patient_revenue": self.gross_patient_revenue,
            "contractual_allowances": self.contractual_allowances,
            "net_patient_revenue": self.net_patient_revenue,
            "contractual_allowance_rate":
                self.contractual_allowance_rate,
            "net_to_gross_ratio": self.net_to_gross_ratio,
            "net_revenue_per_bed": self.net_revenue_per_bed,
            "net_revenue_per_patient_day":
                self.net_revenue_per_patient_day,
            "operating_expenses": self.operating_expenses,
            "net_income": self.net_income,
            "operating_margin_on_npr": self.operating_margin_on_npr,
            "net_income_margin_on_npr":
                self.net_income_margin_on_npr,
            "opex_per_bed": self.opex_per_bed,
            "opex_per_patient_day": self.opex_per_patient_day,
            "payer_diversity_index": self.payer_diversity_index,
            "is_medicare_heavy": self.is_medicare_heavy,
            "is_medicaid_heavy": self.is_medicaid_heavy,
            "size_cohort": self.size_cohort,
            "margin_band": self.margin_band,
        }


# ────────────────────────────────────────────────────────────────────
# Cohort classification
# ────────────────────────────────────────────────────────────────────

def _size_cohort(beds: int) -> str:
    """PE-convention hospital-size cohort. These bucket boundaries
    match the way partners talk about deals: 'a 300-bed community'
    is a very different animal than a 'small critical-access'."""
    if beds < 50:
        return "MICRO"                     # critical-access / rural
    if beds < 150:
        return "SMALL_COMMUNITY"
    if beds < 300:
        return "COMMUNITY"
    if beds < 500:
        return "REGIONAL"
    return "ACADEMIC_LARGE"


def _margin_band(margin: float) -> str:
    if margin < 0:
        return "NEGATIVE"
    if margin < 0.04:
        return "THIN"
    if margin < 0.12:
        return "HEALTHY"
    return "STRONG"


def _safe_div(num: float, den: float) -> float:
    if not den or den == 0:
        return 0.0
    return num / den


def _payer_diversity_index(shares: List[float]) -> float:
    """1 - HHI of the day mix, normalized to 0..1.

    A single-payer hospital → 0 (no diversity). Perfectly
    balanced across 3 payer classes → ~0.667. Higher is better
    for risk diversification, worse for Medicare-favored economics.
    """
    total = sum(shares) or 1.0
    normed = [s / total for s in shares]
    hhi = sum(s * s for s in normed)
    # HHI ranges from 1/n (perfectly balanced) to 1.0 (all in one)
    return max(0.0, min(1.0, 1.0 - hhi))


def compute_metrics(row: Mapping[str, Any]) -> HospitalMetrics:
    """Compute derived metrics for one HCRIS row."""
    def _f(key: str) -> float:
        v = row.get(key, 0) or 0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    def _i(key: str) -> int:
        try:
            return int(_f(key))
        except (ValueError, TypeError):
            return 0

    def _s(key: str) -> str:
        return str(row.get(key, "") or "")

    beds = _i("beds")
    bed_days_avail = _f("bed_days_available")
    total_pd = _f("total_patient_days")
    medicare_days = _f("medicare_days")
    medicaid_days = _f("medicaid_days")
    gross_npr = _f("gross_patient_revenue")
    allowances = _f("contractual_allowances")
    npr = _f("net_patient_revenue")
    opex = _f("operating_expenses")
    net_income = _f("net_income")

    # Day-mix pcts (prefer row value when present; else derive)
    medicare_pct = _f("medicare_day_pct")
    if not medicare_pct and total_pd:
        medicare_pct = medicare_days / total_pd
    medicaid_pct = _f("medicaid_day_pct")
    if not medicaid_pct and total_pd:
        medicaid_pct = medicaid_days / total_pd
    other_pct = max(0.0, 1.0 - medicare_pct - medicaid_pct)

    op_margin = _safe_div(npr - opex, npr)
    ni_margin = _safe_div(net_income, npr)

    return HospitalMetrics(
        ccn=_s("ccn"),
        name=_s("name"),
        state=_s("state"),
        city=_s("city"),
        county=_s("county"),
        fiscal_year=_i("fiscal_year"),
        beds=beds,
        bed_days_available=bed_days_avail,
        total_patient_days=total_pd,
        occupancy_rate=_safe_div(total_pd, bed_days_avail),
        medicare_days=medicare_days,
        medicaid_days=medicaid_days,
        medicare_day_pct=medicare_pct,
        medicaid_day_pct=medicaid_pct,
        other_day_pct=other_pct,
        gross_patient_revenue=gross_npr,
        contractual_allowances=allowances,
        net_patient_revenue=npr,
        contractual_allowance_rate=_safe_div(allowances, gross_npr),
        net_to_gross_ratio=_safe_div(npr, gross_npr),
        net_revenue_per_bed=_safe_div(npr, beds),
        net_revenue_per_patient_day=_safe_div(npr, total_pd),
        operating_expenses=opex,
        net_income=net_income,
        operating_margin_on_npr=op_margin,
        net_income_margin_on_npr=ni_margin,
        opex_per_bed=_safe_div(opex, beds),
        opex_per_patient_day=_safe_div(opex, total_pd),
        payer_diversity_index=_payer_diversity_index(
            [medicare_pct, medicaid_pct, other_pct],
        ),
        is_medicare_heavy=medicare_pct > 0.50,
        is_medicaid_heavy=medicaid_pct > 0.30,
        size_cohort=_size_cohort(beds),
        margin_band=_margin_band(op_margin),
    )


# ────────────────────────────────────────────────────────────────────
# Metric catalog for the UI — labels, formatting, good/bad direction
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricSpec:
    """UI-side spec for rendering a benchmark row."""
    attr: str
    label: str
    category: str                          # "Size" / "Revenue Cycle" / ...
    format_spec: str                       # ",.0f" or ".1%" etc.
    suffix: str = ""
    higher_is_better: bool = True
    unit_help: str = ""                    # what the units mean

    def fmt(self, value: float) -> str:
        try:
            return format(value, self.format_spec) + self.suffix
        except (ValueError, TypeError):
            return "—"


METRIC_CATALOG: List[MetricSpec] = [
    # Size / utilization
    MetricSpec("beds", "Beds", "Size", ",.0f",
               higher_is_better=True,
               unit_help="licensed bed count"),
    MetricSpec("total_patient_days", "Patient days",
               "Size", ",.0f",
               unit_help="total inpatient days filed"),
    MetricSpec("occupancy_rate", "Occupancy rate",
               "Size", ".1%",
               unit_help="patient days ÷ bed days available"),
    # Payer mix
    MetricSpec("medicare_day_pct", "Medicare day share",
               "Payer Mix", ".1%",
               higher_is_better=False,
               unit_help="share of inpatient days covered by Medicare"),
    MetricSpec("medicaid_day_pct", "Medicaid day share",
               "Payer Mix", ".1%",
               higher_is_better=False,
               unit_help="share of inpatient days covered by Medicaid"),
    MetricSpec("other_day_pct", "Commercial / other day share",
               "Payer Mix", ".1%",
               higher_is_better=True,
               unit_help="commercial + self-pay day share (higher = better economics)"),
    MetricSpec("payer_diversity_index", "Payer diversity",
               "Payer Mix", ".2f",
               higher_is_better=True,
               unit_help="1 − HHI of day mix; 0 = single-payer, 0.67 = balanced across 3"),
    # Revenue cycle
    MetricSpec("net_revenue_per_bed", "NPR per bed",
               "Revenue Cycle", ",.0f",
               suffix=" $",
               higher_is_better=True,
               unit_help="net patient revenue ÷ beds"),
    MetricSpec("net_revenue_per_patient_day",
               "NPR per patient day",
               "Revenue Cycle", ",.0f",
               suffix=" $",
               higher_is_better=True,
               unit_help="net patient revenue ÷ total patient days"),
    MetricSpec("contractual_allowance_rate",
               "Contractual allowance rate",
               "Revenue Cycle", ".1%",
               higher_is_better=False,
               unit_help="contractual allowances ÷ gross patient revenue"),
    MetricSpec("net_to_gross_ratio", "Net-to-gross ratio",
               "Revenue Cycle", ".1%",
               higher_is_better=True,
               unit_help="NPR ÷ gross patient revenue (collection-rate proxy)"),
    # Cost structure
    MetricSpec("opex_per_bed", "Opex per bed",
               "Cost Structure", ",.0f",
               suffix=" $",
               higher_is_better=False,
               unit_help="operating expenses ÷ beds"),
    MetricSpec("opex_per_patient_day",
               "Opex per patient day",
               "Cost Structure", ",.0f",
               suffix=" $",
               higher_is_better=False,
               unit_help="operating expenses ÷ total patient days"),
    # Margin
    MetricSpec("operating_margin_on_npr", "Operating margin",
               "Margin", ".1%",
               higher_is_better=True,
               unit_help="(NPR − opex) ÷ NPR"),
    MetricSpec("net_income_margin_on_npr", "Net income margin",
               "Margin", ".1%",
               higher_is_better=True,
               unit_help="net income ÷ NPR"),
]


def catalog_by_category() -> Dict[str, List[MetricSpec]]:
    out: Dict[str, List[MetricSpec]] = {}
    for m in METRIC_CATALOG:
        out.setdefault(m.category, []).append(m)
    return out
