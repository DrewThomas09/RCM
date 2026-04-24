# Thesis Pipeline

**In one sentence**: one-click orchestrator that runs the full 14-step diligence chain on a deal in ~170 milliseconds.

---

## What problem does this solve?

Before this pipeline existed, a PE analyst doing diligence had to:
1. Click Benchmarks → fill form → submit
2. Click Denial Prediction → fill form → submit
3. Click Bankruptcy Scan → fill form → submit
4. Click Deal MC → fill form → submit
5. Click Covenant Stress → fill form → submit
6. ... 10 more times

Each module rendered in isolation. The analyst was the glue.

**Now**: one form, one click, one report. Every module runs, headline numbers flow into downstream modules, bear-case evidence is collected, and the analyst sees the whole picture in one scrollable page.

---

## The 14 steps (in order)

1. **CCD ingest** — load the claims + revenue-cycle dataset
2. **KPI bundle** — compute HFMA benchmarks (days in AR, denial rate, etc.)
3. **Cohort liquidation** — denial + AR aging analysis
4. **QoR waterfall** — quality of revenue attribution
5. **Denial prediction** — ML model on claims
6. **Bankruptcy scan** — risk signature match
7. **Steward score** — real-estate lease stress
8. **Cyber score** — IT / BA risk
9. **Counterfactual advisor** — "what would change your mind" lever ranking
10. **Physician attrition** — per-NPI flight risk
11. **Provider economics** — per-physician P&L
12. **Market intel** — public comps + transaction multiples + sector sentiment
13. **Payer stress** — auto-derived mix + rate-shock MC *(new this cycle)*
14. **HCRIS X-Ray** — filed Medicare cost-report benchmark *(new this cycle, when CCN supplied)*
15. **Regulatory calendar** — CMS/OIG events × thesis drivers *(new this cycle)*
16. **Deal scenario assembly** — synthesize inputs for Deal MC
17. **Deal Monte Carlo** — 1,500 trials, 5-year MOIC / IRR distribution
18. **Covenant stress** — breach probability per quarter *(new this cycle)*
19. **Exit timing** — IRR curve × buyer-fit across years 2-7

Each step is wrapped in `_timed(step_name, fn, step_log)` → logs elapsed_ms + status. One failure doesn't abort the chain; the report contains whatever succeeded.

---

## Public API

```python
from rcm_mc.diligence.thesis_pipeline import (
    run_thesis_pipeline,
    PipelineInput,
    ThesisPipelineReport,
    pipeline_observations,
)

inp = PipelineInput(
    dataset="hospital_04_mixed_payer",        # CCD fixture
    deal_name="Meadowbrook Regional Hospital",
    specialty="HOSPITAL",
    revenue_year0_usd=450_000_000,
    ebitda_year0_usd=67_500_000,
    enterprise_value_usd=600_000_000,
    equity_check_usd=250_000_000,
    debt_usd=350_000_000,
    entry_multiple=9.0,
    medicare_share=0.45,
    landlord="MPT",
    hopd_revenue_annual_usd=45_000_000,
    hcris_ccn="010001",                       # triggers HCRIS X-Ray step
    n_runs=1_500,
)
report = run_thesis_pipeline(inp)

# Headline numbers
print(f"P50 MOIC: {report.p50_moic:.2f}x")
print(f"Regulatory verdict: {report.regulatory_verdict}")
print(f"Covenant max breach: {report.covenant_max_breach_probability*100:.0f}%")
print(f"Closest autopsy match: {report.top_autopsy_match}")

# Step-level diagnostics
for step in report.step_log:
    print(f"{step['step']}: {step['elapsed_ms']}ms · {step['status']}")

# Feed checklist
obs = pipeline_observations(report)
# obs["regulatory_calendar_run"] = True, etc.
```

---

## The ThesisPipelineReport surface

