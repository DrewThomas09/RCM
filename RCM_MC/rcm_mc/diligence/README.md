# diligence/

The analytic core. Each subdirectory is one named diligence question with its own README, prior library, and Monte Carlo (where applicable). The 7 cycle-shipped modules — HCRIS X-Ray, Regulatory Calendar, Covenant Lab, Bridge Audit, Bear Case, Payer Stress, Thesis Pipeline — are documented in the top-level [RCM_MC/README.md](../../README.md). The summary below covers everything in this folder.

## Top-level files

| File | Purpose |
|------|---------|
| `_pages.py` | Server-rendered HTML pages for the diligence surfaces — one route per submodule |
| `ccd_bridge.py` | Cross-checks Care Compare data against HCRIS to catch data-quality regressions |
| `comparable_outcomes.py` | Looks up historical PE outcomes for similar deals, used by `bear_case` and `exit_timing` |
| `INTEGRATION_MAP.md` | Cross-module dependency map (which engine reads from which) |
| `SESSION_LOG.md` | Implementation log from the cycle that shipped these modules |

## Subpackages

Each has its own README — click the folder for the deep reference.

| Package | What it answers |
|---------|-----------------|
| [bear_case/](bear_case/) | Auto-generated counter-narrative for the IC memo |
| [benchmarks/](benchmarks/) | HFMA-band peer benchmarks across 20+ RCM KPIs |
| [bridge_audit/](bridge_audit/) | Banker-bridge reality check vs ~3,000 historical initiative outcomes |
| [checklist/](checklist/) | 40+ task workflow tracker across 5 phases |
| `counterfactual/` | "What if the lever didn't work?" sensitivity sweeps |
| [covenant_lab/](covenant_lab/) | Capital-stack stress lab (500 paths × 20Q × 4 covenants) |
| `cyber/` | Cyber-incident probability + EBITDA impact prior |
| `deal_autopsy/` | Pattern-match against 12 named PE healthcare failures |
| `deal_mc/` | Headline value Monte Carlo (1,500–3,000 trials, 8 drivers) |
| `denial_prediction/` | Ridge predictor over claims features with conformal bands |
| `exit_timing/` | IRR curve × buyer-type fit (Y2–Y7, 4 archetypes) |
| [hcris_xray/](hcris_xray/) | 17,701 cost reports × 15 metrics × cohort-matched peers |
| `ingest/` | Inbound data parsing for hospital fixtures + claims |
| `integrity/` | Data-integrity checks against the source files |
| `labor/` | Workforce / wage-index analysis |
| `ma_dynamics/` | MA penetration, V28 coding compression risk, Star ratings |
| `management_scorecard/` | Role-weighted exec scoring (CEO 35% / CFO 25% / COO 20%) |
| `patient_pay/` | Self-pay collectibility + bad-debt projections |
| [payer_stress/](payer_stress/) | 19 payers × rate-shock priors × HHI amplifier × 500-path MC |
| `physician_attrition/` | Per-NPI flight risk → revenue-at-risk rollup |
| `physician_comp/` | Comp benchmarking vs MGMA bands |
| `physician_eu/` | Per-MD P&L with drop-candidate identification |
| `quality/` | Care Compare star + HCAHPS + complication / readmission rates |
| `real_estate/` | Lease intensity + landlord risk |
| `referral/` | Referral-graph leakage analysis |
| `regulatory/` | Federal Register monitoring layer |
| [regulatory_calendar/](regulatory_calendar/) | 11 curated CMS/OIG/FTC events × thesis-driver kill-switch |
| `reputational/` | Press / litigation / sentiment scan |
| `root_cause/` | Drill-down attribution for KPI gaps |
| `screening/` | Universe-level filtering before deep diligence |
| `synergy/` | Tuck-in M&A synergy modeling |
| [thesis_pipeline/](thesis_pipeline/) | Orchestrator that runs the 19-step diligence chain |
| `value/` | Value-creation thesis builder |

## Conventions across all submodules

- One `README.md` per module with verdict thresholds + prior sources
- Curated priors live in YAML or as `dataclass` tuples — never embedded in scoring code
- Every Monte Carlo accepts a `seed` for deterministic replay
- Every output dataclass carries `source_module` + `citation_key` for IC-memo provenance
- Verdict bands are PASS / CAUTION / WARNING / FAIL with documented numeric cutoffs
