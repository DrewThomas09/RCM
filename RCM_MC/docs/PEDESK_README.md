# PEDESK Phase 1–4 — Branch README

Branch: `hotfix-login-bootstrap`. This document is the single landing
page for the PEDESK go-live fix sequence. Pair with
[`PHASE_4_DEPLOYMENT_READINESS.md`](PHASE_4_DEPLOYMENT_READINESS.md)
for the full IC-audit ledger.

## What this branch contains

A 14-commit fix sequence covering **UI sanitization (Phase 1)**, **data
ingestion fixes (Phase 2 × 5 sub-phases)**, **model retraining (Phase 3 ×
8 sub-phases)**, and **fact-check + deployment readiness (Phase 4)**.
Every fix carries an evidence file path and is exercised by the audit
harness at [`rcm_mc/data_public/ic_audit.py`](../rcm_mc/data_public/ic_audit.py).

## Commit chain (chronological)

| Commit | Phase | Subject |
|---|---|---|
| `84a6e21` | 1 | UI sanitizer chokepoint — `ck_sanitize_value` strips HTML before `_esc()` |
| `ac0b666` | 2A | Predictive Screener — HCRIS-direct AMC margins + SoT overlay + 12% denial + uplift cap |
| `cb4d413` | 2B | State Heatmap — CMI + DSH adjustments + teaching/community split |
| `4fca68e` | 2C | Public Comps — EDGAR feed + earnings math + LTM/Reported + MPW cap + sentiment override |
| `697ba48` | 2D | Rural Sourcing — multi-criterion thesis + nationwide query + per-state cap |
| `9771523` | 2E | Conferences — HIMSS27 Chicago, Leerink27 Miami, verified_source on every entry |
| `d4e9475` | 3A+3B | Random Forest replaces OLS (R² −1.090 → 0.50); MC distributions (P10/P50/P90 + 95% CI) |
| `79df4de` | 3C | Hold Analysis — N-count reconciliation + month-precision overlay + expanded outliers |
| `0626b85` | 3D | Sector Momentum + IRR Dispersion — Bayesian smoothing + TTV + zero-base + survivor-bias |
| `40bd584` | 3E | `/distress` page — MERC + Altman Z' + DCOH + AR-days |
| `0d5318b` | 3F | HCRIS reasonableness matrix at the `_get_latest_per_ccn()` chokepoint |
| `d035fa4` | 3G | Triage funnel pass rate 64.6% → 9.8% |
| `37fd56e` | 3H | Base-rates min-N=15 floor + OLS retrained with held-out validation |
| `095df35` | 4 | IC audit harness + deployment-readiness markdown |
| `00299f3` | side | SoT label refinement (`G-3 Ln 5 / G-3 Ln 3`) |
| `b172beb` | side | HCRIS scrub `_col` helper for sparse-input fixtures |
| `c16c207` | side | Phase 4 readiness file refresh |
| `7cc076f` | side | Backtest subtitle None-guard for the Phase 3H suppression cascade |
| `c5a107c` | side | Phase 4 readiness file refresh |

## Files added (production code)

| Path | Purpose |
|---|---|
| `rcm_mc/data_public/hcris_sot.py` | HCRIS Form 2552-10 worksheet-origin labels + AMC classifier + denial calibration + uplift cap |
| `rcm_mc/data_public/state_market_adjustments.py` | CMI proxy + DSH bracketed formula + teaching-vs-community state aggregation |
| `rcm_mc/data_public/edgar_rss.py` | SEC EDGAR Atom-feed adapter + days-since-reported + REIT cap + sentiment override |
| `rcm_mc/data_public/hold_precision_overlay.py` | Month-precision hold values for marquee deals from public records |
| `rcm_mc/data_public/sector_smoothing.py` | Bayesian smoothing + zero-base guard + TTV + realization-rate diagnostic |
| `rcm_mc/data_public/distress_models.py` | MERC + Altman Z' (private-firm 1983) + DCOH + AR-days + composite scoring |
| `rcm_mc/data_public/hcris_reasonableness.py` | 17-check Reasonableness Matrix scrubber for HCRIS ingestion |
| `rcm_mc/data_public/ic_audit.py` | IC audit harness — top-50 hospitals + top-200 deals + readiness summary |
| `rcm_mc/ml/random_forest_uplift.py` | Pure-numpy random-forest predictor with built-in MC distribution outputs |
| `rcm_mc/ui/data_public/distress_page.py` | `/distress` Bankruptcy + Distress dashboard renderer |
| `docs/PHASE_4_DEPLOYMENT_READINESS.md` | IC-format readiness file (10 verified guarantees, 5 remaining risks, GO recommendation) |
| `docs/PEDESK_README.md` | This file |

