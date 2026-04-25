# site_neutral/

CY2026 OPPS site-neutral payment-rule modeling. Quantifies the EBITDA hit from site-neutral payment expansion (HOPD → freestanding-equivalent rates).

| File | Purpose |
|------|---------|
| `codes.py` | CMS HCPCS code list expanded to include site-neutral candidates per CY2026 NPRM |
| `asc_opportunity.py` | Inverse case — when site-neutral *helps* (the ASC platform thesis) |
| `impact.py` | Per-target impact estimator — share of HOPD revenue × proposed rate cut × volume elasticity |
| `revenue_at_risk.py` | Aggregates per-code impact into a single revenue-at-risk number for Deal MC |

## Hooks

- Feeds `diligence/regulatory_calendar/` site-neutral event impact priors
- Feeds Deal MC's `reg_headwind_usd` driver
- Surfaced on the workbench Risk tab when target HOPD revenue share > 30%
