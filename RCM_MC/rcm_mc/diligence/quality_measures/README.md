# Quality Measures (HEDIS/CQM Gap Analysis)

**In one sentence**: scores a target's quality measures against national benchmarks and peers, sizes the patient care-gap to the next threshold, and rolls a weighted composite into a star-equivalent.

---

## What problem does this solve?

Quality performance is both a value driver and a downside risk: MA Stars bonuses, ACO shared-savings gates, and VBC withholds all hinge on measure rates. But "82% on HbA1c control" isn't actionable. **"47 diabetic patients are one A1c draw from clearing the 4-star cut"** is — the gap-count is the operating lever.

Partners ask:
- *"How does this asset's quality stack up to benchmark and peers?"*
- *"Where's the addressable gap — how many patients to close?"*
- *"What's the composite / star-equivalent, and what drags it?"*

> Distinct from `diligence/quality/` (the VBP/HRRP penalty projector); this is the measure-rate / gap-closure cut.

---

## How it works

1. **Curated measure library** — ~10 HEDIS/CQM measures with a documented national benchmark and direction (higher-is-better for process/screening; lower-is-better for readmissions/ED).
2. **Per-measure evaluation** — rate, signed gap to benchmark, **patient gap-count** to reach it, peer percentile (inverted for lower-is-better so high percentile always = good), and a normalized 0-1 performance score.
3. **Composite scorecard** — weighted 0-100 + 1-5 star-equivalent, total addressable patient-gaps, and the three weakest measures as priorities.

## The demo moment

```python
from rcm_mc.diligence.quality_measures import evaluate_measure, get_measure, score_quality

results = [
    evaluate_measure(get_measure("HBA1C_CONTROL"), numerator=600, denominator=1000),
    evaluate_measure(get_measure("BP_CONTROL"), 700, 1000),
    evaluate_measure(get_measure("PLAN_ALL_READMIT"), 200, 1000),
]
sc = score_quality(results)
print(sc.headline)
```

> Quality composite 58.0/100 (~3.3 stars) across 3 measures; 2 below benchmark, 220 patient-gaps to close. Priorities: PLAN_ALL_READMIT, HBA1C_CONTROL, BP_CONTROL.

---

## Where it plugs in

- **VBC / MA-risk theses** — Stars and gate performance drive bonus/withhold economics.
- **`risk_adjustment`** — quality benchmarking can be risk-adjusted via `risk_adjust_metric(lower_is_better=False)` where case mix matters.
- **Provenance graph** — outputs carry `source_module="diligence.quality_measures"` and `citation_key="QM1"`.

## Files

```
quality_measures/
├── __init__.py
└── measures.py    # QualityMeasure library + evaluate_measure + score_quality
```

## Calibration

Benchmarks are representative national rates for the 2026 cycle — **refresh from the HEDIS / CMS Stars technical specs annually**; they're directional defaults, not contract values.

## Tests

```bash
python -m pytest tests/test_quality_measures.py -q
# Expected: 14 passed
```
