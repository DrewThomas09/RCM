# Risk-Adjusted PMPM Trend

**In one sentence**: separates real cost inflation from case-mix drift by trending PMPM/RAF alongside raw PMPM — so a rising cost curve isn't blamed on the operator when the panel just got sicker.

---

## What problem does this solve?

Raw per-member-per-month (PMPM) cost growth conflates two very different stories:

1. **Costs up because acuity is up** — the panel's RAF rose. Often defensible (you kept sicker patients out of the ED), and under MA-risk it's revenue you also capture.
2. **Costs up at constant case mix** — genuine cost inflation or care leakage the operator owns.

Dividing PMPM by the panel RAF strips story (1) out. The **risk-adjusted PMPM** trend is story (2) — the one that should move the underwrite.

Partners ask:
- *"Is this asset's medical-cost trend a problem, or is the panel aging into it?"*
- *"How does the risk-adjusted cost level compare to peers?"*
- *"If this trend continues, what's the EBITDA hit?"*

---

## How it works

1. **Two trends side by side** — nominal PMPM CAGR vs risk-adjusted (PMPM/RAF) CAGR, plus the case-mix drift (RAF CAGR). The gap between nominal and risk-adjusted *is* the case-mix story.
2. **Peer O/E** — the latest risk-adjusted level is benchmarked against a peer cohort by **reusing `risk_adjust_metric` from `diligence.risk_adjustment`** (the modules compose — no duplicated case-mix logic).
3. **EBITDA projection** — a continuing risk-adjusted trend rolled `projection_years` forward × member-months = extra annual cost.
4. **Verdict** on the risk-adjusted CAGR against medical-cost-trend bands (≤4% in-line, ≤8% elevated, >8% outlier; negative = efficient).

## The demo moment

```python
from rcm_mc.diligence.pmpm import PMPMPeriod, analyze_pmpm

periods = [PMPMPeriod("2023", 1000, raf=1.00),
           PMPMPeriod("2024", 1100, raf=1.10),
           PMPMPeriod("2025", 1210, raf=1.21)]
res = analyze_pmpm(periods, periods_per_year=1.0)
print(res.headline)
```

> PMPM trend: nominal +10.0%/yr, risk-adjusted +0.0%/yr (case-mix drift +10.0%/yr) — verdict IN_LINE. Case mix explains ~100% of headline growth.

The 10%/yr headline cost growth evaporates as an operator concern — it was entirely the panel getting sicker. Flip the RAFs to flat and the same PMPM series reads **OUTLIER** (+10%/yr real inflation).

---

## Where it plugs in

- **Financial diligence / QoE** — the cost-trend cut that underwrites VBC and MA-risk theses.
- **Deal MC** — `projected_ebitda_impact_usd` feeds the cost-trend driver.
- **risk_adjustment** — consumes its O/E engine; pairs with `hierarchical_bench` to stabilize small-panel PMPM.
- **Provenance graph** — outputs carry `source_module="diligence.pmpm"` and `citation_key="PM1"`.

## Files

```
pmpm/
├── __init__.py
└── pmpm_trend.py    # PMPMPeriod / analyze_pmpm + CAGR decomposition + peer O/E + projection
```

## Tests

```bash
python -m pytest tests/test_pmpm.py -q
# Expected: 10 passed
```
