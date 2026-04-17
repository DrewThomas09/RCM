# Analytics

Advanced analytics for initiative impact measurement and service line profitability. Provides causal inference, counterfactual modeling, and DRG-level P&L decomposition -- all numpy-only with no external ML dependencies.

| File | Purpose |
|------|---------|
| `causal_inference.py` | Three causal methods (Interrupted Time Series, Difference-in-Differences, pre-post comparison) for measuring initiative impact |
| `counterfactual.py` | "What would EBITDA be if we hadn't done X?" modeling using causal estimates and ramp curves |
| `service_lines.py` | Maps DRG codes to service lines and computes per-service-line P&L from claim-level data |
