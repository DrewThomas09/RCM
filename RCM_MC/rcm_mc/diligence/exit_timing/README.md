# exit_timing/

**Exit Timing + Buyer-Type Fit Analyzer.** Answers the two questions PE partners face at year 3-5 of every deal: **when** should we exit, and **to whom**.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `analyzer.py` | **`ExitTimingReport` orchestrator** — composes curve + buyer fit + recommendation. |
| `curves.py` | **IRR / MOIC / proceeds curves Y2-Y7.** Takes Deal MC year-by-year EBITDA → per-year `(year, moic, irr, proceeds)` + sharpe-like reward / hold-risk ratio. |
| `buyer_fit.py` | **Per-buyer-type fit scorer.** Target profile → 0-100 fit per buyer archetype. |
| `playbook.py` | **Buyer-type playbooks.** Partner-facing economics per exit channel: multiple premium/discount vs public comp median, time-to-close, close-certainty. |

## Recommendation algorithm

1. Build MOIC/IRR curve for candidate exit years 2-7
2. Score 4 buyer types (Strategic / PE Secondary / IPO / Sponsor-Hold) on scale fit × synergy fit × financing environment × regulatory timing
3. Pick the `(year, buyer_type)` pair with highest **probability-weighted proceeds**

## The buyer types

| Buyer | Typical multiple vs public comp median | Time-to-close | Close-certainty |
|-------|-----|-----|-----|
| Strategic | +0.5-2.0× (synergy-driven premium) | 9-18 months (FTC/AG review) | 65-85% |
| PE Secondary | Flat (0-0.5× discount) | 4-6 months | 80-95% |
| IPO | 0-3× premium depending on sector momentum | 6-12 months | 30-60% |
| Sponsor-Hold (continuation) | Hold + refi | 3-4 months | 90%+ |

Values hand-calibrated per subsector in `content/buyer_playbook.yaml`.

## Where it plugs in

- **Thesis Pipeline step 19** — final step, recommendation feeds Deal Profile
- **Bear Case** — failing 1.5× MOIC hurdle at recommended year becomes `[E1]` evidence
- **UI** at `/diligence/exit-timing`

## Tests

`tests/test_exit_timing.py` — curve math + buyer-fit scoring + recommendation selection.
