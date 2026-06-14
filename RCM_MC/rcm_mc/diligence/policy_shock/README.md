# Policy-Shock Evaluator (Difference-in-Differences)

**In one sentence**: estimates what a regulatory shock — OBBBA Medicaid, a CY2027 MA rate cut, the PFS conversion-factor move — actually does to an asset, using a quasi-experimental design instead of a flat revenue haircut.

---

## What problem does this solve?

When the thesis hinges on "the MA rate cut takes 3% off revenue," the IC's first question is *where did 3% come from?* A flat haircut is an assumption, not evidence. The rigorous answer compares units **exposed** to the policy against units that **aren't**, **before** and **after** the change, and lets the data size the effect — with the diagnostics that make it defensible.

Partners / ICs ask:
- *"What does the OBBBA Medicaid change do to this asset's revenue, and how confident are we?"*
- *"Is the effect we're seeing the policy, or a pre-existing divergence?"*
- *"What's the EBITDA-at-risk dollar number, with a confidence interval?"*

This is the rigorous version of the CY2027 MA/PFS scenario modeling the workbench already tracks.

---

## How it works

1. **2×2 DiD** (`did_2x2`) — the textbook estimator: `(treated_post − treated_pre) − (control_post − control_pre)`. The control's change is the counterfactual.
2. **Two-way fixed-effects DiD** (`estimate_did`) — the workhorse. Unit fixed effects absorb level differences between markets; period fixed effects absorb shocks common to everyone; the `treated × post` interaction **is** the ATT. Standard errors are **cluster-robust** (clustered by unit, CR1 small-sample correction).
3. **Event study** (`event_study`) — treated × relative-period coefficients around the treatment date. Pre-treatment leads **are** the parallel-trends test; a Bonferroni joint check rolls into `pretrend_pvalue`.
4. **Placebo** (`placebo_test`) — re-run on a fake treatment date inside the pre-period. A non-null placebo means the design is catching something other than the policy.
5. **Synthetic control** (`synthetic_control`) — the secondary strategy for a single treated market: nonnegative donor weights (summing to 1) fit to the pre-period by projected gradient descent, then the post-period gap.
6. **Deal bridge** (`policy_ebitda_overlay`) — translate the ATT into EBITDA-at-risk dollars (with CI), flowing into the Deal MC `reg_headwind` driver and the Bear Case like every other finding.

The **verdict** combines all three checks — significance alone is only `SUGGESTIVE`; it escalates to `LIKELY` when parallel trends hold and `STRONG` when the placebo is clean too. Fewer than ~30 clusters caps the verdict and raises `small_cluster_warning`.

---

## The demo moment

Analyst assembles a panel of MA-exposed markets vs FFS-dominant controls, quarterly revenue, treatment at CY2027Q1:

> Policy **reduced** the outcome by **0.041** (95% CI [−0.058, −0.024], p=0.001); 20 treated vs 20 control units. Verdict: **STRONG**.

`policy_ebitda_overlay` on $50M of MA-exposed revenue:

> EBITDA at risk **−$2.05M** (95% CI [−$2.9M, −$1.2M]).

That's an estimated, bounded, defensible number — not a hand-waved haircut — and it flows straight into the Deal MC.

---

## Public API

```python
from rcm_mc.diligence.policy_shock import (
    PanelData, estimate_did, event_study, synthetic_control,
    policy_ebitda_overlay, get_policy,
)

panel = PanelData(
    unit=[...], period=[...], outcome=[...],
    treated_unit=[...], treatment_period=2027,
)
res = estimate_did(panel)
print(res.verdict.value, res.att, res.ci_low, res.ci_high)
print(res.headline)

overlay = policy_ebitda_overlay(res, exposed_revenue_usd=50_000_000)
print(overlay.ebitda_impact_usd)

shock = get_policy("MA_RATE_CY2027")   # treatment definition + expected sign
```

---

## Where it plugs in

- **Regulatory Calendar × Kill-Switch** — the curated `POLICY_SHOCKS` map to thesis drivers; the estimated ATT replaces the assumed EBITDA overlay.
- **Deal Monte Carlo** — `policy_ebitda_overlay` feeds the `reg_headwind_usd` driver with a distributional (CI-bounded) input.
- **Bear Case** — a `STRONG`/`LIKELY` adverse effect becomes `[PS1]` evidence; the policy record supplies the `[PS2]` citation.
- **Provenance graph** — outputs carry `source_module="diligence.policy_shock"` and `citation_key="PS1"`/`"PS2"`.

---

## Files in this module

```
policy_shock/
├── __init__.py         # Public API re-exports
├── did_estimator.py    # OLS+cluster-robust, did_2x2, estimate_did, event_study,
│                       #   placebo_test, synthetic_control, policy_ebitda_overlay
└── policy_library.py   # curated PolicyShock catalog (OBBBA, MA, PFS, site-neutral)
```

---

## Honesty about the method (surfaced, not buried)

- **Normal-approximation p-values.** Cluster-robust inference with few clusters (< ~30) is anti-conservative; `small_cluster_warning` fires and the verdict caps at `SUGGESTIVE`.
- **Common treatment timing.** One policy date for all treated units. Staggered adoption needs a Callaway–Sant'Anna style estimator — a documented follow-up, not silently mis-handled here.
- **Identification is only as good as the control group.** The event-study pretrend test and the placebo are there precisely so a bad control group shows up rather than producing a confident wrong number.

---

## Refreshing the policy library

`POLICY_SHOCKS` dates/provisions reflect public rulemaking/law as of the 2026 diligence cycle. **Confirm the effective date against the Federal Register / statute** before relying on a record, and refresh when CMS publishes a final rule.

---

## Tests

```bash
python -m pytest tests/test_policy_shock.py -q
# Expected: 20 passed
```
