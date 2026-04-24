# HCRIS Peer X-Ray

**In one sentence**: look up any US hospital's filed Medicare cost report and benchmark it against its true peer group in 25 milliseconds.

---

## What problem does this solve?

Before you buy a hospital, you need to know if it's better or worse than similar hospitals. A 300-bed community hospital in Alabama should be compared to other 300-bed community hospitals in the Southeast — not to the 1,500-bed Cleveland Clinic.

Traditional diligence takes weeks of consulting-firm work to build these peer comparisons. A **CapIQ subscription costs $80,000/year** and doesn't even give you this level of detail.

The US government has the data. Every Medicare-accepting hospital files a "Medicare cost report" (HCRIS) every year — a 2,500-field document with bed count, payer mix, revenue, expenses, everything. It's public data. Nobody productizes it for PE diligence.

**This module does.**

---

## How it works (simple version)

1. We shipped 17,701 hospital cost reports (FY 2020–2022) as a gzipped CSV inside the repo
2. You type a hospital's name or Medicare CCN (like `010001` for Southeast Health in Alabama)
3. The tool finds 25–50 actually comparable hospitals using:
   - Same size cohort (MICRO / SMALL_COMMUNITY / COMMUNITY / REGIONAL / ACADEMIC)
   - Within ±30% bed count
   - Same state first, then same region, then national as fallback
4. For each of 15 metrics, it shows:
   - The target's value
   - The peer P25 / median / P75
   - Signed % variance vs median
   - A 3-year trend sparkline (improving / deteriorating / flat)
   - A box-plot showing where the target sits in peer density
5. It also surfaces HCA / THC / UHS / CYH public-comp op margins for the broader market context

---

## The 15 metrics

| Group | Metrics |
|-------|---------|
| **Size** | Beds, Patient days, Occupancy rate |
| **Payer Mix** | Medicare / Medicaid / Other day share, Payer diversity (1−HHI) |
| **Revenue Cycle** | NPR per bed, NPR per patient day, Contractual allowance rate, Net-to-gross ratio |
| **Cost Structure** | Opex per bed, Opex per patient day |
| **Margin** | Operating margin, Net income margin |

Every metric is semantically colored: **green = better than peer P75** (if the metric is "higher is better" like margin) or **green = below peer P25** (if the metric is "lower is better" like opex/bed). Analyst sees winners vs losers at a glance.

---

## Where it plugs in

- **Thesis Pipeline**: auto-runs when the pipeline input has `hcris_ccn` set
- **Bear Case**: HCRIS becomes a citation source — `[H1]` evidence in the auto-generated memo
- **Deal Profile**: has a tile with the SCREENING badge
- **Cross-links**: one-click handoff to Deal MC / Payer Stress / Covenant Stress / Bear Case with NPR + EBITDA + cap structure pre-seeded using 9.0× peer-median entry × 42/58 equity/debt

---

## Files in this module

```
hcris_xray/
├── __init__.py       # Public API surface — re-exports everything from metrics.py + xray.py
├── metrics.py        # HospitalMetrics dataclass + 15 metric specs + cohort classifier
└── xray.py           # Peer-matching engine + benchmark computation + XRayReport
```

### `__init__.py` (thin)
Pure re-export shim. Import everything from here: `from rcm_mc.diligence.hcris_xray import xray, find_hospital, search_hospitals, HospitalMetrics, XRayReport`.

### `metrics.py` (350 LOC)
Pure-math module with **no I/O**. Two jobs:

1. **`HospitalMetrics` dataclass** — one filed HCRIS report as typed fields (beds, patient_days, medicare_days, opex, npr, operating_margin, etc.). Built from the CSV row in `rcm_mc/data/hcris.py`.
2. **`METRIC_SPECS` tuple** — the 15 canonical metrics with `label`, `direction` (HIGHER_BETTER / LOWER_BETTER / NEUTRAL), `units`, `group`, and `extract(m: HospitalMetrics) → float`. Adding a 16th metric means adding one `MetricSpec(...)` entry here — no other file changes.
3. **Cohort classifier** (`classify_cohort`) — bins beds into `MICRO / SMALL_COMMUNITY / COMMUNITY / REGIONAL / ACADEMIC`. This is what peer-matching uses to stop comparing a 50-bed rural hospital to Cleveland Clinic.

### `xray.py` (538 LOC)
**The brain.** Three responsibilities:

1. **Hospital lookup** — `find_hospital(ccn_or_name)` + `search_hospitals(query, state=None, limit=20)`. Fuzzy name match over 17,701 rows.
2. **Peer-group assembly** — for a given target, walks a waterfall: same cohort + same state + ±30% beds → same region → national. Stops when 25+ peers found (configurable via `peer_k`).
3. **Benchmark computation** — for each of the 15 metrics, computes target value, peer P25/median/P75, signed variance vs median, 3-year trend slope. Returns `XRayReport` with `headline`, `trend_signal`, and `metrics: List[MetricBenchmark]`.

Performance: cold load parses the gzipped CSV (~250ms), then results cache in memory — subsequent x-rays run ~7ms.

---

## Adjacent files (outside this module)

- **[`rcm_mc/data/hcris.csv.gz`](../../data/hcris.csv.gz)** — 17,701-row gzipped dataset (FY 2020–2022)
- **[`rcm_mc/data/hcris.py`](../../data/hcris.py)** — CSV loader + schema validator
- **[`rcm_mc/ui/hcris_xray_page.py`](../../ui/hcris_xray_page.py)** — web page at `/diligence/hcris-xray`
- **[`tests/test_hcris_xray.py`](../../../tests/test_hcris_xray.py)** — 21 tests covering lookup, peer-matching, benchmark math, cohort edge cases

---

## Public API

```python
from rcm_mc.diligence.hcris_xray import (
    xray, find_hospital, search_hospitals, dataset_summary,
    get_target_history,
    HospitalMetrics, MetricBenchmark, XRayReport,
)

# One-shot X-Ray
report = xray(ccn="010001", peer_k=25)
print(report.headline)
print(f"Trend: {report.trend_signal}")
for bm in report.metrics:
    print(f"{bm.spec.label}: {bm.target_value} vs {bm.peer_median}")

# Search
hits = search_hospitals("REGIONAL", state="AL", limit=20)

# Multi-year trend for one hospital
history = get_target_history("010001")
# Returns list ordered oldest-first
```

---

## Performance

- **Cold load** (first call): ~250ms (parses 17,701 rows)
- **Subsequent X-Rays**: ~7ms each (dataset cached in memory)

---

## Data refresh

The HCRIS dataset ships as a snapshot. To refresh:

```bash
rcm-mc data refresh hcris
```

Pulls the latest from CMS + rebuilds `hcris.csv.gz`. Documented in the `rcm_mc/data/README.md`.
