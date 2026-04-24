# physician_attrition/

**P-PAM (Predictive Physician Attrition Model).** Given a roster of providers + optional public-data context (NPI enumeration date, local-competitor count, specialty FMV benchmark), score each provider's 18-month flight-risk probability.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `features.py` | **9-dimension feature extraction.** From `Provider` dataclass (shared with `physician_comp/`) + optional NPI-enumeration-date (public CMS registry) + optional local-competitor count + FMV delta. |
| `model.py` | **Logistic-style flight-risk predictor — stdlib only.** Hand-calibrated coefficients. 9-dim `AttritionFeatures` → sigmoid → 18-month flight-risk probability. No sklearn. |
| `analyzer.py` | **Orchestrator → `AttritionReport`** with per-provider flight-risk + concentration-weighted NPR-at-risk + retention recommendations. |

## The 9 feature dimensions

1. Years in role / tenure
2. Age (proxy for retirement risk)
3. Productivity trend (wRVU trajectory)
4. Comp delta vs specialty FMV benchmark
5. Specialty-level churn rate (peer-referenced)
6. Local competitor count (NPI registry density)
7. Prior-role turnover history (if available)
8. Subspecialty-board recency
9. Quality metric trajectory (proxy for engagement)

## Why hand-calibrated coefficients

- **Reproducibility**: partners can inspect + defend per-feature contributions
- **Small-sample robustness**: no overfitting on a 50-provider roster
- **Zero runtime deps beyond numpy**

## Output

`AttritionReport`:
- Per-provider 18-month flight-risk percentile + point estimate
- NPR-at-risk rollup (top-N departures × their revenue contribution)
- Retention-structure recommendations (earn-out tranches, comp parity adjustments)

## Where it plugs in

- **Thesis Pipeline step 10** — runs when roster supplied
- **Deal MC** — `physician_attrition` driver distribution fed from this model
- **Bear Case** — material NPR-at-risk becomes OPERATIONAL theme evidence
- **LOI / earn-out** — `physician_comp/earnout_advisor_enhancement` uses attrition-risk concentration to structure earn-outs

## Tests

`tests/test_physician_attrition*.py` — feature extraction + sigmoid calibration + roster rollup math.
