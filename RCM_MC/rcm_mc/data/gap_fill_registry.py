"""Gap → fill-source registry: how each HCRIS metric gap gets filled.

The accuracy loop flags every value we don't have with a subtle red dot
(ck_gap_dot) and counts them (ck_gap_count). This module is the other half:
for each metric that carries gaps, it records WHERE the missing data lives and
what it takes to fill it — researched against the public CMS catalog — so a
red dot is never a dead end, it's a known piece of sourcing work.

Two honest classes of gap:

  • ``external`` / ``reingest`` — the value exists in a public source we don't
    yet pull (the CMS Provider of Services file for bed counts) or in HCRIS
    columns the loader doesn't yet read (the other Worksheet S-3 Medicaid
    columns). These graduate to ``wired`` when a loader lands in an
    environment that can reach the source.

  • ``artifact`` — the value is NOT missing-but-findable; the filing itself is
    internally inconsistent (net patient revenue > gross, opex ≫ revenue,
    patient-days > bed-days). There is no other source to "fill" it from — the
    red dot IS the resolution, and pulling a different number would be
    fabrication. These are recorded so we don't waste sourcing effort on them.

Nothing here downloads at import time; this is a catalog + a census over
already-loaded metrics. Filling is a separate, network-gated step.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class GapFillSource:
    """One metric gap and its researched remediation path."""
    field: str                  # HospitalMetrics attribute that carries the gap
    label: str                  # human label
    fill_kind: str              # "external" | "reingest" | "artifact"
    source: str                 # named public source (or why it's unfillable)
    dataset_id: str = ""        # CMS dataset id / worksheet coordinate, when known
    url: str = ""               # catalog landing page
    access: str = ""            # "open" | "api" | "in-house re-ingest" | "n/a"
    status: str = "registered"  # "registered" | "wired" | "n/a (artifact)"
    note: str = ""


# Researched against data.cms.gov / the CMS provider-data catalog (June 2026).
# Bed counts: CMS Provider of Services (POS) file carries bed_size by CCN; the
# Hospital General Information dataset (xubh-q36u) is the API-served alternative.
# Medicaid days: Worksheet S-3 splits Medicaid days across six columns
# (in/out-of-state paid + eligible-unpaid, Medicaid HMO, other); the loader
# currently sums only column 7 (00700), so filings reporting Medicaid days
# elsewhere read as missing — fillable in-house by summing the other columns
# from the NMRC raw file (coordinates must be ground-truth-verified first).
GAP_FILL_SOURCES: List[GapFillSource] = [
    GapFillSource(
        field="medicaid_day_pct", label="Medicaid day share",
        fill_kind="reingest",
        source="HCRIS Worksheet S-3 Pt I additional Medicaid columns",
        dataset_id="S300001 line 01400 cols 00100-00700 + DSH lines",
        url="https://data.cms.gov/resources/hospital-provider-cost-report-data-dictionary",
        access="in-house re-ingest", status="registered",
        note="Loader sums only col 00700 (Title XIX); sum in/out-of-state "
             "paid+unpaid, HMO and other Medicaid columns to fill ~14.9% of "
             "hospital-years. Verify coordinates against known filings first.",
    ),
    GapFillSource(
        field="beds", label="Licensed beds",
        fill_kind="external",
        source="CMS Provider of Services file (bed_size) / Hospital General Info",
        dataset_id="xubh-q36u",
        url="https://data.cms.gov/provider-data/dataset/xubh-q36u",
        access="api", status="registered",
        note="Backfill the bed count by CCN when HCRIS S-3 line 14 col 2 is "
             "blank; unblocks net_revenue_per_bed / opex_per_bed for those CCNs.",
    ),
    GapFillSource(
        field="net_revenue_per_bed", label="NPR per bed",
        fill_kind="external",
        source="Derived once beds backfilled (see beds row)",
        dataset_id="xubh-q36u", access="api", status="registered",
        note="No separate source — resolves automatically when beds are filled.",
    ),
    GapFillSource(
        field="opex_per_bed", label="Opex per bed",
        fill_kind="external",
        source="Derived once beds backfilled (see beds row)",
        dataset_id="xubh-q36u", access="api", status="registered",
        note="No separate source — resolves automatically when beds are filled.",
    ),
    GapFillSource(
        field="net_to_gross_ratio", label="Net-to-gross ratio",
        fill_kind="artifact",
        source="Filing inconsistent: gross < net patient revenue",
        access="n/a", status="n/a (artifact)",
        note="Gross revenue is understated/absent in the filing — no external "
             "source can correct one hospital's misreported gross. Flag, don't fill.",
    ),
    GapFillSource(
        field="contractual_allowance_rate", label="Contractual allowance rate",
        fill_kind="artifact",
        source="Filing inconsistent: allowances vs gross out of [0,1]",
        access="n/a", status="n/a (artifact)",
        note="Same root as net-to-gross — a bad gross/allowance filing. Flag, don't fill.",
    ),
    GapFillSource(
        field="operating_margin_on_npr", label="Operating margin",
        fill_kind="artifact",
        source="Filing artifact: opex incomplete/aggregated (margin out of band)",
        access="n/a", status="n/a (artifact)",
        note="A parent/CCN rollup or partial expense lines — the filing's own "
             "opex is wrong; no other source gives THIS entity's real margin. Flag.",
    ),
    GapFillSource(
        field="occupancy_rate", label="Occupancy rate",
        fill_kind="artifact",
        source="Filing artifact: patient-days exceed bed-days available",
        access="n/a", status="n/a (artifact)",
        note="Bed-days available understated in the filing — gated >105%. Flag.",
    ),
]

_BY_FIELD: Dict[str, GapFillSource] = {g.field: g for g in GAP_FILL_SOURCES}


def fill_source_for(field: str) -> Optional[GapFillSource]:
    """The researched fill path for a metric field, or None if not catalogued."""
    return _BY_FIELD.get(field)


def _is_gap(v) -> bool:
    return v is None or (isinstance(v, float) and v != v)  # None / NaN


def gap_census(metrics: Iterable) -> Dict[str, int]:
    """Count gaps per registered field across a sequence of HospitalMetrics
    (or any objects exposing those attributes). Data-driven, so the report
    reflects the live dataset, not hardcoded numbers."""
    counts = {g.field: 0 for g in GAP_FILL_SOURCES}
    total = 0
    for m in metrics:
        total += 1
        for field in counts:
            if _is_gap(getattr(m, field, None)):
                counts[field] += 1
    counts["_total"] = total
    return counts


def gap_report(metrics: Iterable) -> List[Dict[str, object]]:
    """Combine the live census with each field's fill source, sorted by gap
    count — the work queue for closing data gaps."""
    counts = gap_census(metrics)
    total = counts.get("_total", 0) or 1
    rows = []
    for g in GAP_FILL_SOURCES:
        n = counts.get(g.field, 0)
        rows.append({
            "field": g.field, "label": g.label, "gaps": n,
            "gap_pct": round(100.0 * n / total, 1),
            "fill_kind": g.fill_kind, "status": g.status,
            "source": g.source, "dataset_id": g.dataset_id,
            "url": g.url, "note": g.note,
        })
    rows.sort(key=lambda r: -r["gaps"])
    return rows