## What has been fixed

**Phase 1** — Library / Research / Portfolio / Backtest tabs no longer
render literal `<span>` text in the DOM. Sanitizer chokepoint at
`rcm_mc/ui/_chartis_kit_v2.py::ck_sanitize_value`; values flow as raw
integers/floats; CSS-only formatting via `.ck-kpi-value.sc-num`.

**Phase 2** — five surface fixes:
- **2A** Predictive Screener: −50.0% AMC margin placeholder eliminated;
  Source-of-Truth overlay maps every figure to its HCRIS Worksheet
  origin (`G-3 Ln 3`, `S-3 Pt I Ln 14 Col 2`, etc.); AMC denial
  calibration anchored at 12% (CAQH/AHA midpoint, [11%, 13%] band);
  uplift capped at total denied revenue (recovery_ceiling = 1.0).
- **2B** State Heatmap: Medicare share decoupled from operating margin
  via CMI proxy + DSH supplemental-payment estimate + teaching/
  community margin split. Old "Highest Medicare Dependency" panel
  removed and replaced with the Teaching-vs-Community Decomposition.
- **2C** Public Comps: SEC EDGAR Atom feed wired for HCA / THC /
  CYH (=CHS); earnings-timeline math now operates on filed-on date
  (`97d ago` not `7d ago`); LTM vs Reported flag exposed via
  `PublicComp.reporting_basis`; MPW EV/EBITDA capped at 12× during
  distress (was 24.36×); sentiment override downgrades `positive` →
  `mixed` for credit-tightening / restructuring headlines.
- **2D** Rural Sourcing: nationwide query restored (was AL-only);
  multi-criterion thesis combining Operating Margin (1.5×),
  Days Cash on Hand, Medicare Mix, and bed-count; per-state cap of
  `max(2, limit/10)` for diversity.
- **2E** Conferences: HIMSS 2027 → Chicago, Leerink 2027 → Miami
  Beach; `verified_source` URL + `verified_on` timestamp on all 16
  entries with per-row "verify · YYYY-MM-DD" chip.

**Phase 3** — eight model-retraining fixes:
- **3A** Random Forest replaces OLS — held-out R² **0.4959** (was
  −1.090); Medicare % demoted from #1 to #5; new top-3 drivers are
  operating_margin, cmi_proxy, commercial_pct.
- **3B** P10/P50/P90 + 95% CI on every Est. Uplift figure (free output
  of the 80-tree RF ensemble — each tree = one MC sample).
- **3C** Hold Analysis: corpus 735 / hold 507 / hold+MOIC 459 reconciled
  via Sample-size panel + per-chart N tags; month-precision overlay
  for 7 marquee deals; expanded outlier rules preserve Steward (13.5y
  long-stuck) and Envision (4.6y realized loss).
- **3D** Bayesian smoothing on small-N subsectors; TTV column;
  `safe_change_pct(min_reliable_base=3)` suppresses zero-base %;
  `/irr-dispersion` Survivor bias caveat panel + per-sector REALIZED
  column; publishable threshold raised from N≥3 to N≥5.
- **3E** `/distress` page deployed with MERC (FAIL ≥ 1.00), Altman Z'
  (FAIL < 1.23), DCOH (FAIL < 30d), AR Days (FAIL > 60d), composite
  scoring (Altman 35% / MERC 30% / DCOH 20% / AR 15%), and the
  AR > DCOH cross-trigger alert.
- **3F** HCRIS reasonableness matrix (17 checks: 10 drop-tier, 7
  warn-tier) hard-piped into `_get_latest_per_ccn()` so every
  downstream screen reads scrubbed rows. `RCM_MC_HCRIS_RAW=1` env
  override available for internal data-quality work.
- **3G** Triage funnel pass rate **64.6% → 9.8%** on 765-deal corpus.
  Medicaid hard cap at 40%, MERC hard cap at 1.00, EV/EBITDA cap at
  15×, EBITDA margin floor 12%, commercial mix floor 40%, min EV
  $100M, data completeness floor 75%.
