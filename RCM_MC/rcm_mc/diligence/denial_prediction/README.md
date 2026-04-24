# denial_prediction/

**Claim-level denial prediction** — CCD-native predictive analytic that feeds the EBITDA bridge's denial-reduction lever with a data-driven target instead of an industry-aggregate guess.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — CCD-native denial prediction. |
| `model.py` | **Naive Bayes denial model — stdlib only.** `P(denial=1 | features) ∝ P(denial=1) × ∏_f P(f | denial=1)`. No sklearn dependency. |
| `analyzer.py` | End-to-end analyzer: CCD → features → model → report. One-liner public surface. |

## Why Naive Bayes + stdlib

- **Auditability > accuracy ceiling.** Naive Bayes is inspectable — partner sees the per-feature likelihood ratios and can defend them. A black-box gradient-boosted model would have higher AUC but worse defensibility.
- **No sklearn** — consistent with the package-wide "boring stack" principle. The math is explicit, the code is one file.
- **CCD-native** — features are the fields already normalized in Phase 1 ingest. No separate feature-engineering pass required.

## Features

From CCD fields:
- Payer, procedure code category (CPT block), place of service
- Provider specialty, provider-NPI denial history
- Claim age at submission, days from discharge to bill
- Patient-pay share, eligibility-verification presence
- Prior-auth status, medical-necessity doc flags

Per-feature likelihood ratios are pre-computed from the CCD training set at model-fit time, stored, and looked up at inference.

## Output

`DenialPredictionReport`:
- Per-claim predicted denial probability
- Aggregate portfolio denial rate projection
- Top-5 feature contributions to denials (for targeted remediation)
- Expected impact of moving the worst feature to cohort P50 (feeds bridge lever)

## One-liner API

```python
from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.denial_prediction import analyze_ccd

ccd = ingest_dataset("data/seller_pack/")
report = analyze_ccd(ccd)
print(report.projected_denial_rate)
```

## Where it plugs in

- **Thesis Pipeline step 5** — runs after Phase 2 benchmarks
- **EBITDA bridge v2** — `denial_workflow` lever uses this projection instead of industry-aggregate
- **Bridge Auto-Auditor** — if banker claims denial improvement, audit compares claim vs this model's projection

## Tests

`tests/test_denial_prediction.py` — NB math + feature-contribution stability + fixture-data prediction accuracy.
