# Hierarchical (Partial-Pooling) Benchmarking

**In one sentence**: empirical-Bayes shrinkage so a low-volume facility stops looking like an outlier on noise alone — the statistically correct way to rank small-n units.

---

## What problem does this solve?

A 12-bed facility posts a risk-adjusted O/E of 1.9 and lands at the top of the "worst operators" list. But with that little volume, 1.9 is mostly noise — its confidence interval spans 0.6 to 3.2. Ranking it against a 400-bed system measured to ±0.05 compares a coin-flip to a calibrated instrument. **Naive ranking systematically surfaces the smallest units at both tails** — you chase phantom outliers and miss real ones buried in mid-size noise.

Partners ask:
- *"Is this small site really an outlier, or is it just noisy?"*
- *"After accounting for sample size, who are the genuine over/under-performers?"*
- *"How much should I trust this facility's number?"*

This pairs directly with [`diligence/risk_adjustment`](../risk_adjustment/README.md): feed the per-unit risk-adjusted O/E ratios in, get shrunken, rank-stable estimates out.

---

## How it works

**Partial pooling** (empirical Bayes): pull each unit's estimate toward the group mean by an amount that depends on how noisy that unit is. A high-volume unit barely moves (its data speaks); a low-volume unit shrinks hard toward the mean (its data is weak).

```
τ²            between-unit variance, estimated by DerSimonian-Laird
μ*            precision-weighted grand mean = Σ y_i/(τ²+s_i²) / Σ 1/(τ²+s_i²)
B_i           shrinkage factor = τ²/(τ²+s_i²)     (1=trust the data, 0=full pool)
ŷ_i           shrunken estimate = μ* + B_i (y_i − μ*)
```

- **Single level** (`partial_pool`) — units against a common mean.
- **Two level** (`partial_pool_nested`) — providers within markets (or markets within states): units shrink toward their *group's* pooled mean; group means shrink toward the grand mean. Conditional-shrinkage composition.
- **Outlier flagging** is done on the **shrunken** CI vs the grand mean — a unit is only called an outlier when the signal survives shrinkage.

## The demo moment

```python
from rcm_mc.diligence.hierarchical_bench import partial_pool

res = partial_pool(
    units=["TinyClinic", "BigSystem", "MidA", "MidB", "MidC"],
    estimates=[1.90, 1.20, 1.05, 0.98, 1.02],     # risk-adjusted O/E
    standard_errors=[0.65, 0.04, 0.12, 0.12, 0.12],
)
print(res.headline)
for u in sorted(res.units, key=lambda u: u.rank_shrunken):
    print(u.unit, round(u.raw, 2), "→", round(u.shrunken, 2),
          "B=", round(u.shrinkage_factor, 2), "outlier" if u.is_outlier else "")
```

> Partial pooling over 5 units (grand mean 1.18, τ²=0.01): 1 survive as outliers after shrinkage. Biggest rank correction: TinyClinic moved #1→#3 (shrinkage 0.02).

TinyClinic's 1.90 collapses toward the mean (B≈0.02 — almost no trust in its own data); **BigSystem**, precise and genuinely high, is the real outlier.

---

## Where it plugs in

- **HCRIS Peer X-Ray / risk-adjusted benchmarking** — wrap the per-facility O/E ranking so small-n sites don't dominate the tails.
- **Bear Case** — only shrinkage-surviving outliers become evidence; phantom outliers are demoted with a documented reason.
- **Provenance graph** — outputs carry `source_module="diligence.hierarchical_bench"` and `citation_key="HB1"`.

## Files

```
hierarchical_bench/
├── __init__.py
└── shrinkage.py    # partial_pool / partial_pool_nested + DerSimonian-Laird τ²
```

## Honesty about the method

- **Normal-normal model** (Gaussian sampling + prior). For rates near 0/1 with tiny denominators, transform first (e.g. log-O/E).
- **DerSimonian-Laird τ²** is a moment estimator, mildly biased with very few units (< ~5); `tau_squared` and the unit count are returned so the caller can judge.

## Tests

```bash
python -m pytest tests/test_hierarchical_bench.py -q
# Expected: 11 passed
```