- **3H** Base-rates min-N=15 floor on quartiles + rates (the 67%
  loss-rate-from-3-deals false-confidence pattern is gone). OLS
  retrained on real 80/20 split — held-out R² −0.015 (honestly
  reported); predictions suppressed when not validated.

**Phase 4** — IC audit harness exercises Phases 1–3 against the system-
of-record (HCRIS Form 2552-10, public-deals corpus). Pass 1: 50
hospitals × 6 fields = 300 verified field-rows with explicit worksheet
origins. Pass 2: 200 deals through the Phase 3G triage funnel. Output
to `docs/PHASE_4_DEPLOYMENT_READINESS.md` (14kB).

## What still needs to be fixed

Five remaining risks, each with an in-place mitigation. None block
deployment.

| ID | Severity | Area | Status |
|---|---|---|---|
| **R-001** | medium | Backtest regression — held-out R² ≈ −0.015. Predictions correctly suppressed; Phase 3A Random Forest (R² 0.50) is the canonical fallback. **Follow-up:** wire RF as the canonical predictor inside `_calibration_stats` |
| **R-002** | low | Altman Z' proxies — HCRIS slim extract carries G-3 only; balance-sheet inputs (working capital, retained earnings, equity, liabilities) imputed from sector-typical ratios. **Follow-up:** load full HCRIS Worksheet G for credit-committee-grade output |
| **R-003** | low | Hold precision — 7 marquee deals at month-precision; ~500 retain integer-year. Cluster note labels P25=P50 collisions explicitly. **Follow-up:** automate a public-record pull for the full corpus |
| **R-004** | low | Conferences refresh cadence — verified once (2026-05-06). Per-entry verify chip exposes staleness. **Follow-up:** curator re-verifies each fiscal year |
| **R-005** | low | EDGAR feed dependency — 24h on-disk cache survives transient failures. **Follow-up:** add a stale-cache banner when EDGAR has been unreachable for >48h |

## How to verify

Run the audit harness against the live HCRIS extract:

```python
from rcm_mc.data_public.ic_audit import (
    audit_top_revenue_hospitals, audit_pipeline_matches,
)

p1 = audit_top_revenue_hospitals(n=50)
p2 = audit_pipeline_matches(n=200)
print(f"Pass 1: examined={p1.total_examined} verified={p1.verified}")
print(f"Pass 2: PASS/WATCH/FAIL = {sum(1 for f in p2.findings if f.status=='verified')}/...")
```

The harness regenerates `docs/PHASE_4_DEPLOYMENT_READINESS.md` on
demand. Re-running after a code change produces a current readiness
file against branch HEAD.

Each phase ships with an in-line smoke test inside the relevant
module. Runtime sanity-check examples:

| Phase | Smoke |
|---|---|
| 1 | `from rcm_mc.ui._chartis_kit import ck_sanitize_value; assert ck_sanitize_value('<span class="mn">42%</span>') == '42%'` |
| 2A | `from rcm_mc.data_public.hcris_sot import worksheet_origin; assert worksheet_origin('net_patient_revenue') == 'G-3 Ln 3'` |
| 2B | `from rcm_mc.data_public.state_market_adjustments import dsh_uplift_pct; assert dsh_uplift_pct(0.45) == 0.13` |
| 2C | `from rcm_mc.data_public.edgar_rss import correct_sentiment; assert correct_sentiment('positive', title='credit tightening') == 'mixed'` |
| 3A | `from rcm_mc.ml.random_forest_uplift import get_model; _, r2 = get_model(); assert r2 > 0.40` |
| 3F | `from rcm_mc.data_public.hcris_reasonableness import is_clean; assert not is_clean({'net_patient_revenue': 10e6, 'operating_expenses': 1_000e6, 'beds': 100})` |
| 3G | `from rcm_mc.data_public.deal_screening_engine import screen_corpus; pass_rate ∈ [8%, 12%]` |
| 3H | `MIN_N_FOR_QUARTILES == 15` |

## Deployment go/no-go

**GO with three caveats** (R-001 backtest regression suppression,
R-002 Altman proxies disclosure, R-004 conferences refresh cadence).
All caveats are surfaced inline to the partner; none block deployment.
Working tree is clean against `hotfix-login-bootstrap`.
