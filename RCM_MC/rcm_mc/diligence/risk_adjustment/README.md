# CMS-HCC Risk Adjustment + Risk-Adjusted Benchmarking

**In one sentence**: scores a target's case-mix burden (RAF) and puts peer cost/outcome comparisons on a case-mix-normalized footing, so a sicker patient panel isn't mistaken for an inefficient operator.

---

## What problem does this solve?

This is the healthcare-specific analytic the workbench was missing. Two hospitals can have identical cost-per-case, but if one treats a far sicker population, judging them on the raw number is wrong. Payers, ACOs, and CMS all normalize for case mix using the **CMS-HCC Risk Adjustment Factor (RAF)** before comparing performance. Until now the workbench compared targets to peers on raw HCRIS metrics — vulnerable to exactly this case-mix illusion.

Partners ask:
- *"Is this target actually expensive, or just treating sicker patients?"*
- *"How sick is the panel relative to the program average?"*
- *"After adjusting for case mix, is the operator efficient or an outlier?"*

A RAF of 1.00 is the program-average beneficiary. A panel RAF of 1.30 means the population is 30% sicker than average — you'd *expect* its costs to run ~30% above the program mean before judging the operator at all.

---

## How it works

The RAF decomposition is the standard CMS one:

```
RAF = demographic_factor
    + Σ disease_HCC_coefficients   (after hierarchy "trumping")
    + Σ disease_interaction_factors
```

1. **Demographic factor** — age/sex band (plus an under-65 disabled band). Older → higher weight.
2. **Disease HCCs** — each diagnosed condition is crosswalked (ICD-10 prefix *or* free text) to a Hierarchical Condition Category, the **disease hierarchy** is applied (metastatic cancer trumps lung cancer trumps localized; CKD-5 trumps CKD-4), and surviving coefficients are summed. Hierarchy stops double-counting severities of the same disease family.
3. **Interactions** — a small documented set of disease pairs that add on top (Diabetes × CHF, CHF × COPD, CHF × renal failure, …).
4. **Risk-adjusted benchmarking** — the load-bearing step. Given the target's metric, the target's RAF, and a peer cohort's metrics + RAFs:

   ```
   peer_rate_per_raf = mean(peer_value) / mean(peer_raf)
   expected_value    = peer_rate_per_raf × target_raf
   O/E               = target_value / expected_value
   ```

   O/E ≈ 1.0 → performs as case mix predicts. O/E > 1.0 on a cost metric → genuinely expensive after adjustment (an operator signal). The verdict flips polarity for "higher-is-better" metrics (quality stars, gap-closure).

---

## The demo moment

Target costs **30% above peers** raw — looks like a problem. But the panel RAF is **1.30** vs peer mean **1.00**:

> `cost_pmpm`: O/E **1.00** (+0.0% vs case-mix expectation). Raw gap to peers **+30.0%**; case mix explains **+30.0%** of it — verdict **IN_LINE**.

The "expensive operator" finding evaporates: it was a sicker panel. Conversely a target at peer-level raw cost but a RAF of 0.85 surfaces as **ELEVATED / OUTLIER** — it's expensive *for how healthy its patients are*, which raw benchmarking would have missed entirely.

---

## Public API

```python
from rcm_mc.diligence.risk_adjustment import (
    Demographics, compute_raf, score_panel, risk_adjust_metric,
)

# Single beneficiary
score = compute_raf(
    Demographics(age=78, sex="M"),
    ["E11.42", "I50.9", "J44.9"],   # ICD-10 or free text both work
)
print(score.raf, score.hccs, score.interactions)

# Panel rollup
panel = [(Demographics(72, "M"), ["CHF"]),
         (Demographics(80, "F"), ["E11.42", "I50.9"])]
ps = score_panel(panel)
print(ps.mean_raf, ps.hcc_prevalence)

# Risk-adjusted peer benchmark
b = risk_adjust_metric(
    "cost_pmpm",
    target_value=130.0, target_raf=ps.mean_raf,
    peer_values=[100, 110, 90, 105], peer_rafs=[1.0, 1.0, 1.0, 1.0],
    lower_is_better=True,
)
print(b.verdict.value, b.oe_ratio, b.headline)
```

---

## Where it plugs in

- **HCRIS Peer X-Ray / RCM Benchmarks** — wrap any peer comparison in `risk_adjust_metric` so the verdict reflects case mix, not just the raw gap.
- **Bear Case** — a true post-adjustment OUTLIER becomes `[RA1]` evidence; a raw gap fully explained by case mix *removes* a false finding.
- **MA rate / V28 work** — pairs with `diligence.policy_shock`: V28 compresses coded RAF, the rate notice prices it.
- **Provenance graph** — every output carries `source_module="diligence.risk_adjustment"` and `citation_key="RA1"`.

---

## Files in this module

```
risk_adjustment/
├── __init__.py        # Public API re-exports
├── hcc_library.py     # demographic grid + curated HCC factors + ICD-10/keyword crosswalk + hierarchy
└── risk_scorer.py     # compute_raf / score_panel / risk_adjust_metric + verdicts + headlines
```

---

## Calibration + scope (read before trusting a number)

The coefficients are **representative** of the **CMS-HCC V28 (PY2024+) community, non-dual, aged** segment — the most common payment segment, used as the diligence default. They are a **curated subset** (~24 of ~115 payment HCCs) covering the highest-prevalence / highest-weight conditions, **not** the full model. Magnitudes are in the published ballpark but are **not payment-grade**.

For payment-grade precision (a target's actual claims extract in confirmatory diligence), swap `compute_raf` for the certified grouper or the **Tuva `cms_hcc` mart** behind the optional adapter — both return a `RiskScore`, so no caller changes. See [`docs/TUVA_MYELIN_INTEGRATION.md`](../../../docs/TUVA_MYELIN_INTEGRATION.md).

**Refresh annually** when CMS publishes the new factor table with each Rate Announcement.

---

## Tests

```bash
python -m pytest tests/test_risk_adjustment.py -q
# Expected: 26 passed
```
