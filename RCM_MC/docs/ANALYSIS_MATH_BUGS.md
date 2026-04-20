# Analysis-math bugs discovered during Phase A of the Demo_Real sprint

Log of analysis / valuation-math bugs found in passing while fixing
the targeted Phase-A bugs (DCF FCF column and LBO MOIC/IRR). **These
are NOT fixed in Phase A** — logged for a follow-up pass so the
targeted phase stays scoped.

## Open

### 1. DCF sensitivity matrix never renders

- **Model output key:** `sensitivity["wacc_vs_terminal_growth"]`
  ([`rcm_mc/finance/dcf_model.py::_build_sensitivity`](../rcm_mc/finance/dcf_model.py))
- **UI reads:** `sensitivity.get("wacc_x_growth", sensitivity.get("matrix", []))`
  ([`rcm_mc/ui/models_page.py:172`](../rcm_mc/ui/models_page.py))
- **Net effect:** the WACC × Terminal Growth sensitivity heatmap
  never renders on `/models/dcf/<id>`. The model silently computes
  35 cells nobody sees.
- **Double drift:** wrong key name *and* wrong shape. Model returns
  a flat list `[{"wacc", "terminal_growth", "enterprise_value"}, …]`
  but the UI expects a nested shape `[{"wacc", "values": [{"ev"}, …]}, …]`.

### 2. `/models/dcf` and `/models/lbo` link out to `/models/financials/<id>` (3-Statement)

- Route appears on the DCF and LBO pages but has not been verified
  end-to-end in this phase. Dangling cross-link risk if the 3-Stmt
  renderer has its own drift issues.

### 3. `/analysis` landing still advertises `/dcf` and `/market-analysis` top-level routes that 404

- `curl /dcf` and `curl /market-analysis` both return 404.
- Either the routes were removed and the landing copy is stale, or
  the routes were renamed and the landing was not updated.

---

(additional entries will be appended as Phase A progresses)
