# value/

**Phase 4 — Value Creation Model.** Phase marker; actual value-creation math lives in `pe/` + `mc/`.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | **Phase 4 marker only.** Per-root-cause recoverable EBITDA feeds `rcm_mc.pe.rcm_ebitda_bridge` (and `pe.value_bridge_v2` when wired). Payer-behavior MC reuses `rcm_mc.mc.ebitda_mc`. |

## Why this package is thin

The four-phase RCM Diligence Playbook (Ingestion → Benchmarking → Root Cause → Value Creation) is the **narrative architecture**. Phase 4 — the value-creation layer — is the point where diligence findings become financial projections.

Actual value math already exists elsewhere:
- **EBITDA bridge**: `pe/value_bridge_v2.py` (primary) + `pe/rcm_ebitda_bridge.py` (v1 legacy). Takes packet → 7-lever unit-economics → projected EBITDA.
- **Monte Carlo**: `mc/v2_monte_carlo.py` produces the distribution around the bridge.
- **100-day plan**: `pe/value_creation_plan.py` + `pe_intelligence/value_creation_plan_generator.py` turns findings into dated actions.
- **Value tracker** (post-close): `pe/value_tracker.py` locks the plan and tracks actuals.

This package exists to hold the phase narrative. Source-of-truth lives where the math does.

## Where it plugs in

This is a placeholder. Direct consumers import from `pe/` and `mc/`, not here.
