# working_capital/

**Working-capital diligence** (Gap 7). Three submodules form the **NWC negotiation ammunition** partners bring to close — the peg target + the reserve catch + the gaming detector.

## The NWC negotiation dynamic

At close, purchase price is adjusted dollar-for-dollar by the delta between delivered NWC and the negotiated peg. A $5M peg delta = $5M cash swing. Sellers optimize for inflated closing NWC; buyers defend the peg. This module generates the partner's negotiation ammunition.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — 3 submodules. |
| `normalized_peg.py` | **Seasonality-adjusted NWC peg target.** Detrend by mean + adjust for quarterly seasonality indices, then average 12-24 months of trailing monthly NWC snapshots. Produces the defensible closing NWC peg. |
| `dnfb_reserve.py` | **Discharged-Not-Final-Billed estimator.** DNFB = claims discharged but not billed by close. Acute hospital typical: 3-5 days. Healthy RCM: 2-3. **Above 5 days = liquidity red flag** and likely understated reserve. |
| `pull_forward_detector.py` | **Pre-close collections pull-forward flag.** Sellers accelerate collections in the 60 days pre-close to inflate closing NWC. Flag when last-60-days cash-flow index is meaningfully above trailing months. |

## How it flows in negotiation

1. **Normalized peg sets the anchor** — partner walks in with a defensible 12-24 month average, seasonality-adjusted. Seller's higher peg needs justification.
2. **DNFB reserve estimator catches understated reserves** — if DNFB days exceed the acute-hospital norm, the closing balance overstates recoverable value. Partner demands a reserve.
3. **Pull-forward detector catches gaming** — if collections spiked in the final 60 days, the closing NWC is inflated. Partner requests a normalization adjustment.

Together: this is worth $3-10M on a typical healthcare services deal.

## Where it plugs in

- **Thesis Pipeline step 5** — runs alongside Phase 2 benchmarks
- **Bridge Auto-Auditor** — DNFB detector feeds one of the 21 lever categories (working-capital release)
- **LOI Drafter** — peg target and reserve recommendations populate specific LOI terms
- **Bear Case** — material pull-forward finding becomes `[B1]` bridge audit evidence

## Calibration anchors

- DNFB industry benchmark: acute hospitals 3-5 days; healthy RCM 2-3 days (HFMA survey)
- Seasonality indices: 12-quarter rolling mean from HCRIS
- Pull-forward threshold: last-60-days cash-flow index >1.15× trailing-90-day mean = flag

## Tests

`tests/test_working_capital*.py` — seasonality detrending + DNFB reserve math + pull-forward detection (fixture with known gaming pattern).
