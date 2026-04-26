# Report 0093: Map Next Key File — `rcm_mc/ml/README.md`

## Scope

Reads `RCM_MC/rcm_mc/ml/README.md` end-to-end (315 lines, 29 KB). Closes Report 0092 Q1, Q2, Q3. Cross-corrects the catastrophic CLAUDE.md drift identified in Report 0092 MR503.

## Findings

### Header positioning

Title: `# ML (Machine Learning)`. First line: "Machine learning layer for metric prediction, anomaly detection, backtesting, and forecasting." **All models are numpy-only (no sklearn/scipy)** — Ridge implemented from closed-form `β = (XᵀX + αI)⁻¹Xᵀy`, conformal prediction provides distribution-free uncertainty intervals. Confirms CLAUDE.md "no new runtime dependencies" invariant.

### Module documentation coverage — 38 of 40 modules

Per Report 0092: 40 .py modules + `__init__.py`. README documents **38 in detail**, leaving 2 module gaps:

| Undocumented in README | Lines | Notes |
|---|---|---|
| `trained_rcm_predictor.py` | 468 | **Substantial — not mentioned anywhere in README.** |
| `bayesian_calibration.py` | 303 | **Not mentioned anywhere in README.** |

**MR509 below.** README is otherwise comprehensive; the gap is real not assumed.

### Public-surface vs documented modules

`__init__.py` re-exports 10 names (per Report 0092). README documents 38 modules. **Discrepancy:** 28 documented modules are accessed via direct path imports, never via `rcm_mc.ml.*`. Per the README this is intentional — the 10-name surface is the contract; the rest are internal but documented.

### Cross-corrections to CLAUDE.md (Report 0092 MR503)

CLAUDE.md Phase 4 says only "ridge_predictor + conformal" added. **README documents 38 modules** in this subpackage. CLAUDE.md is not just stale — it's **missing 36 modules**. MR503 escalates from "high" to "critical" doc rot.

### Resolution of Report 0092 questions

**Q1.** What is in the 29 KB README? → 38-module catalog with public-surface contract, fallback-ladder design, conformal-coverage discipline.

**Q2.** Which `*_predictor.py` is canonical?
- `ridge_predictor.py` (510L) — **canonical, primary engine for `DealAnalysisPacket`**, has conformal CI.
- `rcm_predictor.py` (505L) — **legacy Phase-1**, kept stable for backtester + CLI to avoid breaking test contracts. Same Ridge math, simpler `(value, lower, upper)` tuple output.
- `rcm_performance_predictor.py` (361L) — **forward-looking**, Holt-Winters + benchmark shrinkage for 12-month forecasts. Different scope.
- `trained_rcm_predictor.py` (468L) — **undocumented in README** (see MR509). Likely a fourth variant; status unknown.

**Q3.** `ensemble_methods` vs `ensemble_predictor` semantics:
- `ensemble_methods.py` (442L) — primitives: bagging / blending / stacking (closed-form numpy).
- `ensemble_predictor.py` (422L) — orchestrator: auto-selects best of {Ridge, kNN, weighted-median} per metric on held-out MAE.
**Not duplicates** — methods provides math, predictor uses it. Cross-correct Report 0092 MR505 (severity drop, not a duplicate).

### NEW high-priority discoveries (subsystems referenced in README, never mapped)

