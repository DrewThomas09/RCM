# real_estate/

**The "Steward module."** Targets the sale-leaseback blind spot that produced Steward (2016 MPT → 2024 bankruptcy), Prospect (2019 Leonard Green → 2025), and other REIT-backed hospital failures.

## The five-factor Steward pattern

Steward, Prospect, and similar platform failures shared **five co-occurring factors**:
1. REIT landlord (usually MPT or similar) with market-rate+ rents
2. High rent-to-revenue ratio (typical failure: 4-6%+)
3. Operator undercapitalization (thin equity cushion)
4. High Medicaid mix (margin-compressed payer)
5. Distressed refi calendar coinciding with rate-environment shift

`steward_score.py` pattern-matches the target against these five factors. When 4+ co-occur, the module flags **STEWARD_RISK_CRITICAL**.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — Steward / Prospect / MPT causal pattern. |
| `types.py` | Shared types — `StewardRiskTier` severity labels. Separate from regulatory `RegulatoryBand` — real-estate-specific. |
| `steward_score.py` | **5-factor Steward Score composite.** Pattern-match against the Steward/Prospect/MPT failure mode. |
| `lease_waterfall.py` | **Portfolio-level lease waterfall.** Year-by-year rent obligations through hold (default 10y), per-property + portfolio rollup, escalator math. |
| `capex_deferred_maintenance.py` | **Capex-wall detector.** HCRIS fixed-asset data × gross PPE → deferred-maintenance signature. Flags targets with suspiciously low maintenance capex relative to asset base. |
| `sale_leaseback_blocker.py` | **State-by-state sale-leaseback feasibility.** Per-state feasibility of sale-leaseback exit. Seeded from `content/sale_leaseback_blockers.yaml` (e.g., Connecticut HB 5316 phaseout). |
| `specialty_rent_benchmarks.py` | Specialty rent-benchmark lookup — reads `content/specialty_rent_benchmarks.yaml`, returns P25/P50/P75 band. `classify_rent_share` maps target's rent-to-revenue into a band. |

## Where it plugs in

- **Thesis Pipeline step 7** — Steward score + lease stress
- **Bankruptcy-Survivor Scan** — Steward score is one of the 12 deterministic pattern checks
- **Deal Autopsy** — Steward / Prospect are specific named failures in the autopsy library; this module feeds signature values for matching
- **Regulatory Calendar** — sale-leaseback blocker YAML references CT HB 5316 and similar state phaseouts

## Calibration

`steward_score.py` thresholds hand-calibrated from retrospective analysis of:
- Steward Health (2016 MPT sale-leaseback → 2024 bankruptcy)
- Prospect Medical (2019 Leonard Green + MPT → 2025 distress)
- Surgery Partners / similar PE healthcare failures with REIT-landlord component

## Tests

`tests/test_real_estate.py` + `tests/test_steward_score.py` — score thresholds + 5-factor co-occurrence detection + lease-waterfall escalator math.
