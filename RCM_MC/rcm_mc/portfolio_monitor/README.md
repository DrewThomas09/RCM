# portfolio_monitor/

Hold-period actual-vs-plan dashboard at `/portfolio/monitor`. Tracks every active deal's actual KPIs against the underwriting case, surfaces variance, and flags drift.

| File | Purpose |
|------|---------|
| `dashboard.py` | Server-rendered dashboard — one row per deal, columns for plan vs actual on the headline KPIs, color chips for variance |
| `snapshot.py` | Per-quarter snapshot writer — captures actuals into `quarterly_snapshots`, computes variance |
| `variance.py` | Variance attribution — decomposes plan-vs-actual gap by lever (denial rate, A/R days, payer mix shift, volume, etc.) |

## Why a separate dashboard from the workbench

The workbench is for **diligence** — pre-close, single-deal, analyst-driven. The portfolio monitor is for **operations** — post-close, multi-deal, partner-driven. Different audience, different cadence, different KPIs. Keeping them separate avoids the "Bloomberg terminal trying to be a portfolio review" problem.
