# irr_attribution/

ILPA-style IRR decomposition. Splits realized fund IRR into the components an LP wants to see: revenue growth, margin expansion, multiple arbitrage, leverage, time, and luck.

| File | Purpose |
|------|---------|
| `irr.py` | XIRR + MIRR helpers (pure-numpy Newton's method root-find) |
| `decompose.py` | Top-level `decompose(deal)` → component contribution waterfall |
| `components.py` | Per-component decomposers: revenue, margin, multiple, leverage, time, FX, dividends |
| `fund.py` | Fund-level rollup across deals — aggregate attribution and dispersion |
| `ilpa.py` | ILPA-template-compliant report renderer |

## What it answers

The classic LP question: *"You returned 2.4× over 4 years. How much of that was operating improvement vs multiple arbitrage vs leverage?"* The decomposition makes each component dollar-explicit.

Used by:
- LP digest (`reports/lp_update.py`)
- Fund-level dashboard (`portfolio/portfolio_dashboard.py`)
- Post-realization deal autopsy
