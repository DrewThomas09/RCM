# physician_comp/

**Physician comp FMV + productivity-drift modeling** (Prompt J). Five submodules addressing deal-side comp analytics that VMG's FMV-MD does not cover (VMG is compliance-letter workflow; this is forward-looking simulation).

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — differentiation vs VMG / FMV-MD. |
| `comp_ingester.py` | **Provider roster ingester.** Payroll + W-2 + 1099 + scheduling → list of `Provider` dataclasses. Computes per-provider comp-per-wRVU, comp-as-%-of-collections, comp-per-hour-worked. |
| `fmv_benchmarks.py` | **FMV benchmark lookups.** Every function carries a "public-aggregate placeholder" caveat. Licensed MGMA / Sullivan Cotter / AMGA data replaces these when licensing is configured. |
| `productivity_drift_simulator.py` | **THE novel analytic — post-close "comp model reset" drift.** For each provider, simulate a new (lower $) comp model → model the productivity drop → revenue drag. This is what no VMG-style tool computes. |
| `stark_aks_red_line.py` | **Stark / AKS red-line detector.** Rule-based flags for configurations that have historically drawn FCA / DOJ attention. **Not legal advice** — analytic with statutory cites. |
| `earnout_advisor_enhancement.py` | **Earn-out advisor with provider-retention structure.** When top-5 provider concentration crosses thresholds, specific earn-out structures align seller's personal incentive with retained providers. |

## The novel analytic: productivity drift

Classic PE play: buy physician practice at $X → reset comp model down → immediately realize "savings." What this misses:

> Provider P currently earns $650K at 8,500 wRVUs. Buyer proposes reset to $550K at same wRVUs. At the new ratio ($64.70/wRVU vs current $76.50), P's productivity drops to 7,400 wRVUs. Revenue falls more than comp savings. **Net EBITDA impact negative.**

`productivity_drift_simulator.py` runs this simulation per provider on the roster. Output is the risk-adjusted expected EBITDA delta from a proposed comp reset.

## Stark / AKS red lines

`stark_aks_red_line.py` encodes pattern-matches against configurations that historically drew attention:
- Physician ownership of ASC where referrals dominate (Safe Harbor analysis)
- Medical-director comp above 75th percentile of peer benchmark (FMV concern)
- Volume / value-based referral incentives (Stark flat)
- Free or below-market office space / equipment to referring physicians

Each flag cites the relevant statute (42 U.S.C. §1320a-7b for AKS; 42 U.S.C. §1395nn for Stark). **Analytic flag, not legal advice** — flagged for legal review.

## Earn-out structure advisor

When top-5 provider concentration exceeds ~40% of EBITDA, `earnout_advisor_enhancement.py` recommends specific structures:
- Provider-specific earn-out tranches keyed to retention
- Cliff-vest vs graded-vest with wRVU targets
- Clawback provisions for voluntary departures within 24mo

## Where it plugs in

- **Physician Attrition** — uses same `Provider` dataclass
- **Bear Case** — productivity-drift + Stark/AKS flags feed OPERATIONAL theme
- **Deal MC** — comp-reset savings fed as a driver (but risk-adjusted per productivity drift)
- **LOI drafting** — earn-out advisor output suggests specific LOI terms

## Tests

`tests/test_physician_comp*.py` — comp-ingester math + FMV lookup contracts + productivity-drift simulator + Stark/AKS pattern detection.
