# Survival Analysis (Retention & Readmission)

**In one sentence**: turns a static readmission/churn rate into a time-to-event view — survival curves, group comparisons, and a hazard model that says which factors drive risk.

---

## What problem does this solve?

A "15% 30-day readmission rate" is a single number that hides the thing that matters: *when* and *for whom*. Do readmissions cluster in the first week (a fixable discharge-process problem) or spread evenly (a sicker panel)? Is churn front-loaded (onboarding failure) or late (satisfaction decay)? For any value-based-care or patient-LTV thesis, the unit of analysis is **time-to-event**, not a rate.

Partners ask:
- *"What's the readmission curve look like — and where does it bend?"*
- *"Is the treated cohort's retention actually different from control?"*
- *"Which factors raise readmission risk, holding the others fixed?"*

---

## How it works

1. **Kaplan-Meier** (`kaplan_meier`) — the non-parametric survival curve S(t), with **Greenwood** standard errors, **log-log** confidence bands (stay inside [0,1]), and median survival. Right-censoring handled (a patient event-free at last contact still counts in the risk set until then).
2. **Log-rank test** (`logrank_test`) — compares two curves (treated vs control, high- vs low-acuity). Chi-square, 1 df; p-value via `math.erfc` — no scipy.
3. **Cox proportional hazards** (`cox_ph`) — Breslow partial likelihood, Newton-Raphson. Returns per-covariate **hazard ratios** with CIs, **Harrell's concordance** (C-index), and a **proportional-hazards diagnostic** so a violated assumption shows up instead of producing a confident wrong HR.

All numpy + stdlib.

## The demo moment

```python
from rcm_mc.diligence.survival import kaplan_meier, logrank_test, cox_ph

km = kaplan_meier(durations, events)        # events: 1=readmit, 0=censored
print(km.median_survival, km.survival_at(30))

lr = logrank_test(durations, events, groups)   # 0/1 cohort
print(lr.p_value)

cox = cox_ph(durations, events, X, names=["acuity", "age", "ma_flag"])
print(cox.headline)        # "acuity raises hazard (HR 2.71, 95% CI [...], p=...)"
for c in cox.covariates:
    print(c.name, c.hazard_ratio, c.p_value)
```

> `acuity raises hazard (HR 2.71, 95% CI [2.10, 3.49], p=0.000); concordance 0.74.`

---

## Where it plugs in

- **VBC / LTV theses** — retention curves and churn hazards feed patient-LTV and value-based-care underwriting.
- **Quality diligence** — time-to-readmission complements the HRRP/VBP projector in `diligence/quality/`.
- **Provenance graph** — outputs carry `source_module="diligence.survival"` and `citation_key="SV1"`.

## Files

```
survival/
├── __init__.py
└── estimators.py    # kaplan_meier / logrank_test / cox_ph + Greenwood/Breslow/concordance
```

## Honesty about the method

- **Breslow tie handling** (simplest); `tie_fraction` is reported so you can see if Efron would matter.
- **Model-based SEs** (observed information), not robust to mis-specified PH — the PH diagnostic in the headline is the guard.

## Tests

```bash
python -m pytest tests/test_survival.py -q
# Expected: 17 passed
```
