# Payer Mix Stress Lab

**In one sentence**: stress-tests a hospital's commercial + government payer portfolio against historical rate-movement priors and concentration amplifier.

---

## What problem does this solve?

Every hospital's revenue comes from a mix of insurance payers — UnitedHealthcare, Anthem, Aetna, Medicare FFS, Medicare Advantage, Medicaid, etc. Each payer reprices their contracts every 1-3 years. A 5% rate cut from the target's #1 payer can erase 2-4% of NPR and material EBITDA.

Partners ask:
- *"What's my exposure if UnitedHealth cuts rates at renewal?"*
- *"Is this hospital's payer mix too concentrated?"*
- *"What's the P10 downside on EBITDA over the 5-year hold?"*

Traditional diligence names the payers. This tool **quantifies the dynamic rate-movement risk** — a gap no other product fills.

---

## How it works

1. **Curated payer library** — 19 major US healthcare payers with:
   - National commercial (UHC, Anthem, Aetna, Cigna, Humana)
   - Regional Blues plans (BCBS IL, MI, NC, Highmark, BCBS CA, Kaiser)
   - Medicare FFS + Medicare Advantage aggregate
   - Medicaid FFS + Centene + Molina (managed Medicaid)
   - TRICARE + Workers Comp + Self-pay
   - Each ships with empirical rate-movement priors (p25/median/p75), negotiating leverage score (0-1), renewal cadence (12-mo probability), churn probability (probability of contract termination)
2. **Monte Carlo rate shocks**: per-path per-year per-payer sample rate move from Normal fit to priors, dampened when contract isn't renewing that year, tail churn events.
3. **Concentration amplifier**: when Top-1 share >30%, multiply aggregate NPR volatility by `1 + (top_1 − 0.30) × 2`. When Top-2 share >50%, add +0.10. When Top-3 >70%, add another +0.10. Empirical PE credit-fund heuristic.
4. **Aggregate rollup**: per-year NPR impact cone (P10/P50/P90), cumulative NPR + EBITDA at risk, concentration-risk verdict, per-payer detail cards.

---

## The demo moment

Analyst pastes:
```
UnitedHealthcare, 22%
Anthem, 20%
Medicare FFS, 25%
Medicare Advantage, 15%
Medicaid managed, 10%
Self-pay, 8%
```

Target NPR $450M, EBITDA $67.5M, 5-year hold.

Result:
- **Verdict: WARNING** · Top-1 = 22%, HHI 1842, concentration amplifier 1.00×
- **P10 5-year EBITDA drag: −$5.9M**
- **Worst-exposed payer**: UnitedHealthcare — P10 cumulative rate move −6.2%

Per-payer card for UHC shows:
> **UnitedHealthcare (22%)** · Median 5-year rate move **+3.5%** · P10 tail −6.2% · P90 +11.8%
> *Library prior per renewal: μ +1.5%, P25 −4.5%, P75 +5.5% — renewal cadence 35%/12mo*
> Behavioral notes: "Most aggressive repricing counterparty in US healthcare. Uses Change Healthcare / Optum data to drive evidence-based rate cuts on hospital outliers."

---

## Public API

```python
from rcm_mc.diligence.payer_stress import (
    run_payer_stress,
    PayerMixEntry,
    default_hospital_mix,
    classify_payer,
    PAYER_PRIORS,
)

mix = [
    PayerMixEntry("UnitedHealthcare", 0.22, contract_renewal_date="2026-09-30"),
    PayerMixEntry("Anthem", 0.20, contract_renewal_date="2027-03-31"),
    PayerMixEntry("Medicare FFS", 0.25),
    # ...
]

result = run_payer_stress(
    target_name="Meadowbrook Regional",
    mix=mix,
    total_npr_usd=450_000_000,
    total_ebitda_usd=67_500_000,
    horizon_years=5,
    n_paths=500,
)
print(result.verdict.value)  # PASS / CAUTION / WARNING / FAIL
print(result.headline)
print(f"P10 5-yr EBITDA drag: ${result.p10_cumulative_ebitda_impact_usd/1e6:.1f}M")
for row in result.per_payer:
    print(f"{row.payer_name}: median rate move {row.median_rate_move*100:+.2f}%")
```

---

## Where it plugs in

- **Thesis Pipeline**: auto-derives a mix from `medicare_share` input, runs stress test automatically
- **Bear Case**: high concentration + material P10 drag become `[P1]` evidence
- **Deal Profile**: tile under DILIGENCE phase
- **Cross-links**: feeds Deal MC's exit-multiple sensitivity via EBITDA-at-risk

---

## Files in this module

```
payer_stress/
├── __init__.py             # Public API re-exports
├── payer_library.py        # 19 curated payers + keyword classifier (410 LOC)
└── contract_simulator.py   # run_payer_stress + MC engine + amplifier math (634 LOC)
```

### `__init__.py` (thin)
Re-exports: `run_payer_stress`, `PayerMixEntry`, `default_hospital_mix`, `classify_payer`, `PAYER_PRIORS`.

### `payer_library.py` (410 LOC)
The **curated payer catalog**. 19 `PayerPrior` records covering every material US healthcare payer:

- National commercial: UnitedHealthcare, Anthem, Aetna, Cigna, Humana
- Regional Blues: BCBS IL / MI / NC / CA, Highmark, Kaiser
- Government: Medicare FFS, Medicare Advantage aggregate
- Managed Medicaid: Medicaid FFS, Centene, Molina
- Other: TRICARE, Workers Comp, Self-pay

Each prior ships with empirical rate-movement priors (p25/median/p75 per renewal), negotiating leverage score (0-1), 12-month renewal probability, churn probability, and behavioral notes (e.g., *"UHC uses Change Healthcare / Optum data to drive evidence-based rate cuts on hospital outliers"*).

Also contains `classify_payer(name) → PayerPrior` — fuzzy keyword matcher so "United" or "UHC" or "UnitedHealthcare" all resolve to the same prior.

### `contract_simulator.py` (634 LOC)
The **Monte Carlo engine + concentration amplifier**. For each path × year × payer:

1. Sample a rate-move from Normal fit to the payer's prior
2. Dampen by (1 − renewal probability) when not renewing that year
3. Draw a tail churn event (contract termination) with payer-specific probability
4. Apply concentration amplifier: Top-1 share >30% → multiply aggregate NPR volatility by `1 + (top_1 − 0.30) × 2`; Top-2 >50% → +0.10; Top-3 >70% → +0.10 more

Rolls up to per-year NPR impact cone (P10/P50/P90), cumulative NPR + EBITDA at risk, concentration verdict, per-payer detail cards.

Key entry: `run_payer_stress(target_name, mix, total_npr_usd, total_ebitda_usd, horizon_years, n_paths) → PayerStressResult`.

---

## Adjacent files

- **[`rcm_mc/ui/payer_stress_page.py`](../../ui/payer_stress_page.py)** — web page at `/diligence/payer-stress`
- **[`tests/test_payer_stress.py`](../../../tests/test_payer_stress.py)** — 16 tests covering classifier, amplifier math, mix validation

---

## Refreshing the priors

The `PAYER_PRIORS` tuple was calibrated from:
- HFMA / MGMA annual rate-move surveys
- Public-company 10-K commentary (HCA / THC / UHS all disclose payer-specific rate movements)
- Healthcare Financial Management Association benchmarks

Refresh annually.

---

## Tests

```bash
python -m pytest tests/test_payer_stress.py -q
# Expected: 16 passed
```
