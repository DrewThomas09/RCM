# physician_eu/

**Physician Economic Unit Analyzer — per-provider P&L.** Answers the question partners ask every physician-group deal: "which of these providers are net-negative contributors even at fair-market comp?"

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `features.py` | **Per-provider contribution-margin math.** `contribution_margin(p) = collections(p) − direct_cost(p) − allocated_overhead(p)`. Deterministic per-provider envelope. |
| `analyzer.py` | **Roster-level orchestrator.** Ranks by contribution margin, finds loss-makers, quantifies drop-them-at-close bridge lever. |

## The drop-candidate lever

Partners need to know: of N providers in the roster, how many are net-negative contributors at FMV comp? Those are "drop candidates" — removing them at close boosts EBITDA without affecting anything else.

Typical finding on PPM roll-ups: 15-25% of the roster is net-negative when overhead is allocated correctly. `analyzer.py` quantifies the EBITDA uplift from pruning drop-candidates and feeds it into Deal MC as a positive-lever driver.

## Output

Partner-facing "Roster Optimization" section with:
- Per-provider contribution envelope (revenue / comp / overhead / contribution)
- Ranked table sorted by contribution margin (ascending — loss-makers first)
- Drop-candidate list with total EBITDA uplift
- Replacement-availability flag (drop-candidates in high-demand specialties can't be dropped without replacement)

## Where it plugs in

- **Thesis Pipeline step 11** — runs alongside physician_attrition
- **Deal MC** — drop-candidate EBITDA uplift is a positive driver in the bridge
- **LOI drafting** — drop-candidate recommendations feed specific close-date provisions

## Related

- `physician_comp/` shares the `Provider` dataclass
- `physician_comp/productivity_drift_simulator.py` asks the inverse question: if we reset comp on a KEEPING provider, how much productivity drops?

## Tests

`tests/test_physician_eu.py` — contribution-margin math + roster ranking + drop-candidate flagging.
