"""NEW-21 Unit-economics spine (normalized log-scale comparison).

The capstone reference exhibit: one normalized spine that ties every healthcare
vertical together so a single chart can compare the dollar cost of "treating one
patient" across more than four orders of magnitude, from a hospice routine
home-care day to a one-time gene therapy.

Each vertical stores its natural unit (per diem, per discharge, per 30-day
period, per treatment, per RVU, per cycle, per visit, and so on) and a dollar
figure that is either a verified point value tied to a 2026 final-rule citation
or a range drawn from a secondary source. Range rows and secondary-source rows
are flagged so a surface renders them as ranges, not as charted points, until a
primary source is confirmed.

The representative value used for the log axis is the geometric mean of the low
and high bounds (the natural center on a log scale); for a point value the low
and high are equal so the representative is the value itself.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-21"

# A figure that spans this many orders of magnitude or more earns the headline
# log-scale flag; the published spine spans about five.
ORDERS_OF_MAGNITUDE_FLAG = 4.0


@dataclass(frozen=True)
class SpineRow:
    """One vertical on the spine.

    ``low`` and ``high`` are the dollar bounds of the natural unit; they are
    equal for a verified point value. ``est_verify`` marks a secondary-source
    figure that must be validated against a primary source before it is charted
    as a point. ``payment_system`` color-codes the row.
    """

    vertical: str
    natural_unit: str
    low: float
    high: float
    payment_system: str
    source: str
    vintage: str
    est_verify: bool = False
    note: str = ""

    @property
    def is_range(self) -> bool:
        return self.high > self.low

    @property
    def representative(self) -> float:
        """Geometric mean of the bounds, the natural center on a log axis."""
        return math.sqrt(self.low * self.high)

    def validate(self) -> "SpineRow":
        if self.low <= 0 or self.high <= 0:
            raise ValueError(f"{self.vertical}: figures must be positive")
        if self.high < self.low:
            raise ValueError(f"{self.vertical}: high {self.high} below low {self.low}")
        return self


# The master spine. Verified 2026 final-rule anchors carry est_verify=False and
# a rule citation; range and secondary-source rows carry est_verify=True.
SPINE: List[SpineRow] = [
    # Verified Medicare anchors (2026 final rules).
    SpineRow("Hospice routine home care days 1 to 60", "per diem", 230.83, 230.83,
             "Hospice PPS", "CMS-1835-F", "FY2026"),
    SpineRow("Hospice routine home care days 61 plus", "per diem", 181.94, 181.94,
             "Hospice PPS", "CMS-1835-F", "FY2026"),
    SpineRow("Hospice continuous home care", "per day", 1674.29, 1674.29,
             "Hospice PPS", "CMS-1835-F", "FY2026", note="69.76 per hour, also the SIA rate"),
    SpineRow("Hospice inpatient respite care", "per diem", 532.48, 532.48,
             "Hospice PPS", "CMS-1835-F", "FY2026"),
    SpineRow("Hospice general inpatient care", "per diem", 1199.86, 1199.86,
             "Hospice PPS", "CMS-1835-F", "FY2026"),
    SpineRow("Home health 30-day period", "per 30-day period", 2038.22, 2038.22,
             "HH PPS / PDGM", "CMS-1828-F", "CY2026"),
    SpineRow("Inpatient hospital operating standardized amount", "per discharge",
             6752.61, 6752.61, "IPPS", "CMS-1833-F", "FY2026",
             note="multiplied by the MS-DRG weight; from final-rule addenda"),
    SpineRow("Hospital outpatient conversion factor", "per service", 91.415, 91.415,
             "OPPS", "CMS-1834-FC", "CY2026"),
    SpineRow("Ambulatory surgical center conversion factor", "per case", 56.322, 56.322,
             "ASC PPS", "CMS-1834-FC", "CY2026"),
    SpineRow("Physician services conversion factor", "per RVU", 33.5675, 33.5675,
             "PFS", "CMS-1832-F", "CY2026",
             note="qualifying APM participant rate; non-QP rate is 33.4009"),
    SpineRow("ESRD dialysis bundled base rate", "per treatment", 281.71, 281.71,
             "ESRD PPS", "CMS-1830-F", "CY2026", note="AKI rate identical"),
    SpineRow("Inpatient rehab standard payment", "per discharge", 19371.0, 19371.0,
             "IRF PPS", "CMS-1829-F", "FY2026",
             note="from final-rule addenda; confirm against IRF final rule"),
    SpineRow("Long-term acute care standard federal rate", "per discharge",
             50824.51, 50824.51, "LTCH PPS", "CMS-1833-F", "FY2026"),
    SpineRow("Inpatient psych base per diem", "per diem", 892.87, 892.87,
             "IPF PPS", "FY2026 IPF final rule", "FY2026",
             note="ECT is 673.85 per treatment"),
    # Sourced ranges (list prices, not net; flagged as ranges, not estimates).
    SpineRow("CAR-T cell therapy", "per treatment", 400000.0, 475000.0,
             "WAC / commercial", "Bloomberg, BioSpace, ICER 2024", "2024",
             note="WAC list price, not net of rebates; Yescarta list near 373000"),
    SpineRow("Gene therapy one-time treatment", "per treatment", 2125000.0, 4250000.0,
             "WAC / commercial", "ICER 2024, Bloomberg", "2024",
             note="WAC list price; Zolgensma near 2.125M, Lenmeldy 4.25M"),
    # Secondary-source estimates: validate before charting as a point value.
    SpineRow("Skilled nursing Medicaid", "per patient-day", 250.0, 450.0,
             "State Medicaid", "State plan rates", "2025/26", est_verify=True),
    SpineRow("Retail or urgent care", "per visit", 150.0, 300.0,
             "Commercial / cash", "Industry estimate", "2025/26", est_verify=True),
    SpineRow("Direct primary care", "per member per month", 65.0, 100.0,
             "Membership", "Industry estimate", "2025/26", est_verify=True),
    SpineRow("IVF or fertility", "per cycle", 12000.0, 25000.0,
             "Cash / commercial", "FertilityIQ, GoodRx, SoFi 2025", "2025", est_verify=True),
    SpineRow("ABA therapy", "per 15-minute unit", 15.0, 30.0,
             "Commercial / Medicaid", "Industry estimate", "2025/26", est_verify=True),
    SpineRow("Non-emergency medical transport", "per trip", 25.0, 50.0,
             "Medicaid / MCO", "Industry estimate", "2025/26", est_verify=True,
             note="ambulatory; wheelchair or stretcher higher"),
    SpineRow("Behavioral health outpatient", "per session", 100.0, 200.0,
             "PFS / commercial", "Industry estimate", "2025/26", est_verify=True),
    SpineRow("Dental orthodontia", "per case", 5000.0, 7000.0,
             "Cash / commercial / Medicaid", "Industry estimate", "2025/26", est_verify=True),
    SpineRow("Ambulance BLS base", "per transport", 260.0, 290.0,
             "Medicare Ambulance Fee Schedule", "CMS AFS PUF 2025/26", "2025/26",
             est_verify=True, note="plus mileage, locality adjusted"),
    SpineRow("Telehealth remote patient monitoring", "per patient-month", 100.0, 100.0,
             "PFS", "CMS PFS, Prevounce, ThoroughCare 2025/26", "2025/26", est_verify=True),
]


def unit_economics_spine(
    rows: Optional[Sequence[SpineRow]] = None,
    *,
    include_estimates: bool = True,
    source: str = "Healthcare unit-economics master spine",
    vintage: str = "2025/26",
    audience: str = "both",
) -> Exhibit:
    """Build the normalized log-scale unit-economics comparison.

    ``rows`` defaults to the master :data:`SPINE`. ``include_estimates`` keeps
    the secondary-source rows in the chart (still flagged); set it False to chart
    only the verified anchors.
    """
    table = list(rows) if rows is not None else list(SPINE)
    if not include_estimates:
        table = [r for r in table if not r.est_verify]
    if not table:
        raise ValueError("unit_economics_spine requires at least one row")
    for r in table:
        r.validate()

    # Sort ascending by representative value so the log axis reads low to high.
    table = sorted(table, key=lambda r: r.representative)

    points: List[Dict[str, Any]] = []
    for r in table:
        rep = r.representative
        points.append({
            "label": r.vertical,
            "natural_unit": r.natural_unit,
            "value": rep,
            "low": r.low,
            "high": r.high,
            "log10": math.log10(rep),
            "is_range": r.is_range,
            "payment_system": r.payment_system,
            "est_verify": r.est_verify,
            "source": r.source,
            "vintage": r.vintage,
            "note": r.note,
        })

    reps = [p["value"] for p in points]
    min_rep, max_rep = min(reps), max(reps)
    span = math.log10(max_rep) - math.log10(min_rep)
    payment_systems = sorted({r.payment_system for r in table})
    n_estimates = sum(1 for r in table if r.est_verify)
    n_ranges = sum(1 for r in table if r.is_range)

    flags: List[Flag] = []
    if span >= ORDERS_OF_MAGNITUDE_FLAG:
        flags.append(Flag(
            code="log_scale_required",
            severity="info",
            message=(
                f"Figures span {span:.1f} orders of magnitude, from {min_rep:,.2f} "
                f"to {max_rep:,.0f}. Chart on a log axis."
            ),
            source=source,
        ))
    if n_estimates:
        flags.append(Flag(
            code="estimates_present",
            severity="warn",
            message=(
                f"{n_estimates} verticals are secondary-source estimates shown as "
                "ranges. Verify against a primary source before charting as a point."
            ),
            source=source,
        ))

    # Self-consistent reconciliations that hold for any valid input: the
    # representative sits inside its bounds, and the span is the log ratio of the
    # extremes.
    n_within = sum(1 for r in table if r.low <= r.representative <= r.high)
    reconciliations = [
        Reconciliation(
            identity="representative value lies within the low and high bounds",
            lhs=n_within,
            rhs=len(table),
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="order-of-magnitude span equals log of max over min",
            lhs=span,
            rhs=math.log10(max_rep / min_rep),
            tolerance=1e-9,
        ),
    ]

    series = [Series(name="Unit economics by vertical", kind="bar", points=points)]

    footnote = Footnote(
        source=source,
        vintage=vintage,
        assumptions=[
            "The representative value is the geometric mean of the low and high bounds.",
            "Verified rows are 2026 final-rule anchors; ranges are charted low to high.",
            "Secondary-source rows are flagged and shown as ranges, not points.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Healthcare unit economics on one normalized spine",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(table)} verticals from {min_rep:,.2f} to {max_rep:,.0f} per "
            f"natural unit, spanning {span:.1f} orders of magnitude."
        ),
        meta={
            "log_scale": True,
            "min_representative": min_rep,
            "max_representative": max_rep,
            "orders_of_magnitude": span,
            "payment_systems": payment_systems,
            "n_rows": len(table),
            "n_ranges": n_ranges,
            "n_estimates": n_estimates,
            "table": points,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return unit_economics_spine(
        source="Healthcare unit-economics master spine, 2026 final rules",
        vintage="2025/26",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Unit-economics spine (normalized log-scale comparison)",
        audience="both",
        demo=_demo,
    )
)
