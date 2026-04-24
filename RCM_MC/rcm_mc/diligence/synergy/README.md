# synergy/

**Synergy realization** (Gap 8) — two analytics that reality-check seller-claimed synergies.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — two submodules. |
| `integration_velocity.py` | **EHR migration cost library + time estimator.** Epic migration: 18-36 months, ~$100-200K per provider + $500K-$1.5M per bed at system level. Seeded from published case studies. |
| `cross_referral_reality_check.py` | **Sister-practice referral test.** Sellers claim cross-referral synergy between sister practices. This uses `referral/leakage_analyzer.py` data to reality-check the claim — how much cross-referral is actually happening vs claimed. |

## The pattern

Seller decks always promise synergies. Partners always distrust them. This module provides **two specific reality checks**:

### Integration velocity

"We'll consolidate to Epic in Y1" — usually unrealistic. `integration_velocity.py` benchmarks proposed timelines against published case studies. Epic migrations are 18-36 months (not "Year 1"); cost is $100-200K per provider + $500K-$1.5M per bed. Seller's 12-month promise gets a haircut or a red flag.

### Cross-referral claims

"Our sister practices will refer to each other" — often fictional. If the referral graph already shows 0% cross-flow, a promised 30% cross-flow post-close isn't a synergy, it's a wish. `cross_referral_reality_check.py` compares claimed vs actual referral data.

## Where it plugs in

- **Bridge Auto-Auditor** — synergy claims in the bridge go through these reality checks before becoming bridge levers
- **Bear Case** — OVERSTATED synergies feed `[B1/B2/B3]` evidence

## Related

- `referral/leakage_analyzer.py` provides the cross-referral data this module queries
- `pe_intelligence/synergy_*` modules (credibility scorer, modeler, sequencing scorer) work at a higher abstraction — this module does the specific realization checks

## Tests

`tests/test_synergy*.py` — EHR migration benchmark lookups + cross-referral reality-check math.
