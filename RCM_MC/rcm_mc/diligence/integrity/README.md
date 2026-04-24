# integrity/

**Data-integrity gauntlet** — every guardrail that must hold before a CCD-derived metric can flow into the packet or PE brain. Each module is load-bearing and runs as a **hard precondition**, not a warning.

## The single entry

**`preflight.run_ccd_guardrails`** is the one function the packet builder calls before trusting any CCD-derived `ObservedMetric`. Runs every guardrail in this subpackage, returns pass/fail + reasons.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "load-bearing, hard precondition" contract. |
| `preflight.py` | **`run_ccd_guardrails`** — orchestrator. Packet builder calls this before trusting CCD metrics. |
| `cohort_censoring.py` | Structured guardrail wrapping the math in `benchmarks/cohort_liquidation.py`. Makes the as-of censoring rule explicit so preflight can check it. |
| `distribution_shift.py` | **Distribution-shift check.** PE Intelligence archetype recognition was calibrated on acute-hospital-dominant HCRIS. When an analyst drops a dental CCD, this refuses to silently apply acute-hospital priors. |
| `leakage_audit.py` | **Target leakage audit.** Guards the trap: Hospital X's CCD → KPIs → join training corpus → ridge predictor trains on corpus → when Hospital X runs, model sees its own data. |
| `split_enforcer.py` | **Provider-disjoint train / calibration / test splits.** Fixes `ml/conformal.py`'s row-shuffle split — same provider's rows can't be in both calibration + test set, which would void conformal coverage guarantee. |
| `temporal_validity.py` | **Temporal validity stamp.** 2023 historical claims don't predict 2026 payer behavior once OBBBA Medicaid work requirements, site-neutral payment, MA risk-adj revisions phase in. Every KPI carries a validity window. |

## Why this is a gauntlet, not a suggestion

Distribution shift (dental CCD ≠ acute hospital prior), target leakage (Hospital X's own data in its training corpus), provider-disjoint splits (conformal coverage), temporal validity (2023 ≠ 2026 under OBBBA) — each is a specific, well-documented way a derived number can be technically correct but **epistemically wrong**. The integrity layer refuses to emit the number when conditions aren't met.

Preferred over soft warnings because a skeptical auditor wants the **reason** a number isn't rendered, not a silently-degraded number.

## Tests

`tests/test_integrity*.py` — each guardrail has isolated unit tests + an integration test through `preflight.run_ccd_guardrails`.
