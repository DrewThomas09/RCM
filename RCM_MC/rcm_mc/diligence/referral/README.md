# referral/

**Referral-leakage + provider-concentration diligence** (Prompt M, Gap 5).

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — two submodules. |
| `leakage_analyzer.py` | **Referral graph analyzer.** Referring-provider → destination edges → share retained in network vs leaked to competitors. |
| `provider_concentration.py` | **"Provider X controls $Y of revenue"** — the call-out line the partner-voice memo wants. Concentration stats + departure stress test. |

## Why referral leakage matters

For a physician practice or specialty platform, the referral network IS the asset. Partner statement: "A physician practice isn't really selling patients — it's selling the referral network."

If 30% of outbound referrals leak to competitors, that's a standing 30% revenue opportunity the platform hasn't captured. If 80% are retained, the moat is real. `leakage_analyzer.py` surfaces the breakdown.

## Provider-concentration stress

`provider_concentration.py` answers the concentration question two ways:
1. **Simple stat**: "Provider X controls $Y of revenue" — the call-out line for the memo
2. **Departure stress test**: "if top-N providers all leave, what happens to revenue?"

Combined with `physician_attrition/`, this quantifies retention-dependent revenue.

## Where it plugs in

- **Thesis Pipeline** — runs when referral graph data available
- **Synergy / cross-referral reality check** (`diligence/synergy/cross_referral_reality_check.py`) — uses this data to reality-check seller-claimed cross-referral synergies
- **Deal MC** — concentration tail as a driver

## Tests

`tests/test_referral*.py` — graph traversal + concentration math + departure stress scenarios.
