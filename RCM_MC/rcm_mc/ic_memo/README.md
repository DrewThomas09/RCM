# ic_memo/

One-click IC-memo generator at `/diligence/ic-memo/<deal_id>`. Renders an 8-section investment-committee memo that bundles every diligence module's headline output into a print-ready HTML document.

| File | Purpose |
|------|---------|
| `memo.py` | Top-level memo builder. Pulls from the `DealAnalysisPacket`, gathers regulatory + bear-case + covenant blocks, returns a structured memo dataclass |
| `render.py` | HTML rendering — uses the shared `_ui_kit.shell()` so the memo matches workbench styling. `@media print` CSS for clean Cmd-P → PDF |
| `scenarios.py` | Section that lays out base / upside / downside cases with MOIC / IRR cones |

## What the memo contains

1. Deal metadata + recommendation (`PROCEED` / `PROCEED_WITH_CONDITIONS` / `DECLINE`)
2. Waterfall + KPIs
3. Bankruptcy scan + autopsy matches
4. Counterfactual sensitivity
5. Public-comp context
6. Auto-injected regulatory timeline block (from `regulatory_calendar`)
7. Auto-injected bear-case block (from `bear_case`)
8. Open questions for the banker + walkaway conditions

## Sister module: ic_binder/

`ic_binder/` builds the **full deal book** — 50–100 pages of supporting analysis. `ic_memo/` is the **executive summary** that fronts it.