| Reference | Where in README | Status |
|---|---|---|
| `domain/econ_ontology.py` | lines 13, 71, 73 | **Cross-package never reported.** A causal-edges DAG used by anomaly_detector + ridge_predictor. New unmapped subpackage. |
| `pe_intelligence/` | line 297 | **Cross-package never reported.** "Wires the four canonical PE-intelligence cascades from `pe_intelligence/`." 4 cascades documented as canonical. |
| `data_public/deals_corpus.py` | lines 203-204 | Concrete file in the 313-file `data_public/` (Report 0091 unmapped #3). Used by survival_analysis for hold-year stratification. |
| `pe/predicted_vs_actual.py` | line 121 | Concrete file in `pe/` (Report 0091 unmapped #6). Source for portfolio_learning bias map. |
| `prediction_events` + `outcome_events` SQLite tables | line 173-174 | **NEW SQLite tables never reported.** Per Report 0017 + Report 0091 there are 22+ tables; these are 2 of them. Append-only ledger. |
| `hospital_benchmarks` SQLite table | lines 49, 85, 150, 156, 168, 192 | **NEW SQLite table.** HCRIS-derived benchmark pool used by ~6 of the 38 documented modules. Foundational. |
| `MODEL_QUALITY_REGISTRY` | line 303 | Registry pattern; predictor self-register for `/models/quality` scoreboard. |
| `/models/quality` HTTP route | line 301-303 | **Never reported as a server.py route.** |
| `/models/importance` HTTP route | line 285-286 | **Never reported as a server.py route.** Pairs with `ui/feature_importance_viz.py`. |
| `infra/cache.ttl_cache` | line 301 | Report 0054 caching cross-cut named caching but didn't pin the API. README confirms `ttl_cache` is the public surface. |

### Design discipline (architectural invariants spelled out at lines 307-314)

The README spells out 5 invariants ML modules must respect:

1. **No sklearn dependency** — closed-form Ridge in numpy.
2. **Conformal coverage guarantee** — 90% intervals.
3. **Graceful fallback ladder** — Ridge → weighted-median → benchmark percentile.
4. **Dollar metrics never predicted** — analyst inputs only (`net_revenue`, `gross_revenue`, `current_ebitda`, `total_operating_expenses`).
5. **Sanity-range clamps** — every numeric output clamped to a documented physical range (e.g., `(0.0, 0.40)` for denial rate).
6. **Provenance flag** — `synthetic-priors` until ≥30 real closed-deal labels, then flips to `real-cohort-N`.

These are **ml/-specific load-bearing invariants** that no other doc states.

### Apr 2026 cycle confirmation

Lines 211-303 of README explicitly mark **13 new ML surfaces** ("Predictor expansion cycle (Apr 2026)"). Cross-correlates with Report 0092 finding of 17 modules at `Apr 25 12:01` mtime. The mtime delta of 4 (17 vs 13) likely accounts for: README itself, conformal.py refresh, ridge_predictor.py refresh, model_quality.py being a "harness" not strictly a new surface but rewritten.

### Module size correlates with documentation depth

- Smallest documented modules (~150 lines): `survival_analysis`, `comparable_finder`, `efficiency_frontier` — get 5-line README entries.
- Largest documented modules (~500+ lines): `ridge_predictor`, `model_quality`, `labor_efficiency` — get 8-12-line README entries.
- The 2 undocumented modules (`trained_rcm_predictor` 468L + `bayesian_calibration` 303L) are **substantial** — undocumented but loaded.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR503-update** | **CLAUDE.md missing 36 of 38 ml/ modules** (escalation of original Report 0092 MR503) | Architecture doc rot is critical. Any onboarding off CLAUDE.md will not see 95% of the ml/ surface. | **Critical** |
| **MR509** | **`trained_rcm_predictor.py` (468L) and `bayesian_calibration.py` (303L) undocumented in ml/README.md** | Two substantial modules not in the otherwise-comprehensive README. May be dead code, mid-refactor, or intentional internal-only. | **Medium** |
| **MR510** | **Three "rcm predictor" variants** (cross-correct Report 0092 MR504) | Confirmed 3 are real (canonical / legacy / forward) plus 1 undocumented (`trained_*`). Branch that modifies one must consider the others. | High |
| **MR511** | **Two new SQLite tables (`prediction_events` + `outcome_events`) never schema-walked** | Per Report 0091: 22+ unmapped tables. These two are append-only ledgers; growth-unbounded risk if no retention. | Medium |
| **MR512** | **`hospital_benchmarks` table never schema-walked** | Foundational table used by ~6 ml/ modules. If schema changes, broad ml/ blast radius. | **High** |
| **MR513** | **2 unmapped sibling subpackages discovered: `domain/` (econ_ontology) and `pe_intelligence/`** | Per Report 0091 these were not on the unmapped list at all. **`domain/` is HIGH-PRIORITY discovery**. | **High** |
| **MR514** | **`MODEL_QUALITY_REGISTRY` is implicit registration pattern** | New predictors must self-register or they don't show up at `/models/quality`. Branch adds a predictor → forgets to register → silently invisible. | Medium |
| **MR515** | **`/models/quality` + `/models/importance` HTTP routes never reported in server.py inventory** | Reports 0005 + 0018 + 0019 covered server.py — these routes are missing. Either they're new (Apr 2026) or report missed them. | Medium |

## Dependencies

- **Incoming:** `analysis/packet_builder.py` (predicts via `ridge_predictor`), CLI `rcm-mc analysis`, server.py `/models/*` routes, scenario MC.
- **Outgoing:** numpy, sqlite3 (`prediction_events`, `outcome_events`, `hospital_benchmarks`), `domain/econ_ontology.py`, `pe_intelligence/*`, `data_public/deals_corpus.py`, `pe/predicted_vs_actual.py`, `pe/rcm_ebitda_bridge.py`, `infra/cache.ttl_cache`.

## Open questions / Unknowns

- **Q1.** What is in `trained_rcm_predictor.py` (468L) and how does it differ from the 3 documented `*_predictor.py` variants?
- **Q2.** What is in `bayesian_calibration.py` (303L)?
- **Q3.** What is the schema of `hospital_benchmarks`, `prediction_events`, `outcome_events` tables?
- **Q4.** Where are `/models/quality` + `/models/importance` registered in server.py?
- **Q5.** What is in `rcm_mc/domain/econ_ontology.py` (the unmapped sibling subpackage)?
- **Q6.** What are the 4 canonical PE-intelligence cascades in `pe_intelligence/`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0094** | Read `trained_rcm_predictor.py` head + tail (closes Q1). |
| **0095** | Map `rcm_mc/domain/` directory (closes Q5; hits new high-priority subpackage). |
| **0096** | Map `rcm_mc/pe_intelligence/` directory (closes Q6; hits new subpackage). |
| **0097** | Schema-walk `hospital_benchmarks` (closes Q3 partially). |
| **0098** | Grep server.py for `/models/quality` registration (closes Q4). |

---

Report/Report-0093.md written.
Next iteration should: map `rcm_mc/domain/` directory (HIGH-PRIORITY new subpackage discovered in this report).