```python
@dataclass
class ThesisPipelineReport:
    # Step outputs (any can be None if the step short-circuited)
    ccd: Optional[Any] = None
    kpi_bundle: Optional[Any] = None
    cohort_report: Optional[Any] = None
    waterfall: Optional[Any] = None
    denial_report: Optional[Any] = None
    bankruptcy_scan: Optional[Any] = None
    steward_score: Optional[Any] = None
    cyber_score: Optional[Any] = None
    counterfactual_set: Optional[Any] = None
    attrition_report: Optional[Any] = None
    eu_report: Optional[Any] = None
    exit_timing_report: Optional[Any] = None
    autopsy_matches: Optional[List[Any]] = None
    market_intel: Optional[Dict[str, Any]] = None
    regulatory_exposure: Optional[Any] = None
    covenant_stress: Optional[Any] = None
    payer_stress: Optional[Any] = None
    hcris_xray: Optional[Any] = None
    deal_scenario: Optional[Any] = None
    deal_mc_result: Optional[Any] = None

    # Step-level diagnostics
    step_log: List[Dict[str, Any]]

    # Derived headline numbers (flow to Deal Profile + IC Packet)
    p50_moic: Optional[float]
    prob_sub_1x: Optional[float]
    regulatory_verdict: Optional[str]
    covenant_max_breach_probability: Optional[float]
    covenant_median_cure_usd: Optional[float]
    top_autopsy_match: Optional[str]
    exit_recommendation_year: Optional[int]
    exit_expected_irr: Optional[float]
    # ... many more
```

---

## Where it plugs in

- **Deal Profile**: the "Thesis Pipeline" tile launches this with pipeline-input params
- **Bear Case**: `generate_bear_case_from_pipeline(report)` auto-pulls every source off this report
- **UI page**: `/diligence/thesis-pipeline` renders the step log + headline grid + deep-link tiles to every sub-module

---

## Files in this module

```
thesis_pipeline/
├── __init__.py        # Public API re-exports
└── orchestrator.py    # 19-step chain + defensive wrappers + headline extraction (929 LOC)
```

### `__init__.py` (thin)
Re-exports: `run_thesis_pipeline`, `PipelineInput`, `ThesisPipelineReport`, `pipeline_observations`.

### `orchestrator.py` (929 LOC)
The **single-file brain** for the whole pipeline. Three responsibilities:

1. **`PipelineInput` dataclass** — every field the 19 steps need. Optional fields (like `hcris_ccn`, `landlord`, `hopd_revenue_annual_usd`) trigger optional steps. Required fields (dataset, deal_name, revenue/EBITDA) are the minimum for the chain to run.

2. **The step chain** — each of the 19 steps is a small function `def step_<name>(input, prior_outputs) → output`. Every call is wrapped in `_timed(step_name, fn, step_log)` which catches exceptions, logs elapsed ms + status (OK / ERROR / SKIP), and allows the chain to continue even when a single step fails. One broken module never breaks the whole report.

3. **Headline extraction** — after all steps run, a final synthesizer pulls out the ~20 headline numbers the Deal Profile + IC Packet need (p50_moic, prob_sub_1x, regulatory_verdict, covenant_max_breach_probability, top_autopsy_match, exit_recommendation_year, exit_expected_irr, etc.) and packs them into `ThesisPipelineReport` as first-class fields.

Also contains `pipeline_observations(report)` — converts the report into a flat dict of booleans (`{"regulatory_calendar_run": True, ...}`) for the IC Packet checklist.

**To add a 20th step**: (1) write `def step_<name>(inp, prior) → output`, (2) add a call inside `run_thesis_pipeline` wrapped in `_timed`, (3) add the output field to `ThesisPipelineReport`. No other file changes.

---

## Adjacent files

- **[`rcm_mc/ui/thesis_pipeline_page.py`](../../ui/thesis_pipeline_page.py)** — web page at `/diligence/thesis-pipeline`
- **[`tests/test_thesis_pipeline.py`](../../../tests/test_thesis_pipeline.py)** — 18 tests covering chain order, defensive wrappers, headline extraction, optional-step gating

---

## Tests

```bash
python -m pytest tests/test_thesis_pipeline.py -q
# Expected: 18 passed
```
