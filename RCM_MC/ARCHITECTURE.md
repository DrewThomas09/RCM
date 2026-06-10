# ARCHITECTURE — running design notes (session 2026-06-10)

## Data registry & provenance spine (as found)
- HCRIS: rcm_mc/data/hcris.py → `_get_latest_per_ccn()` (6,123 hospitals,
  latest authoritative filing per CCN; coordinate map verified vs 7 systems).
- Source→URL provenance: `rcm_mc/ui/_chartis_kit.SOURCE_URLS` + ck_source_link.
- Plausibility bands: `rcm_mc/core/margins.py` (margin −40…+30%, occupancy ≤105%).
- Gap registry: `rcm_mc/data/gap_fill_registry.py` (+ `rcm-mc data gaps`).
- Prediction bounds: `rcm_mc/ml/prediction_bounds.py`.
- Basis badges: ACTUAL / PREDICTED / ENTERED via `ck_basis_badge`.

## P2 — CIM Cross-Check / Variance Engine (this session)
**Spec.** A consultant enters management's CIM claims for a hospital target /
market; the engine computes independent public-data estimates for each claim
from the HCRIS universe scoped to (state [, bed band] [, target CCN]) and
renders a variance table: claim | independent estimate (value, n, source,
method, drill link) | variance % | flag (green ≤10%, yellow ≤25%, red >25%,
grey UNVERIFIABLE when the public side is a gap). One-click variance memo
(text) + CSV export listing claim / estimate / variance / source / suggested
expert-call question. Claims are ENTERED; estimates are ACTUAL with
source links. Claim types in slice 1 (hospital subsector):
- market_size_dollars  → Σ net_patient_revenue in scope (state patient-revenue base)
- provider_count       → count of HCRIS hospitals in scope
- median_operating_margin_pct → median margin in scope (plausible band only)
- medicare_share_pct / medicaid_share_pct → median day-share in scope (NaN-aware)
- inpatient_days       → Σ total_patient_days in scope
- target_net_revenue_dollars → the target CCN's own filed NPR (CIM top line vs filing)
**Module layout.** Pure logic in `rcm_mc/diligence/cim_crosscheck.py`
(estimators + variance + memo text, fully unit-testable, no UI imports);
page in `rcm_mc/ui/cim_crosscheck_page.py` (GET form → table → exports);
route `/diligence/cim-crosscheck` + palette + Diligence sub-nav.
**Honesty rules.** Estimates name n and vintage; margin medians use the core
plausible band; unverifiable ≠ zero; the engine never fabricates an estimate
when scope is empty. Variance against a Σ-claim uses the same scope the
consultant chose — scope is printed on the table header.

## Deploy/verify loop (canonical)
main merge → deploy.yml (test gate → SSH droplet → restart pedesk.service →
public pedesk.app/healthz + guide-health) → sandbox verification = deploy-run
conclusion + local playwright screenshots + route_walker markers on the same
SHA (sandbox egress cannot reach pedesk.app — DECISIONS.md #1).
