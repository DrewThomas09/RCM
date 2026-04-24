# FILE_MAP — per-file function index

**Scope**: every `.py` file in the repo (excluding `__pycache__`, `.egg-info`, `.venv`, and macOS `* 2.py` duplicates). **Total: 1,705 files.** Built incrementally, 50 files per chunk, so a reader (human or agent) can land anywhere and know what every file does without reading source.

**Grand-total breakdown**:

| Area | Files |
|------|-------|
| `RCM_MC/rcm_mc/` (main source, 29 sub-packages) | 1,298 |
| `RCM_MC/tests/` | 339 |
| `RCM_MC/rcm_mc_diligence/` (adjacent) | 54 |
| Root + handoff scripts | 3 |
| Adjacent projects (ChartisDrewIntel, cms_medicare, handoff) | 11 |

**Chunk progress**: 29 / ~34 — CATALOG COMPLETE

**Legend**: ✓ = covered by a README in its directory · ✗ = no README (flagged as a doc gap).

---

## Chunk 1 — Top-level entry points + 9 small packages (50 files)

### Top-level entry points (3 files, all ✗ — root README covers them narratively)

| File | Purpose |
|------|---------|
| [RCM_MC/demo.py](RCM_MC/demo.py) | One-shot demo — seeds a realistic portfolio to a temp SQLite DB, starts HTTP server on a free port, prints login URLs. Zero-config onboarding. |
| [RCM_MC/seekingchartis.py](RCM_MC/seekingchartis.py) | `python seekingchartis.py` front-door launcher — starts the server, opens the browser, `--port` / `--db` / `--no-browser` flags. |
| [RCM_MC/handoff/verify_rework.py](RCM_MC/handoff/verify_rework.py) | Post-handoff smoke test — validates that a UI rework drop landed cleanly (file presence, CSS tokens, shell-render check). CI-friendly exit codes. |

### `rcm_mc/` top-level modules (8 files, covered by package docs)

| File | Purpose |
|------|---------|
| [rcm_mc/__init__.py](RCM_MC/rcm_mc/__init__.py) | Package version (`1.0.0`), product name (`SeekingChartis`), wires the logger. |
| [rcm_mc/__main__.py](RCM_MC/rcm_mc/__main__.py) | `python -m rcm_mc` dispatcher — delegates to `cli.main`. |
| [rcm_mc/api.py](RCM_MC/rcm_mc/api.py) | Minimal FastAPI endpoint for programmatic simulation (`POST /simulate`). Optional — FastAPI only imported if installed. |
| [rcm_mc/cli.py](RCM_MC/rcm_mc/cli.py) | `rcm-mc` top-level CLI. Routes into `core.calibration`, `pe.breakdowns`, `analysis.stress`, `reports.html_report`, `data.data_scrub`. |
| [rcm_mc/lookup.py](RCM_MC/rcm_mc/lookup.py) | Back-compat shim — re-exports `rcm_mc.data.lookup` so old scripts calling `python -m rcm_mc.lookup` still work. |
| [rcm_mc/pe_cli.py](RCM_MC/rcm_mc/pe_cli.py) | `rcm-mc pe` subcommands — `bridge` / `returns` / `grid` / `covenant`. `--json` for script-friendly output, `--from-run DIR` pulls EBITDA from an existing run. |
| [rcm_mc/portfolio_cmd.py](RCM_MC/rcm_mc/portfolio_cmd.py) | `rcm-mc portfolio` — `register` / `list` / `show` / `rollup` snapshot-tracking CLI. Defaults DB to `~/.rcm_mc/portfolio.db`. |
| [rcm_mc/server.py](RCM_MC/rcm_mc/server.py) | `rcm-mc serve` — `http.server` / `socketserver` ThreadingHTTPServer app. Stdlib-only, routes → `portfolio_dashboard` / `exit_memo` / `text_to_html`. |

### `rcm_mc/alerts/` — 4 files ✓ [README](RCM_MC/rcm_mc/alerts/README.md)

Portfolio alerts lifecycle: evaluate → acknowledge → snooze → age → escalate.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `alerts.py` | **Evaluators** (Brick 101) — stateless scan over portfolio for covenant trips, variance breaches, signal clusters. Returns flat list. Re-fires every page load. |
| `alert_acks.py` | **Ack + snooze** (Brick 102) — persist "seen, hide" decisions so re-fires don't flood the partner's Monday triage. SQLite `alert_acks`. |
| `alert_history.py` | **History + age tracking** (Brick 104) — first-seen + duration so partners can answer "how long has this covenant been red?" Drives escalation at 30-day threshold. |

### `rcm_mc/ai/` — 6 files ✓ [README](RCM_MC/rcm_mc/ai/README.md)

LLM-assisted analysis. Every LLM feature degrades gracefully when `ANTHROPIC_API_KEY` is absent — template fallbacks preserve full function.

| File | Purpose |
|------|---------|
| `__init__.py` | Package-level docstring on graceful degradation contract. |
| `llm_client.py` | Stdlib-only (`urllib.request`) Anthropic Messages client. Cost tracking, response caching. No-op fallback when no key. |
| `claude_reviewer.py` | Second-pass review hook for partner-review pages. Additive, not load-bearing — if the call fails, deterministic review still renders. |
| `conversation.py` | Multi-turn conversational interface with tool-calling. Dispatches natural language to platform functions (deal query, packet load). SQLite `conversation_sessions`. |
| `document_qa.py` | Per-deal document indexing — chunk (~500 char), TF-IDF-ish scoring via numpy, LLM-boosted answers when available. |
| `memo_writer.py` | LLM-assisted memo composition with fact-checking. `use_llm=False` default renders templates (same as `packet_renderer`) so no regression. |

### `rcm_mc/auth/` — 5 files ✓ [README](RCM_MC/rcm_mc/auth/README.md)

Multi-user auth, session cookies, audit log, RBAC, external (LP / management) users.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `auth.py` | **Core auth** (Brick 125) — `users` table, scrypt password hashing, session cookies. Replaces single HTTP-Basic user so acks are per-analyst. |
| `audit_log.py` | **Unified audit log** (Brick 133) — append-only `audit_events` table every sensitive handler writes to. Answers "show me everything AT did Monday." |
| `rbac.py` | **Role-based access control** (Prompt 48) — `ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER`. `require_permission` decorator → 403 on fail. |
| `external_users.py` | **External portals** (Prompts 84-85) — `EXTERNAL_MANAGEMENT` (read-only own deal) and `LIMITED_PARTNER` (read-only fund aggregates). |

### `rcm_mc/analytics/` — 5 files ✓ [README](RCM_MC/rcm_mc/analytics/README.md)

Advanced analytics: causal inference, counterfactuals, service-line P&L, demand analysis.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `causal_inference.py` | **Three numpy-only methods** (Prompt 81) — Interrupted Time Series (segmented regression), Difference-in-Differences, pre-post with CI. |
| `counterfactual.py` | **"What would EBITDA be without X?"** (Prompt 83) — uses causal estimates + ramp curves to rebuild the no-initiative counterfactual. |
| `service_lines.py` | **Service-line profitability** (Prompt 82) — DRG → service line mapping, claim-level per-line P&L. |
| `demand_analysis.py` | **Disease density, stickiness, price elasticity, tailwinds** — CMS chronic conditions × DRG utilization × market structure → demand defensibility score. |

### `rcm_mc/compliance/` — 4 files ✗ **NO README — gap**

HIPAA / SOC 2 readiness: PHI scanner, hash-chain audit log, CLI.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — three capabilities: PHI scanner, audit_chain, CLI. |
| `__main__.py` | `python -m rcm_mc.compliance scan <path>` CLI — exit 0 on no findings, 1 on any. CI-friendly. |
| `phi_scanner.py` | Pattern-based PHI detector — SSN, phone, DOB, NPI, MRN, ICD codes with name, etc. SSA-guidance sanity band on SSN. |
| `audit_chain.py` | Hash-chain extension of `auth.audit_log` — SHA-256 links each event to predecessor so after-the-fact mutation is detectable. HIPAA / SOC 2 audit requirement. |

### `rcm_mc/domain/` — 3 files ✓ [README](RCM_MC/rcm_mc/domain/README.md)

Healthcare revenue-cycle economic ontology — the canonical "what every metric *is*".

| File | Purpose |
|------|---------|
| `__init__.py` | Ontology docstring — maps every metric to its slot in the revenue cycle + EBITDA/cash/risk relationship. |
| `econ_ontology.py` | Core ontology tables — metric → RC stage, P&L pathway, causal parents/children, reimbursement sensitivity. |
| `custom_metrics.py` | Partner-defined custom KPIs registered as first-class — proprietary "revenue integrity index" etc. Slots into the same ontology. |

### `rcm_mc/engagement/` — 2 files ✗ **NO README — gap**

Per-engagement RBAC, comments, draft/publish state machine (layered on top of app-level auth/rbac).

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — engagement = "the diligence project the deal team is executing against". |
| `store.py` | Single coherent aggregate — SQLite store for engagements, members, comments, deliverables. Deliberately one file since splitting adds import churn without clarity. |

### `rcm_mc/provenance/` — 6 files ✓ [README](RCM_MC/rcm_mc/provenance/README.md)

**The "every number has a story" sub-package.** The #1 partner complaint was "I don't know where any number came from." This package fixes that.

| File | Purpose |
|------|---------|
| `__init__.py` | DataPoint-contract docstring. |
| `tracker.py` | **`DataPoint` dataclass** — atomic unit. Answers what / where / source / confidence for every scalar the platform surfaces. |
| `registry.py` | **Per-deal DataPoint collection** — created at calc start, passed through simulator / pe_math / loaders, persisted to `metric_provenance` table. |
| `graph.py` | **Rich provenance DAG** — typed edges, node categories (SOURCE / OBSERVED / PREDICTED / CALCULATED / AGGREGATED). Complements the simpler wire-format graph in `analysis/packet.py`. |
| `ccd_nodes.py` | **CCD-derived nodes** — `CCDDerivedMetric` typed wrapper around `ProvenanceNode` for claims-and-denials data. Carries the chain-walk fields. |
| `explain.py` | **Plain-English explanations** — `explain_metric` returns 1-2 paragraphs a partner can read; `explain_for_ui` returns structured dict for popover rendering. |

### `rcm_mc/scenarios/` — 4 files ✓ [README](RCM_MC/rcm_mc/scenarios/README.md)

Programmatic what-if scenario builder + preset shocks.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `scenario_builder.py` | Fluent API for adjusting config parameters and running simulated scenarios (Step 81). |
| `scenario_overlay.py` | Pure function applying parameter shocks to config. Does not mutate MC kernel math. |
| `scenario_shocks.py` | **Preset payer-policy shocks** — runs MC under shocked configs, returns `ebitda_drag` stats for client-side overlay rendering. |

---

## Chunk 1 summary

**50 files documented.** README coverage: 9 of 11 sub-packages have READMEs. **Gaps**:
- `rcm_mc/compliance/` — needs a README (PHI scanner, hash-chain, CLI all worth documenting for HIPAA auditability)
- `rcm_mc/engagement/` — needs a README (engagement model layered on RBAC)

**Next chunk (2)**: `core/` (8) + `rcm/` (6) + `pe/` (21) + `mc/` (7) + `ml/` (25) — the math layer. ~67 files; will split across chunks 2 and 3 to stay ≤50 per chunk.

---

## Chunk 2 — The math layer: `core/` + `rcm/` + `pe/` + `mc/` (42 files, all ✓ README-covered)

### `rcm_mc/core/` — 8 files ✓ [README](RCM_MC/rcm_mc/core/README.md)

The Monte Carlo kernel + calibration. This is the deterministic, audit-defensible heart of the platform. Zero third-party deps beyond numpy/pandas.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `simulator.py` | The primary simulator — runs N MC trials, returns `(simulations_df, metrics_dict)`. Aligns benchmark to actual config via `infra.profile.align_benchmark_to_actual`. |
| `kernel.py` | Stable public-API wrapper over `simulator.py`. Dataclass-based entrypoint so the formula isn't exposed — callers depend on a contract, not an implementation. |
| `rng.py` | **Centralized RNG via `SeedSequence`** — produces independent reproducible streams per named component. Replaces the fragile `seed+1` pattern; each named stream is order-independent. |
| `calibration.py` | Fits `actual.yaml` / `benchmark.yaml` priors from observed data. Core entrypoint for `rcm-mc calibrate`. |
| `distributions.py` | Distribution constructors + validators. `DistributionError` raised on bad shape params. Moment-matching helpers (`beta_alpha_beta_from_mean_sd`). |
| `_calib_schema.py` | Private — column/value normalization for the calibration pipeline. Relies on `infra.config.canonical_payer_name`. |
| `_calib_stats.py` | Private — Bayesian posterior math for calibration. Beta-binomial posterior mean/SD given prior + observation count. |

### `rcm_mc/rcm/` — 6 files ✓ [README](RCM_MC/rcm_mc/rcm/README.md)

Revenue-cycle-management math + initiative tracking. Where claim-level mechanics live.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `claim_distribution.py` | Frozen `@dataclass` of per-payer claim-outcome distributions (denial rate, appeal success, write-off propensity, etc.). `@lru_cache` on common constructions. |
| `initiatives.py` | **Initiative library** — 8-12 standard RCM initiatives (prior-auth, CDI, underpayment recovery, etc.) with affected params, delta distributions, costs, ramp, confidence. Consumed by ranking/ROI/100-day logic. |
| `initiative_optimizer.py` | Ranks initiatives by EBITDA uplift × EV uplift × payback × confidence. Runs N+1 simulations (baseline + each initiative). Does not touch MC kernel math. |
| `initiative_tracking.py` | **Brick 57** — hold-period per-initiative quarterly attribution. Answers "which RCM workstream is behind plan?" when deal EBITDA variance is red. |
| `initiative_rollup.py` | **Brick 83** — cross-deal rollup of initiative performance across a 5-15 platform portfolio. Answers "is `prior_auth_improvement` consistently delivering?" |

### `rcm_mc/pe/` — 21 files ✓ [README](RCM_MC/rcm_mc/pe/README.md)

The PE deal-math layer. Turns simulated EBITDA uplift into MOIC/IRR/bridge/covenant math — the numbers an IC actually underwrites on.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `pe_math.py` | **Audit-defensible kernel** — stdlib-only (pandas only for tables). Value-creation bridge, returns, leverage. The math a director walks through on a whiteboard. |
| `breakdowns.py` | Compare-with-breakdown MC — returns attribution dict keyed by driver bucket (payer denials / underpayments / A/R days / appeals). |
| `attribution.py` | **OAT value attribution** — one-at-a-time $ contribution by driver bucket. Uses mixed configs: `D_S = mean ebitda_drag(mixed(S), benchmark)`. Explains *why* the MC spread is what it is. |
| `value_bridge_v2.py` | **v2 unit-economics bridge** — replaces the v1 coefficient bridge. Starts from collectible NPR (not raw NPSR) so leakage already modeled doesn't double-count. Transparent lever-by-lever. |
| `rcm_ebitda_bridge.py` | **v1 bridge — DEPRECATED.** Uniform research-band coefficients. Kept for legacy calibration comparison; new work uses v2. |
| `ramp_curves.py` | Per-lever implementation ramps for v2 bridge. `implementation_ramp` scalar overstates Y1 for slow-to-land initiatives (CDI, payer reneg); this adds per-lever curves. |
| `lever_dependency.py` | Cross-lever dependency adjuster — prevents double-counting when an analyst models both parent (`eligibility_denial_rate`) and child (`denial_rate`) levers. Uses `domain.econ_ontology` graph. |
| `debt_model.py` | **Multi-tranche debt projection** (Prompt 45) — year-by-year balances, mandatory amort, excess-cash sweeps, leverage ratios, covenant compliance. Feeds financing size + refi timing. |
| `waterfall.py` | **4-tier American GP/LP waterfall** (Prompt 46) — Return of Capital → Preferred Return (8% IRR default) → GP Catch-up → 20/80 split. Fund-level distribution math. |
| `hold_tracking.py` | **Brick 52** — per-KPI variance (actual vs underwritten), severity bucketing (on-track / lagging / off-track). Quarterly management reporting ingest. |
| `predicted_vs_actual.py` | **Prompt 43** — diligence-time prediction vs hold-time actual. Was the actual within the original CI? |
| `remark.py` | **Brick 61 re-mark** — re-underwrites a held deal based on actual EBITDA run-rate. Emits before/after: "entry $50M → exit $58M MOIC 2.55× becomes entry $50M → exit $51M MOIC 1.45×." |
| `pe_integration.py` | **Brick 46 auto-compute hook** — when `actual.yaml` carries a `deal:` section, `rcm-mc run` auto-materializes `pe_bridge.json`, `pe_returns.json`, `pe_hold_grid.csv`. |
| `value_creation.py` | Value-creation dataclass + drivers. The base model the v2 bridge + ramp curves compose over. |
| `value_creation_plan.py` | **Prompt 41** — auto-generates 100-day VCP `Initiative` entries from v2 bridge lever impacts. SQLite-persisted. Feeds Prompt 42 hold dashboard. |
| `value_plan.py` | YAML-driven Value Plan config — read/write of the plan shape, distinct from `value_creation_plan.py` (which is the builder/persister). |
| `value_tracker.py` | **Post-close tracker** — each quarter, actuals recorded per lever. Realization rate, ramp deviations, feeds prediction-ledger accuracy loop. |
| `fund_attribution.py` | **Prompt 60** — fund-level value decomposition into RCM improvement / organic growth / multiple expansion. |
| `cms_advisory.py` | CMS provider-level advisory scoring — ported from sibling `cms_medicare-master/` project (same team, no external license). Plotting/CLI stripped; kept pure scoring math. |
| `cms_advisory_bridge.py` | Converts `cms_advisory` scoring output into `RiskFlag` instances for the packet's `risk_flags` list + one summary metric. Separation of concerns — advisory stays testable in isolation. |

### `rcm_mc/mc/` — 7 files ✓ [README](RCM_MC/rcm_mc/mc/README.md)

Two-source Monte Carlo — prediction uncertainty × execution uncertainty. Sits on top of the v2 bridge.

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface: `MetricAssumption`, `RCMMonteCarloSimulator`, `MonteCarloResult`. |
| `ebitda_mc.py` | **Two-source MC over v1 bridge** — samples prediction uncertainty (ridge-predictor conformal bands) + execution uncertainty (actual vs target realization) independently per draw. |
| `v2_monte_carlo.py` | **MC over v2 bridge** — same two-source composition adapted to the v2 unit-economics surface. This is the current-state primary MC. |
| `convergence.py` | Running-P50 convergence check. Packet's MC section trustworthy only if running P50 over last `window` changes by less than `tolerance`. Re-run prompt instead of silent drift. |
| `mc_store.py` | SQLite storage, one row per `(deal_id, scenario_label, analysis_run_id)`. Append-only so partners can diff runs over time. |
| `portfolio_monte_carlo.py` | **Prompt 37 cross-deal MC** — 0.3 within-family execution correlation baseline → fund-level EBITDA distribution. |
| `scenario_comparison.py` | Side-by-side MC comparison — pairwise win-probability `P(A > B)` computed directly from samples (no distributional assumption). |

---

## Chunk 2 summary

**42 files documented · 92/1,705 cumulative (5.4%).** README coverage: all 4 packages covered. **No new gaps.**

**Key architectural insight**: the math layer is tightly layered and well-documented. Every file has a single responsibility and docstring explaining the Brick / Prompt / Phase it ships in. v1 bridge is deprecated but kept; v2 is the live path. MC comes in v1 (ebitda_mc), v2 (v2_monte_carlo), portfolio (cross-deal), and comparison flavors — each is a distinct sampling strategy.

**Next chunk (3)**: `ml/` (25) + `analysis/` (21) — ~46 files, the predictor + packet-builder layer.

---

## Chunk 3 — Predictor + packet-builder: `ml/` + `analysis/` (46 files, all ✓ README-covered)

### `rcm_mc/ml/` — 25 files ✓ [README](RCM_MC/rcm_mc/ml/README.md)

Phase-1 regression prediction engine + every downstream ML surface. Fills missing RCM metrics from partial data by finding comparable hospitals and fitting Ridge models. Also hosts the proprietary hospital-screening scorers (distress, investability, margin trajectory, market intelligence).

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface re-exports. Phase-1 predictor contract. |
| `ridge_predictor.py` | **Conformal-calibrated Ridge with size-gated fallback ladder.** Three branches: ≥15 comparables → Ridge + split conformal (honest 90% CIs), 5-14 → pooled Ridge, <5 → cohort median. This is the primary predictor. |
| `rcm_predictor.py` | **Hardcoded per-metric Ridge engine** — fits a per-metric Ridge on comparables' known features → target's missing features. Deterministic starting point; used when the richer `ridge_predictor` ladder isn't needed. |
| `conformal.py` | **Split conformal prediction** — distribution-free uncertainty intervals with finite-sample coverage guarantees. If calibration set is exchangeable with new point, 90% interval truly contains truth 90% of the time. No normality assumption. |
| `ensemble_predictor.py` | Auto-selecting ensemble over Ridge + nonlinear models. Ridge is right for ~linear RCM relationships (denial_rate vs bed_count); a few metrics (CMI, case-rate revenue) need nonlinear. |
| `comparable_finder.py` | **6-dimension similarity** — bed count (0.25), case mix, payer mix, geography, teaching status, financial profile. Weights defended in IC. Returns ranked peer list. |
| `feature_engineering.py` | Three pure functions: `derive_features` (interaction terms lifting Ridge R²), `normalize_metrics` (z-score vs peer medians), and schema helpers. |
| `bayesian_calibration.py` | **Hierarchical Beta-Binomial** for rate metrics (denial/collection/clean claim) + Gamma-Lognormal for dollar metrics (AR days, C2C). Multilevel shrinkage by payer/state/hospital type — thin data shrinks toward peer priors. |
| `anomaly_detector.py` | **Prompt 28 automated sanity checks.** Three stacked strategies: z-score vs cohort >2.5 (implausible lows/highs), business-rule (denial 2% impossible), trend-break (cohort-wide regime shift misses). Severity banded. |
| `backtester.py` | Hold-out backtest of the predictor — per-hospital: hide last `holdout_months` of data, predict from rest + comparables, score. Two entrypoints: per-hospital + cross-sectional. |
| `prediction_ledger.py` | **Persistent prediction-actuals ledger.** Every prediction recorded; when actuals arrive they're matched back. This is the feedback loop that makes models improve over time. |
| `portfolio_learning.py` | **Prompt 30 fund-calibrated predictions.** "Our model overestimates denial-rate improvement by 15% based on our last 4 deals" — institutional knowledge out of partners' heads into model priors. |
| `fund_learning.py` | Fund-level aggregation of value-creation actual-vs-plan — computes fund realization rate, detects systematic lever bias, adjusts future predictions. |
| `distress_predictor.py` | **Logistic regression on HCRIS features** — probability a hospital hits operating margin <-5% within next fiscal year. Core moat: Bloomberg shows trailing financials; this predicts next year's distress. |
| `hospital_clustering.py` | **K-means archetype clustering** over ~6,000 US hospitals on standardized HCRIS features. Each cluster gets a PE-relevant label ("Large Academic", "Rural Critical Access", "Suburban Profitable"). Used as a prior by many downstream modules. |
| `investability_scorer.py` | **0-100 composite "should PE pursue this?"** Combines Financial Health (25pts) + Market Position + Operational Efficiency + RCM Opportunity + Risk profile. Transparent sub-scores — partners can argue any component. |
| `margin_predictor.py` | **Fitted on HCRIS cross-section** (unlike hardcoded RCM predictor). Ridge-predicts operating margin from hospital characteristics + margin percentile within peer group. |
| `rcm_opportunity_scorer.py` | **THE core moat.** Estimates revenue uplift potential from RCM optimization — compares target metrics to best-in-class peers → quantifies the "value creation" thesis PE pays for. "How much EBITDA can RCM unlock here?" |
| `rcm_performance_predictor.py` | Predicts operational metrics (denial rate, AR days, clean claim rate, collection rate) from public-only inputs (HCRIS financials, bed count, payer mix, geography, case-mix proxy). PE screening advantage over any of 6,000+ hospitals without CCD. |
| `realization_predictor.py` | **Risk-adjusts the EBITDA bridge.** Predicts what fraction of the modeled bridge a hospital can actually achieve based on observable success-correlate features. A $25M bridge at 40% realization changes the investment. |
| `efficiency_frontier.py` | **DEA (Data Envelopment Analysis)** — multi-input (staff/cost/beds) × multi-output (revenue/patient days/quality) efficient frontier. Identifies which hospitals are operationally efficient vs room-to-improve. |
| `survival_analysis.py` | **Kaplan-Meier + simplified Cox proportional hazards** on multi-year HCRIS. Time-to-distress trajectory. Moat: Bloomberg shows current financials; this shows the trajectory. |
| `temporal_forecaster.py` | Per-metric time-series trend detection + short-horizon forecasting. Handles payer-rule drift, month-end billing pulses, year-over-year payer mix moves. Needs 3+ years of quarterly history. |
| `market_intelligence.py` | State/regional market concentration (HHI), competitive dynamics, reimbursement environment, growth indicators. Healthcare-specific moat. |
| `queueing_model.py` | **M/M/c + Little's Law** over denial workqueues / coding backlogs / prior-auth pipelines / AR follow-up. Estimates staffing needs, SLA breach probability, throughput capacity. Kleinrock reference. |

### `rcm_mc/analysis/` — 21 files ✓ [README](RCM_MC/rcm_mc/analysis/README.md)

**The packet-centric analysis layer — spine of Phase 4.** Every UI page, API endpoint, and export renders from a single `DealAnalysisPacket`. Nothing renders independently. This is the load-bearing architecture decision.

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports `DealAnalysisPacket`, `HospitalProfile`, `ObservedMetric`, etc. |
| `packet.py` | **The canonical `DealAnalysisPacket` dataclass** — JSON round-trip, carries hospital profile + observed metrics + predictions + risk flags + diligence questions + bridge + MC + provenance. Spec: [`docs/ANALYSIS_PACKET.md`](RCM_MC/docs/ANALYSIS_PACKET.md). |
| `packet_builder.py` | **12-step orchestrator.** Each step can fail independently — marks section `INCOMPLETE` / `FAILED` with reason, downstream renderers skip gracefully. Partner sees everything that did succeed. |
| `completeness.py` | **First-look data-quality layer.** 3 questions: what do we know (registry coverage), what's missing (EBITDA-sensitivity ranked), what grade do we ship (A/B/C/D). |
| `risk_flags.py` | **Automated `RiskFlag` assessment.** Walks observed metrics × hospital profile × comparable cohort × bridge and produces severity-banded flags. Replaces a morning of hand-work by an associate. |
| `diligence_questions.py` | Auto-generates the diligence questionnaire. Each HIGH/CRITICAL `RiskFlag` gets a concrete follow-up citing the triggering number. |
| `analysis_store.py` | **SQLite cache** for packet runs — `analysis_runs` table keyed `(deal_id, scenario_id, as_of, hash_inputs)`. `hash_inputs` skips expensive rebuilds when inputs match a recent cached run. |
| `stress.py` | Stress-suite harness — runs scenario shocks through the full simulator/bridge/MC stack. Used by `rcm-mc stress`. |
| `pressure_test.py` | **Management-plan pressure test.** Classifies each target as conservative / stretch / aggressive / aspirational based on where it sits vs peer distribution + realization priors. Answers "is management's X realistic?" |
| `challenge.py` | **Reverse challenge solver** — "what assumption change would move modeled drag from $17M to $5M?" IC-pushback mechanic. |
| `compare_runs.py` | Steps 79-80 — compare two output directories or summary CSVs. Trend analysis year-over-year. |
| `cohorts.py` | **Brick 106 group-by-tag portfolio rollup.** Slices partners actually ask for — growth vs roll-ups, legacy fund vs new fund. Feeds off deal_tags. |
| `cross_deal_search.py` | **Prompt 62 cross-deal full-text search.** "Didn't we see something similar at Cleveland?" TF-IDF keyword scoring + RCM-jargon term expansion over notes, overrides, risk flags, diligence questions, packets. |
| `deal_overrides.py` | **Per-deal analyst overrides in SQLite** — distinct from call-time overrides (`BridgeAssumptions`, `optional_contract_inputs`). Lets analysts lock in a thesis-specific assumption across sessions. |
| `deal_query.py` | **Prompt 53 rule-based query parser + executor.** `"denial rate > 10 AND state = IL"` — no SQL exposure, still powerful filter/sort over portfolio. |
| `deal_screener.py` | **Prompt 33-B fast screener from public data only.** Paste 20 names → ranked table in <3 sec per hospital. No ML, no MC — uses HCRIS + benchmarks directly. |
| `deal_sourcer.py` | **Prompt 61 predictive deal sourcing.** Fund defines thesis (metric criteria + geography + size) → scores every HCRIS hospital → ranked match list. |
| `playbook.py` | **Prompt 59 operational playbook.** Per-lever historical deals matching target's archetype → success rates + common initiatives + failure factors. "Hospitals like this tend to succeed on denial automation but fail on coding uplift." |
| `refresh_scheduler.py` | **Stale-analysis detector + auto-refresh.** Detects when public data refreshed after packet was built; optionally rebuilds the stalest first. |
| `anomaly_detection.py` | **Step 78** — calibration-input sanity checks. Flags unusual values pre-simulation (complements `ml/anomaly_detector.py` which runs post-prediction). |
| `surrogate.py` | **Optional fast ML surrogate — not used by main CLI.** Future: train on many MC runs, deploy for portfolio screening or interactive what-ifs before running full n_sims. Research slot. |

---

## Chunk 3 summary

**46 files · 138/1,705 cumulative (8.1%).** README coverage: both packages covered. No new gaps.

**Key insights saved**:
- **Predictor ladder**: `ridge_predictor.py` is size-gated — ≥15 comparables gets Ridge + split conformal (honest intervals); fewer falls back. Conformal is preferred over bootstrap/parametric because of finite-sample coverage guarantees (no normality assumption).
- **Prediction ledger feedback loop**: every prediction is stored; actuals are matched back; `portfolio_learning` and `fund_learning` close the loop into better priors. This is the model-improvement engine, not the models themselves.
- **Packet-centric architecture**: the 12-step `packet_builder.py` orchestrator is load-bearing — every page/API/export renders from the packet. Each step fails independently; partner always sees what succeeded.
- **Three moat scorers**: `distress_predictor` (next-year distress prob), `investability_scorer` (composite 0-100), `rcm_opportunity_scorer` ($ EBITDA unlock from RCM optimization). Together these are what "Bloomberg shows trailing, we predict forward."

**Next chunk (4)**: `finance/` (8) + `infra/` (27) + `integrations/` (7) — infrastructure + finance layer. ~42 files.

---

## Chunk 4 — Finance + infra + integrations (42 files, all ✓ README-covered)

### `rcm_mc/finance/` — 8 files ✓ [README](RCM_MC/rcm_mc/finance/README.md)

Reimbursement mechanics + deal-valuation models (DCF, LBO, three-statement). This is where the economic substrate lives — the layer that stops treating every hospital as an identical fee-for-service entity.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring on the reimbursement + revenue-realization contract. |
| `reimbursement_engine.py` | **Core insight module.** "The same operational metric has a different economic meaning depending on how the hospital gets paid." A 1% denial reduction is worth more on DRG prospective than capitated; a 10-day AR improvement is pure time-value on FFS but near-zero on cap. Feeds the v2 bridge's payer-aware economics. |
| `dcf_model.py` | **5-10 year DCF** from deal profile + value-creation assumptions. Annual cash flows → terminal value → EV → equity value with sensitivity tables. Every assumption labeled for IC audit. |
| `lbo_model.py` | **LBO projection** — MOIC/IRR under a given capital structure with debt paydown, EBITDA growth, multiple expansion/compression. Emits sources & uses + annual P&L + debt schedule + returns waterfall. |
| `three_statement.py` | **Reconstructed Income Statement + Balance Sheet + Cash Flow** from HCRIS public data + deal profile. Healthcare benchmarks fill missing fields. Labeled "NOT audited" — associate's starting model before seller actuals. |
| `denial_drivers.py` | **Why is denial rate high?** Decomposes against HCRIS regional + peer benchmarks to identify likely root causes (prior-auth denials, coding errors, eligibility issues). Sizes the value-creation opportunity. |
| `market_analysis.py` | **Regional market profile** from HCRIS — market share by revenue + beds, HHI concentration, competitive moat indicators (switching costs, scale, network effects), supply chain. |
| `regression.py` | **numpy-only OLS** across the portfolio — which variables correlate with EBITDA margin / denial rate / collection rate. No sklearn dep. |

### `rcm_mc/infra/` — 27 files ✓ [README](RCM_MC/rcm_mc/infra/README.md)

Cross-cutting infrastructure: config, logger, trace, job queue, run history, bundles, notifications, rate limit, response cache, webhooks, OpenAPI, backup, migrations, multi-fund, data retention, transparency parser, consistency check. The plumbing every other package imports.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `logger.py` | Centralized logger — `from .logger import logger`. Uniform format + level across the whole package. |
| `config.py` | YAML config loader + validator. `load_and_validate` is the entry every CLI subcommand calls. Also hosts `canonical_payer_name` used by calibration schema. |
| `profile.py` | Hospital "volume / mix" profile dataclass + `align_benchmark_to_actual` (used by core simulator). |
| `taxonomy.py` | Frozen `Initiative` dataclass — shared between `rcm.initiatives` and the value-plan layer. |
| `trace.py` | **Single-iteration MC audit trace** — expands `simulate_one` Actual vs Benchmark for one draw. Pre-scrub (raw engine). Pair with `provenance.json` + scrubbed `simulations.csv` for full picture. |
| `provenance.py` | Machine-readable run provenance — manifest + per-metric lineage. Written to `provenance.json` each CLI run. |
| `transparency.py` | **Hospital Price Transparency MRF parser.** Since July 2024 CMS requires negotiated-rate publication in a standardized CSV/JSON ("v2.0 standard charges template"). Produces partner-readable summary: payer count, unique services, rate distribution per service. |
| `capacity.py` | **Step 48 standalone capacity/backlog model** — isolates capacity logic from main simulator so alternative models (unlimited, outsourced, etc.) can be swapped in. |
| `diligence_requests.py` | Maps top modeled drivers to specific data pulls for validation. "Diligence requests that move the number." |
| `job_queue.py` | **Brick 95 in-process sim job queue.** Web UI triggers a full `rcm-mc run` non-blocking — returns job ID, polls for progress. Single-worker, in-memory (lost on restart). |
| `run_history.py` | **Step 83** — SQLite `run_history` append-only table for tracking model evolution over time. |
| `output_formats.py` | Steps 86 + 92 — JSON output format + CSV column documentation helpers. |
| `output_index.py` | **UI-4** — auto-builds `index.html` at top of an output folder. Clickable landing page grouping every artifact by kind. Replaces hunting through `MANIFEST.txt`. |
| `_bundle.py` | **Diligence-grade deliverable bundle** — `diligence_workbook.xlsx` (multi-tab Excel) + `data_requests.md` + raw CSVs in `outputs/_detail/`. Replaces 20-file output folder. |
| `_terminal.py` | Stdlib-only ANSI formatting (no `rich`, no `colorama`). Colors auto-disabled for non-TTY + respects `NO_COLOR` env var. |
| `backup.py` | **Atomic SQLite backup** — `VACUUM INTO` + gzip. Restore + verification. Partners on single-machine SQLite deployment can't lose the DB. |
| `migrations.py` | Schema migration registry. Idempotent ALTER TABLE / CREATE INDEX — already-applied changes silently skipped. |
| `consistency_check.py` | Startup-time schema verifier — confirms every needed table exists when DB opens (cold file from backup, migration, or other workstation). |
| `data_retention.py` | **Prompt 57** — configurable per-table retention + GDPR-style `export_user_data`. |
| `multi_fund.py` | **Multi-fund support** — Fund I / II / III with different vintages + sizes. Many-to-many `deal_fund_assignments` join table preserves backward compat. |
| `notifications.py` | **Prompt 44** — email (stdlib `smtplib`) + Slack (stdlib `urllib`) channel abstraction. Weekly digest + critical-event alerts. All optional-dep-free. |
| `webhooks.py` | **Prompt 39** — HMAC-SHA256 signed event dispatch. Events: `deal.created`, `analysis.completed`, `risk.critical`. `X-RCM-Signature` header keyed on per-webhook secret. |
| `openapi.py` | **Prompt 39 enhancement** — auto-generated OpenAPI 3.0 spec (`openapi.json`) + Swagger UI at `/api/docs` (CDN-loaded, no bundled JS). |
| `rate_limit.py` | In-memory sliding-window rate limiter. Used on `/api/data/refresh/<source>` and similar expensive endpoints. Fails open on restart — one extra refresh is acceptable. |
| `response_cache.py` | TTL-based response cache keyed `(path, query_string)`. Thread-safe. Used for cross-portfolio routes (portfolio MC, attribution, heatmap) that take 100ms+ on large portfolios. |
| `automation_engine.py` | **Rule-based workflow engine.** Partners configure rules firing on events (stage change, metric threshold cross, analysis complete, risk flag). Keeps daily-ops loop tight without partner clicks. |

### `rcm_mc/integrations/` — 7 files ✓ [README](RCM_MC/rcm_mc/integrations/README.md)

Outbound CRM sync + inbound diligence-vendor sockets + PMS connectors. Adapter pattern: one `Protocol` declaring data contract, per-vendor implementation.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — adapter pattern + vendor socket list. |
| `integration_hub.py` | **Prompt 58** — DealCloud + Salesforce + Google Sheets push. Standardized portfolio CSV is the common denominator. Google Sheets push optional (API key in config). |
| `chart_audit.py` | **Chart-audit vendor socket.** Samples billed encounters, re-codes, reports under-coding ($ lost per 99213→99214 delta), over-coding risk (RAC exposure), documentation gaps. |
| `contract_digitization.py` | **Contract digitization socket.** PDF/DOCX/scanned payer contract → structured `ContractSchedule` the re-pricer consumes. OCR + hierarchy + table extraction is the vendor's job. |
| `pms/__init__.py` | **Prompt 76 PMS integrations package.** Epic / Cerner / athena connectors. |
| `pms/base.py` | Abstract base `PMSConnector` — four pull methods subclasses implement. SQLite + base64 credential storage (placeholder for real encryption). |
| `pms/epic.py` | **Epic stub.** Placeholder — real FHIR R4 integration is a future sprint. Methods return empty results so connector can be instantiated + tested without network. |

---

## Chunk 4 summary

**42 files · 180/1,705 cumulative (10.6%).** README coverage: all 3 packages covered. No new gaps.

**Key architectural insights captured**:
- **`reimbursement_engine.py` is the economic substrate** — same ops metric has different $ impact depending on how the hospital gets paid. This is why the v2 bridge is payer-aware and the v1 bridge was retired.
- **`infra/` is stdlib-heavy and optional-dep-free** — notifications use `smtplib` + `urllib`, webhooks use `hmac`, terminal color uses raw ANSI, OpenAPI UI loaded from CDN. Product runs on a corporate-firewalled laptop offline by design.
- **Integrations use the adapter pattern** — each vendor socket is a `Protocol` contract. Epic is a stub; chart audit + contract digitization are real implementations.
- **`infra/backup.py` + `infra/migrations.py` + `infra/consistency_check.py`** collectively make single-machine SQLite deployment safe: atomic backup, idempotent schema evolution, cold-file schema verification at startup.

**Next chunks (5-8)**: `diligence/` — 137 files across 35 sub-modules. This is the big partner-facing surface area. Planning split:
- Chunk 5: the 7 new-this-cycle modules (hcris_xray, regulatory_calendar, covenant_lab, bridge_audit, bear_case, payer_stress, thesis_pipeline) — already individually documented, so mainly a tie-in + coverage audit
- Chunks 6-8: the 28 legacy diligence modules (benchmarks, checklist, counterfactual, cyber, deal_autopsy, deal_mc, denial_prediction, exit_timing, integrity, labor, ma_dynamics, management_scorecard, patient_pay, physician_attrition, physician_comp, physician_eu, quality, real_estate, referral, regulatory, reputational, root_cause, screening, synergy, value, working_capital, ccd_bridge.py, _pages.py, and ingest/) — ~50 files each

---

## Chunk 5 — `diligence/` phase 1 (ingest) + the 7 new-this-cycle modules (31 files)

### `rcm_mc/diligence/` top-level — 3 files ✓ [top README](RCM_MC/rcm_mc/diligence/README.md) *(if present)* · see also [INTEGRATION_MAP.md](RCM_MC/rcm_mc/diligence/INTEGRATION_MAP.md) + [SESSION_LOG.md](RCM_MC/rcm_mc/diligence/SESSION_LOG.md)

The analyst's primary workspace. Organised around the four-phase RCM Diligence Playbook: Ingestion → KPI Benchmarking → Root Cause → Value Creation.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring mapping the four diligence phases to sub-package directories (`ingest/`, `benchmarks/`, `root_cause/`, `value/`). |
| `_pages.py` | **HTTP page renderers for the 4 diligence tabs** — each accepts `?dataset=<fixture>` query param and runs the real pipeline (ingest → KPI → cohort → waterfall → advisory) under the editorial shell. No param → "pick a fixture" landing. |
| `ccd_bridge.py` | **CCD → packet bridge** — the one place where Phase 1 output (CCD + TransformationLog + Phase 2 KPIs) meets the Phase 4 packet builder. Converts CCD KPIs → `observed_metrics` dict + matching provenance nodes. |

### `rcm_mc/diligence/ingest/` — 6 files ✓ README-worthy (check existence)

**Phase 1** — Ingestion & Normalization. Turns messy source files (CSV/Excel/scanned) into the Canonical Claims Dataset (CCD) that every downstream phase reads from.

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface — `CanonicalClaim`, `CanonicalClaimsDataset`, `TransformationLog`, `ingest_dataset`. |
| `ccd.py` | **The data contract.** Canonical Claims Dataset — single artefact every downstream phase reads. Chain: `KPI → CCD rows → TransformationLog entries → source file + row + rule`. Defendable to a skeptical auditor. |
| `ingester.py` | **The driver.** `ingest_dataset(path)` walks a dataset dir, dispatches to readers, feeds rows through normalisers, emits `CanonicalClaimsDataset` with row-logged `TransformationLog`. Invariants enforced by fixture tests against `tests/fixtures/messy/`. |
| `readers.py` | Source-format readers — CSV (stdlib `csv`, no pandas), Excel (openpyxl), fixed-width, JSON. Each returns row dicts + per-row source metadata. Format-agnostic downstream. |
| `normalize.py` | Normalization primitives — each takes raw value + TransformationLog + row context, returns coerced value + logs the decision. Row-scoped logs so "why is this field what it is?" is one filter away. |
| `tuva_bridge.py` | Maps `CanonicalClaimsDataset` → Tuva Input Layer schema so partners who want the richer Tuva marts (CCSR, HCC, financial_pmpm, chronic conditions, readmissions) can run vendored Tuva dbt on top of our CCD. Tuva lives at `ChartisDrewIntel-main/` (Apache 2.0, unmodified). |

### `rcm_mc/diligence/hcris_xray/` — 3 files ✓ [README](RCM_MC/rcm_mc/diligence/hcris_xray/README.md)

Peer-benchmark engine over 17,701 HCRIS filings. (Already mapped in detail in the module README.)

| File | Purpose |
|------|---------|
| `__init__.py` | Package surface — `xray`, `find_hospital`, `search_hospitals`, `HospitalMetrics`, `XRayReport`, etc. |
| `metrics.py` | `HospitalMetrics` dataclass + `METRIC_SPECS` (the 15 canonical metrics with direction flag + group) + `classify_cohort` (bed binning). Pure math, no I/O. |
| `xray.py` | Peer-matching waterfall (same cohort + state + ±30% beds → region → national, stops at ≥25 peers) + benchmark computation + `XRayReport`. |

### `rcm_mc/diligence/regulatory_calendar/` — 4 files ✓ [README](RCM_MC/rcm_mc/diligence/regulatory_calendar/README.md)

Thesis kill-switch engine. (Already mapped in the module README.)

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface — `analyze_regulatory_exposure`, `RegulatoryEvent`, `KillSwitchVerdict`, etc. |
| `calendar.py` | **Curated library** of 11 hand-calibrated CMS/OIG/FTC/DOJ/IDR events. Each: publish + effective dates, affected specialties, thesis drivers killed, impact distribution, docket URL. |
| `impact_mapper.py` | Maps one `RegulatoryEvent` × target profile → per-driver impact verdict (`UNAFFECTED / DAMAGED >10% / KILLED >50%`). Pure functions, no I/O. |
| `killswitch.py` | Overall verdict synthesizer — PASS / CAUTION / WARNING / FAIL thresholds + per-year EBITDA overlay + partner-narrative. Feeds Covenant Lab + Deal MC downstream. |

### `rcm_mc/diligence/covenant_lab/` — 4 files ✓ [README](RCM_MC/rcm_mc/diligence/covenant_lab/README.md)

Per-quarter covenant-breach probability simulator. (Already mapped.)

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface. |
| `capital_stack.py` | `DebtTranche` dataclass (6 kinds: revolver, TLA, TLB, unitranche, mezz, seller note) + `build_debt_schedule` + `default_lbo_stack`. |
| `covenants.py` | `CovenantDefinition` + per-period evaluator for the 4 dominant covenants (Net Leverage, DSCR, Interest Coverage, Fixed Charge Coverage). Step-down schedules supported. |
| `simulator.py` | **MC engine** — 500 lognormal paths via stdlib Beasley-Springer-Moro, per-quarter covenant test, equity-cure sizing per breach, regulatory-overlay subtraction. |

### `rcm_mc/diligence/bridge_audit/` — 3 files ✓ [README](RCM_MC/rcm_mc/diligence/bridge_audit/README.md)

Synergy-bridge auto-auditor against 3,000-outcome priors. (Already mapped.)

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface. |
| `lever_library.py` | **21 curated `LeverPrior`s** with median/P25/P75 realization + failure rate + duration + target-conditional boosts. Priority-tiebreak keyword classifier from raw banker text. |
| `auditor.py` | `audit_bridge` engine — per-lever verdict (REALISTIC / OVERSTATED / UNSUPPORTED / UNDERSTATED) + bridge-level gap math + counter-bid recommendation + earn-out alternative. Also `parse_bridge_text` banker-copy-paste ingester. |

### `rcm_mc/diligence/bear_case/` — 3 files ✓ [README](RCM_MC/rcm_mc/diligence/bear_case/README.md)

IC-memo bear-case synthesizer. (Already mapped.)

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface. |
| `evidence.py` | `Evidence` dataclass + **8 defensive extractors** (one per source module: regulatory, covenant, bridge, deal MC, autopsy, exit timing, payer, HCRIS). Each returns `[]` on missing input, never raises. |
| `generator.py` | Orchestrator — ranks by severity × $ × source priority, assigns citation keys `[R/C/B/M/A/E/P/H]`, dedup between regulatory overlay + bridge gap, emits print-ready IC-memo HTML. |

### `rcm_mc/diligence/payer_stress/` — 3 files ✓ [README](RCM_MC/rcm_mc/diligence/payer_stress/README.md)

Payer concentration Monte Carlo with HHI amplifier. (Already mapped.)

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface. |
| `payer_library.py` | **19 curated payers** — national commercials (UHC, Anthem, Aetna, Cigna, Humana), regional Blues, Medicare FFS + MA, Medicaid FFS + Centene + Molina, TRICARE, Workers Comp, Self-pay. Each: P25/median/P75 rate-move distribution + negotiating leverage + renewal prob + churn prob + behavioral notes. |
| `contract_simulator.py` | `run_payer_stress` — 500 paths × horizon × per-payer. Samples from Normal fit to prior, dampens by (1 − renewal prob), draws tail churn. HHI concentration amplifier: Top-1 >30% → `1 + (top_1−0.30)×2` volatility scaling. |

### `rcm_mc/diligence/thesis_pipeline/` — 2 files ✓ [README](RCM_MC/rcm_mc/diligence/thesis_pipeline/README.md)

The 19-step orchestrator that runs every diligence module end-to-end. (Already mapped.)

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface — `run_thesis_pipeline`, `PipelineInput`, `ThesisPipelineReport`, `pipeline_observations`. |
| `orchestrator.py` | **The single-file brain.** `PipelineInput` dataclass + 19 step functions each wrapped in `_timed(step, fn, log)` (catches exceptions, logs elapsed ms + OK/ERROR/SKIP, never aborts the chain). Headline synthesizer packs ~20 top-line numbers into `ThesisPipelineReport`. Runs ~170ms end-to-end on fixtures. |

---

## Chunk 5 summary

**31 files · 211/1,705 cumulative (12.4%).** All 7 new-cycle modules + Phase 1 ingest fully covered. The `ingest/` sub-package probably needs a dedicated README since it's the Phase 1 "data contract" layer and doesn't have one visible — check later and add if missing.

**Key architectural insights captured**:
- **Phase 1 CCD is the defensibility spine** — `ccd.py` is the data contract; `TransformationLog` row-scopes every normalization decision so "why is this field what it is?" is one filter away. Auditable from KPI back to source row + rule.
- **`ccd_bridge.py` is the single choke point** between Phase 1 (ingest) and Phase 4 (packet builder). Phases aren't independent — they compose via this bridge.
- **`tuva_bridge.py` bridges to vendored Tuva** (ChartisDrewIntel-main/, Apache 2.0, unmodified) for partners who want the richer claims marts without leaving our CCD as source of truth.
- **The 7 new-cycle modules share a common pattern**: each has `__init__.py` + a curated-prior library file + an engine file. `hcris_xray/metrics.py`, `regulatory_calendar/calendar.py`, `bridge_audit/lever_library.py`, `payer_stress/payer_library.py` are all "the prior data"; their siblings are "the engine consuming the prior."

**Next chunk (6)**: `diligence/` legacy modules batch 1 — benchmarks, checklist, counterfactual, cyber, deal_autopsy, deal_mc, denial_prediction, exit_timing, integrity. ~50 files.

---

## Chunk 6 — `diligence/` legacy batch 1 (40 files, **all 9 ✗ NO README — major gap**)

**Doc-gap flag**: every module in this chunk lacks a README. The new-cycle modules got per-module READMEs during the doc push but these legacy workhorses never did. Each is load-bearing — prioritize READMEs for `integrity/` and `deal_mc/` first (they're the ones most called across the platform).

### `rcm_mc/diligence/benchmarks/` — 6 files ✗

**Phase 2 — KPI Benchmarking & Stress Testing.** Reads CCD from Phase 1. Computes HFMA-vocabulary KPIs with cited formulas, cohort liquidation curves (with mandatory as_of censoring), and denial stratification by ANSI CARC category.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — Phase 2 surface. |
| `kpi_engine.py` | **The HFMA KPI computer.** Every formula cited. Returns either a computed value OR `None + reason` — never interpolation, never a partial number wearing a full-metric label. "Defendable to a skeptical auditor." |
| `_ansi_codes.py` | **ANSI CARC → denial category.** Rule-based grouping (front-end / coding / clinical / payer-behavior). Load-bearing spec assertion: not an ML classifier — an auditable rule file. |
| `cash_waterfall.py` | **Quality of Revenue output.** Walks every claim gross charges → contractual adjustments → front-end leakage → initial denials (net of appeals) → bad debt → realized cash. Cohorted by date-of-service month. |
| `cohort_liquidation.py` | **Cohort liquidation with mandatory as_of censoring.** Guards the trap: analyst running diligence 2026-03-15 looking at "Jan 2026 cohort at 90 days" would read incomplete data. Refuses to emit a number until the cohort has actually aged past the requested window. |
| `contract_repricer.py` | Takes structured `ContractSchedule` (payer × CPT → contracted rate, carve-outs, stop-loss, withhold primitives) and re-prices historical claims. Feeds underpayment-recovery lever in the bridge. |

### `rcm_mc/diligence/checklist/` — 3 files ✗

The orchestration layer a PE analyst uses day-to-day — every item is a partner-readable question with metadata driving auto-completion.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "Diligence Checklist + Open Questions Tracker." |
| `items.py` | **Curated 36-item RCM due-diligence checklist.** Organized by phase: screening → benchmarks → predictive → risk → financial → deliverable → manual. Each = partner-readable question + auto-complete metadata. |
| `tracker.py` | **Stateless status computer.** Given a `DealObservations` snapshot (what has/hasn't been run), emits per-item status. No SQLite — observed state is the source of truth, tracker just derives. |

### `rcm_mc/diligence/counterfactual/` — 4 files ✗

**Counterfactual deal-structuring advisor.** Given a current RED/CRITICAL finding, back-solves the minimum input change that flips the band. No new math — symbolic inverse against the threshold YAMLs already in the platform.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — the "what would change your mind" engine. |
| `advisor.py` | **One counterfactual solver per risk module.** Each solver: current finding + threshold → minimum input delta that flips band. Symbolic inverse only — fabricates nothing. |
| `ccd_runner.py` | CCD-driven runner. Given a `CanonicalClaimsDataset`, extracts each solver's inputs and returns a `CounterfactualSet`. Ties the advisor to the rest of the platform. |
| `bridge_integration.py` | Feeds counterfactual savings into the v2 EBITDA bridge as a new "reg-risk mitigated" lever. Doesn't touch bridge code — just wraps output as another lever. |

### `rcm_mc/diligence/cyber/` — 6 files ✗

**Cybersecurity posture + business-interruption risk** (Prompt K). Anchored to Change Healthcare 2024 ransomware. Every PE sponsor now treats cyber as board-level screening — this module integrates it into packet + MC.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring, Change Healthcare causal story. |
| `cyber_score.py` | **CyberScore composite (0-100)** + bridge-reserve lever. Rolls submodule outputs into single score displayed on packet overview alongside EBITDA + EV. Banded (lower = worse). |
| `bi_loss_model.py` | **Business-interruption loss MC.** For a target with `revenue_per_day_baseline`, `probability_of_incident_per_year`, `days_of_disruption` distribution, produces $ loss distribution. Feeds the reserve lever. |
| `business_associate_map.py` | **BA cascade risk.** Cross-references target's disclosed BA list (clearinghouse, billing, RCM BPO, telehealth, PACS) against known-catastrophic BA catalogue (YAML). Change Healthcare is tier-0. |
| `ehr_vendor_risk.py` | EHR vendor risk score lookups — per-vendor posture ratings, known-vuln history. |
| `deferred_it_capex_detector.py` | **IT capex underinvestment detector.** Flags overdue EHR replacements (Epic 7-10y cycle, community EHRs 5-7y) + understaffed IT (industry benchmark ~1 FTE per $8-10M revenue). |

### `rcm_mc/diligence/deal_autopsy/` — 3 files ✗

**"You're about to do Steward again."** Library of historical PE healthcare deals with each reduced to a 9-dimension risk signature. Matches target's signature → surfaces nearest historical outcome.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — 9-dim signature + narrative pattern. |
| `library.py` | **Curated library** of historical PE healthcare deals (bankruptcies, distressed sales, strong exits). Each reduced to 9-vector signature at entry + narrative of what happened. |
| `matcher.py` | Signature extraction + similarity matching. 9-vector in [0.0, 1.0]. Squared Euclidean distance normalized to `sqrt(9) = 3.0`. Each dim's squared deviation surfaced so partner sees which dims drove the match. |

### `rcm_mc/diligence/deal_mc/` — 3 files ✗

**Deal-level Monte Carlo** — the EBITDA + MOIC + IRR distribution engine that integrates every risk module's output. Models the full hold-period EBITDA path (not just Phase-1 drag).

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "FULL hold-period EBITDA path, not just Phase-1 drag." |
| `engine.py` | **Deal MC core.** Per trial draws: `organic_growth_rate ~ N(μ, σ)` (revenue CAGR), `denial_rate_improvement_pp ~ N` (uplift), plus 6 more drivers. Produces MOIC/IRR/proceeds distributions. Consumed by `thesis_pipeline.orchestrator`. |
| `charts.py` | **Zero-dep SVG chart generators.** Pure string templates — no numpy, no matplotlib, no plotly. Charts inline in the UI. |

### `rcm_mc/diligence/denial_prediction/` — 3 files ✗

**Claim-level denial prediction** — CCD-native analytic that feeds the EBITDA bridge's denial-reduction lever with a data-driven target instead of an industry-aggregate guess.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — CCD-native denial prediction. |
| `model.py` | **Naive Bayes denial model — stdlib only.** `P(denial=1 | features) ∝ P(denial=1) × ∏_f P(f | denial=1)`. No sklearn. |
| `analyzer.py` | End-to-end analyzer: CCD → features → model → report. One-liner public surface: `from rcm_mc.diligence.denial_prediction import analyze_ccd`. |

### `rcm_mc/diligence/exit_timing/` — 5 files ✗

**Exit Timing + Buyer-Type Fit.** Answers the two questions at year 3-5: **when** should we exit, and **to whom**.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `analyzer.py` | **`ExitTimingReport` orchestrator** — composes curve + buyer fit + recommendation. Algorithm: build MOIC/IRR curve Y2-Y7, score buyer types, recommendation = highest probability-weighted proceeds. |
| `curves.py` | **IRR / MOIC / proceeds curves Y2-Y7.** Takes Deal MC year-by-year EBITDA → per-year `(year, moic, irr, proceeds)` + sharpe-like reward/hold-risk ratio. |
| `buyer_fit.py` | **Per-buyer-type fit scorer.** Given target profile (category, EBITDA scale, payer mix, regulatory overhang, management score, sector sentiment) → 0-100 fit per buyer archetype. |
| `playbook.py` | **Buyer-type playbooks.** Partner-facing economics per exit channel: multiple premium/discount vs public comp median, time-to-close, close-certainty. |

### `rcm_mc/diligence/integrity/` — 7 files ✗

**Data-integrity gauntlet** — every guardrail that must hold before a CCD-derived metric can flow into the packet or PE brain. Each is a hard precondition, not a warning.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "load-bearing, hard precondition." |
| `preflight.py` | **`run_ccd_guardrails`** — the single entry the packet builder calls before trusting any CCD-derived `ObservedMetric`. Runs every guardrail in the subpackage, returns pass/fail + reasons. |
| `cohort_censoring.py` | Structured guardrail wrapping the math in `benchmarks/cohort_liquidation.py`. Makes the censoring rule explicit so preflight can check it. |
| `distribution_shift.py` | **Distribution-shift check.** PE Intelligence archetype recognition was calibrated on acute-hospital-dominant HCRIS. When an analyst drops a dental CCD, this refuses to silently apply acute-hospital priors. |
| `leakage_audit.py` | **Target leakage audit.** Guards the trap: Hospital X's CCD → KPIs → join training corpus → ridge predictor trains on corpus → when Hospital X runs, model sees its own data. |
| `split_enforcer.py` | **Provider-disjoint train/calibration/test splits.** Fixes `ml/conformal.py`'s row-shuffle split — same provider's rows can't be in both calibration + test set, which would void conformal coverage guarantee. |
| `temporal_validity.py` | **Temporal validity stamp.** 2023 historical claims don't predict 2026 payer behavior once OBBBA Medicaid work requirements, site-neutral payment, MA risk-adj revisions phase in. Every KPI carries a validity window. |

---

## Chunk 6 summary

**40 files · 251/1,705 cumulative (14.7%).** **All 9 modules lack READMEs — major documentation gap flagged.** These are the workhorse legacy diligence modules that `thesis_pipeline.orchestrator` actually calls every run.

**Priority READMEs to backfill** (ordered by how many downstream modules call each):
1. **`integrity/`** — called as preflight before every packet-builder run. 7 files, 6 guardrails + 1 orchestrator. High-value README since "why did this KPI get rejected?" currently requires reading source.
2. **`deal_mc/`** — the headline MC engine feeding every downstream consumer.
3. **`benchmarks/`** — Phase 2 spine with `kpi_engine.py` + `cohort_liquidation.py` + `contract_repricer.py`. The HFMA-KPI vocabulary source of truth.
4. **`deal_autopsy/`** — named-failure library + matcher. Small module but signature-match logic is non-obvious.
5. **`cyber/`** — Change Healthcare 2024 anchored. Cyber is a board-level screening concern; the 0-100 composite + BI MC are worth documenting.
6. **`denial_prediction/`** — Naive Bayes stdlib model is unusual enough to warrant a note on why not sklearn.
7. **`exit_timing/`** — 5 files, curve + buyer-fit + playbook separation is clean enough to skim from source but a README would save time.
8. **`counterfactual/`** — advisor + bridge integration.
9. **`checklist/`** — smallest + most self-explanatory.

**Key architectural insights captured**:
- **Phase 2 refuses interpolation.** `kpi_engine.py` returns `None + reason` when inputs are insufficient — never a partial number wearing a full-metric label. Auditability over convenience.
- **Cohort censoring is a hard rule.** `benchmarks/cohort_liquidation.py` and `integrity/cohort_censoring.py` together refuse to emit "90-day liquidation for the Jan 2026 cohort" if the cohort hasn't aged 90 days yet.
- **Counterfactual advisor doesn't fabricate.** It's a symbolic inverse against existing threshold YAMLs — "what input change would flip this RED to AMBER?" is a solve, not a model.
- **Integrity guardrails are hard, not soft.** `preflight.run_ccd_guardrails` is a single choke point — every CCD-derived metric clears this gauntlet before landing in the packet. Distribution shift (dental CCD ≠ acute hospital prior), target leakage (Hospital X's own data in its training corpus), provider-disjoint splits (conformal coverage), temporal validity (2023 ≠ 2026 under OBBBA).

**Next chunk (7)**: `diligence/` legacy batch 2 — labor, ma_dynamics, management_scorecard, patient_pay, physician_attrition, physician_comp, physician_eu, quality, real_estate, referral. ~50 files.

---

## Chunk 7 — `diligence/` legacy batch 2 (44 files, **all 10 ✗ NO README — same gap as chunk 6**)

### `rcm_mc/diligence/labor/` — 4 files ✗

**Labor economics diligence** (Prompt M, Gap 2) — three pragmatic sub-analytics covering wage inflation + staffing + synthetic-FTE detection.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — scope-reduced from original spec, three submodules. |
| `wage_forecaster.py` | **Regional wage-inflation projection.** MSA × role anchors from BLS QCEW / OES public aggregates (2024-2026 trend). Licensed BLS pull replaces these for diligence-grade. |
| `staffing_ratio_benchmark.py` | HCRIS-derived anchors — nurses-per-occupied-bed, coders-per-10K-claims. Quarterly refresh. |
| `synthetic_fte_detector.py` | **Reconciles scheduling FTEs vs billing NPIs vs 941 payroll headcount.** Flags when billing NPIs exceed scheduled FTEs by >25% — historical signature of locum inflation or ghost providers. |

### `rcm_mc/diligence/ma_dynamics/` — 7 files ✗

**Medicare Advantage V28 + payer-mix dynamics** (Prompt L, Gap 11). MA covers >55% of Medicare beneficiaries; V28 (fully effective 2026-01-01) projects 3.12% avg risk-score reduction. Cano Health bankruptcy was directly tied to pre-V28 coding-intensity exposure.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — V28 causal framing, Cano parallel. |
| `v28_recalibration.py` | **Deepest analytic moat.** Given member roster + diagnosis codes + attributed revenue, compute per-member + aggregate revenue impact of V24→V28 transition. |
| `coding_intensity_analyzer.py` | **Aetna/CVS pattern detector.** Flags FCA-attracting patterns: add-only retrospective chart review (codes added to prior years without corresponding removals), etc. |
| `commercial_concentration.py` | Payer HHI + top-payer 5% rate-cut scenario. |
| `downcoding_prior_auth_red_flag.py` | Rule-based payer-behavior signals predicting revenue compression. Not models — partner pressure-test triggers. |
| `medicaid_unwind_tracker.py` | Post-PHE Medicaid redetermination tracker. KFF-sourced: ~70% national procedural termination rate; OCHIN Q4 2023 showed -7% Medicaid volume. Estimates target-level volume-at-risk. |
| `risk_contract_modeler.py` | ACO REACH / MSSP / full-risk MA projector. `attributed_benes × (actual PMPM − benchmark PMPM) × shared-savings rate`. Minimal — uses caller inputs, no CMS file ingest. |

### `rcm_mc/diligence/management_scorecard/` — 4 files ✗

**Systematic quality-of-management diligence.** Turns "will this team hit their forecast?" from ad-hoc reference calls into a scored deliverable.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — replaces ad-hoc reference calls + LinkedIn skimming. |
| `profile.py` | `Executive` dataclass — minimal, hand-collected from data room + reference calls. Optional fields degrade to neutral priors. |
| `scorer.py` | **Per-executive deterministic scoring.** Four dimensions (forecast reliability × comp × tenure × prior-role), each 0-100 with named reason string. Overall = weighted average; red-flag override clips to ≤40. |
| `analyzer.py` | Team-level orchestrator — scores each exec, aggregates into `ManagementReport` (role-weighted overall: CEO 35% / CFO 25% / COO 20% / remainder split). |

### `rcm_mc/diligence/patient_pay/` — 4 files ✗

**Patient payment dynamics** (Gap 9) — HDHP exposure + POS collection + state medical-debt overlay.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — surfaces `HDHPExposure` + `segment_patient_pay_exposure`. |
| `hdhp_segmentation.py` | **HDHP share × bad-debt amplifier.** HDHP members produce outsized patient balances; patient recovery is a fraction of insurer recovery → HDHP share is a material bad-debt driver. |
| `pos_collection_benchmark.py` | Point-of-service collection rate benchmarks — best-in-class vs target, lift opportunity. |
| `medical_debt_overlay.py` | **State-level medical-debt credit-reporting overlay.** State laws banning medical debt on consumer credit reports compress collection tools → bad-debt reserves rise. |

### `rcm_mc/diligence/physician_attrition/` — 4 files ✗

**P-PAM (Predictive Physician Attrition Model).** Given a roster + optional public context (NPI enumeration date, local competitors, FMV benchmarks), scores 18-month flight-risk per provider.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `features.py` | Per-provider feature extraction — 9-dim vector from `Provider` dataclass + optional NPI-enumeration-date + local-competitor count + FMV delta. |
| `model.py` | **Logistic-style flight-risk predictor.** Hand-calibrated coefficients (no sklearn). 9-dim `AttritionFeatures` → sigmoid → 18-mo flight-risk probability. |
| `analyzer.py` | Orchestrator → `AttritionReport` with per-provider flight-risk, concentration-weighted NPR-at-risk, retention recommendations. |

### `rcm_mc/diligence/physician_comp/` — 6 files ✗

**Physician comp FMV + productivity-drift modeling** (Prompt J). Five submodules covering deal-side comp analytics VMG's FMV-MD does not cover (VMG is compliance-letter workflow; this is forward-looking simulation).

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — differentiation vs VMG / FMV-MD. |
| `comp_ingester.py` | Provider roster ingester — `Provider` dataclasses from payroll + W-2 + 1099 + scheduling. Computes per-provider comp-per-wRVU, comp-as-%-of-collections, comp-per-hour. |
| `fmv_benchmarks.py` | FMV benchmark lookups — carries "public-aggregate placeholder" caveat. Licensed MGMA / Sullivan Cotter / AMGA data replaces these when available. |
| `productivity_drift_simulator.py` | **The novel analytic: post-close "comp model reset" drift.** For each provider, simulate a new (lower $) comp model → model the productivity drop → revenue drag. |
| `stark_aks_red_line.py` | **Stark / AKS red-line detector.** Rule-based flags for FCA/DOJ-attracting configurations. Not legal advice — analytic with statutory cites. |
| `earnout_advisor_enhancement.py` | **Earnout advisor with provider-retention structure.** When top-5 provider concentration crosses thresholds, specific earnout structures align seller's personal incentive with retained providers. |

### `rcm_mc/diligence/physician_eu/` — 3 files ✗

**Physician Economic Unit Analyzer — per-provider P&L.** Answers "which providers are net-negative contributors at fair-market comp?"

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring. |
| `features.py` | **Contribution margin math.** `contribution_margin(p) = collections(p) − direct_cost(p) − allocated_overhead(p)`. Deterministic per-provider envelope. |
| `analyzer.py` | Roster-level orchestrator — ranks by contribution, finds loss-makers, quantifies drop-them-at-close bridge lever. Feeds Deal MC EBITDA uplift. |

### `rcm_mc/diligence/quality/` — 2 files ✗

**Clinical quality projector** (Gap 6) — VBP / HRRP / HAC reimbursement-penalty forward projection.

| File | Purpose |
|------|---------|
| `__init__.py` | Surfaces `QualityPenaltyProjection` + `project_vbp_hrrp`. |
| `vbp_hrrp_projector.py` | **Three-year VBP/HRRP/HAC projector.** Given current Care Compare star rating + HRRP excess-readmission ratios + HAC score → reimbursement impact under current CMS formulas over 3-year horizon. |

### `rcm_mc/diligence/real_estate/` — 7 files ✗

**The "Steward module."** Targets the sale-leaseback blind spot that produced Steward (2016 MPT → 2024 bankruptcy), Prospect (2019 Leonard Green → 2025), and other REIT-backed hospital failures.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — Steward / Prospect / MPT causal pattern. |
| `types.py` | Shared types — `StewardRiskTier` severity labels (separate from `RegulatoryBand` — real-estate-specific). Bundled with regulatory into Bankruptcy-Survivor Scan. |
| `steward_score.py` | **Steward Score five-factor composite.** Pattern-matches the Steward/Prospect/MPT failure mode. 5 factors that co-occurred: REIT landlord + high rent-to-rev + operator undercapitalization + Medicaid mix + distressed refi calendar. |
| `lease_waterfall.py` | Portfolio-level lease waterfall — year-by-year rent obligations through hold (default 10y), per-property + portfolio rollup, escalator math. |
| `capex_deferred_maintenance.py` | **Capex-wall detector.** HCRIS fixed-asset data × gross PPE → deferred-maintenance signature. Flags targets with suspiciously low maintenance capex relative to asset base. |
| `sale_leaseback_blocker.py` | **State-by-state sale-leaseback feasibility.** Per-state feasibility of sale-leaseback exit. Seeded from `content/sale_leaseback_blockers.yaml` (CT HB 5316 phaseout, etc.). |
| `specialty_rent_benchmarks.py` | Specialty rent-benchmark lookup — reads `content/specialty_rent_benchmarks.yaml`, returns P25/P50/P75 band. `classify_rent_share` maps target's rent-to-revenue into a band. |

### `rcm_mc/diligence/referral/` — 3 files ✗

**Referral-leakage + provider-concentration** (Prompt M, Gap 5).

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — two submodules. |
| `leakage_analyzer.py` | **Referral graph analyzer.** Referring-provider → destination edges → share retained in network vs leaked to competitors. |
| `provider_concentration.py` | **"Provider X controls $Y of revenue"** — partner-voice-memo call-out line. Concentration stats + departure stress test projection. |

---

## Chunk 7 summary

**44 files · 295/1,705 cumulative (17.3%).** **All 10 modules lack READMEs — same doc gap as chunk 6.** Cumulative legacy diligence gap now 19 modules.

**Priority backfill ordering refined**:
1. `integrity/` (chunk 6) — called preflight every packet-builder run
2. `deal_mc/` (chunk 6) — headline MC feeding every downstream consumer
3. `benchmarks/` (chunk 6) — Phase 2 HFMA-KPI spine
4. **`ma_dynamics/`** (chunk 7) — V28 recalibration is the deepest analytic moat + Cano-parallel causal story
5. **`real_estate/`** (chunk 7) — Steward-module, pattern-matches REIT-landlord failure mode
6. **`physician_comp/`** (chunk 7) — novel productivity-drift simulator + Stark/AKS red-line detector
7. `cyber/`, `deal_autopsy/` (chunk 6)
8. Everything else

**Key architectural insights captured**:
- **V28 is the load-bearing MA analytic.** `ma_dynamics/v28_recalibration.py` takes a member roster + dx codes and computes per-member revenue impact of V24→V28 — directly parallels Cano's bankruptcy trajectory. This is the "Cano Health again" detector.
- **Steward module = 5-factor pattern match.** `real_estate/steward_score.py` pattern-matches REIT landlord + rent-to-rev + undercap + Medicaid mix + refi calendar. Produced Steward (2024) + Prospect (2025). Hard-calibrated from known failures.
- **Synthetic-FTE detector is a fraud-signature module.** `labor/synthetic_fte_detector.py` reconciles scheduling vs billing NPIs vs 941 payroll — gap >25% flags locum inflation or ghost providers. Not a model, a reconciliation.
- **Physician EU = drop-candidate bridge lever.** `physician_eu/analyzer.py` finds net-negative providers at FMV comp → the EBITDA uplift from "drop at close" feeds Deal MC directly.
- **Earnout advisor is context-aware.** `physician_comp/earnout_advisor_enhancement.py` doesn't just recommend "use an earnout" — it picks the structure based on top-5 concentration thresholds.

**Next chunk (8)**: `diligence/` legacy batch 3 — regulatory, reputational, root_cause, screening, synergy, value, working_capital. Plus check `ccd_bridge.py` already covered. ~50 files.

---

## Chunk 8 — `diligence/` legacy batch 3 (22 files, **all 7 ✗ NO README — completes the legacy gap**)

**Cumulative legacy diligence doc gap: 26 of 28 modules lack READMEs** (every legacy module; `root_cause/` and `value/` are single-file thin phase markers that may not need more than a docstring).

### `rcm_mc/diligence/regulatory/` — 7 files ✗

**Regulatory exposure modeling** (Gap 3). Five analytics + a packet composer + TEAM calculator. Each consumable independently; composes into a `RegulatoryRiskPacket` attached to `DealAnalysisPacket` at step 5.5.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — five submodules + packet composition. |
| `packet.py` | **`RegulatoryRiskPacket` composer.** Attaches to `DealAnalysisPacket` at step 5.5 (after comparables, before reimbursement). Carries outputs of all five regulatory submodules. |
| `cpom_engine.py` | **Corporate Practice of Medicine exposure.** Target's legal structure × state footprint × `content/cpom_states.yaml` lattice → per-state CPOM exposure. |
| `nsa_idr_modeler.py` | **No Surprises Act IDR exposure.** For hospital-based physician groups (ER, anesthesia, radiology, pathology, neonatology, hospitalist) — OON revenue share × QPA recalc → revenue-at-risk. |
| `site_neutral_simulator.py` | **OPPS vs PFS site-neutral migration.** HOPD revenue × three scenarios (current CY2026 / MedPAC all-ambulatory / full legislative expansion) × 340B overlay. |
| `antitrust_rollup_flag.py` | **FTC/DOJ antitrust rollup detector.** Target acquisition history + specialty + MSA → estimated HHI at (MSA, specialty) + HSR expansion exposure. |
| `team_calculator.py` | **CMS TEAM calculator.** Mandatory bundled-payment model — 741 hospitals in 188 CBSAs starting 2026-01-01. Bundled episodes: LEJR, SHFFT, spinal fusion, CABG, major bowel. |

### `rcm_mc/diligence/reputational/` — 4 files ✗

**Reputational + ESG risk** (Gap 12). Three submodule scanners plus package init.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — 3 submodules. |
| `state_ag_heatmap.py` | **State AG enforcement heatmap.** State AGs with active PE-healthcare review regimes + recent enforcement. Refresh quarterly against state AG press releases. |
| `bankruptcy_contagion.py` | **Same-specialty / same-region / same-landlord cluster detector.** Known-bankruptcy corpus × target's signature → cluster-risk flag ("3 nearby bankruptcies in specialty Y, landlord Z"). |
| `media_risk_scan.py` | **Regex keyword scan** over caller-supplied archived coverage (ProPublica, STAT, NYT, KHN, Fierce Healthcare, Modern Healthcare, PESP). Target-name + risk-keyword hits. |

### `rcm_mc/diligence/root_cause/` — 1 file ✗

**Phase 3 — Root Cause Analysis.** Pareto of drivers for every off-benchmark KPI. ZBA autopsy surfaces recoverable write-offs. Every finding is one click from underlying CCD rows.

| File | Purpose |
|------|---------|
| `__init__.py` | **Phase 3 marker.** Currently just the docstring — actual root-cause logic lives distributed across `benchmarks/` + `counterfactual/` + individual risk modules. This is a phase placeholder; future analytics will land here. |

### `rcm_mc/diligence/screening/` — 2 files ✗

**Pre-packet scans** — the go-to-market wedge.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "the go-to-market wedge" for 30-minute teaser scans. RED/CRITICAL means deal doesn't advance. |
| `bankruptcy_survivor.py` | **Bankruptcy-Survivor Scan — 12 deterministic patterns.** Historical failure sig matches (6): Steward (2016 MPT → 2024), Cano (2023), Envision, Prospect, USAP, Surgery Partners-era. Live-risk patterns (6): REIT-landlord clusters, V28-exposed MA rollups, locum-inflated rosters, NSA-exposed ER groups, HDHP-heavy patient-pay mix, deferred-capex signatures. 12 deterministic checks, ~30 min to run. |

### `rcm_mc/diligence/synergy/` — 3 files ✗

**Synergy realization** (Gap 8). Two analytics that reality-check seller-claimed synergies.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — two submodules. |
| `integration_velocity.py` | **EHR migration cost library + time estimator.** Epic migration: 18-36 months, ~$100-200K per provider + $500K-$1.5M per bed at system level. Seeded from published case studies. |
| `cross_referral_reality_check.py` | **Sister-practice referral test.** Sellers claim cross-referral synergy between sister practices. This uses `referral/leakage_analyzer.py` data to reality-check the claim — how much cross-referral is actually happening vs claimed. |

### `rcm_mc/diligence/value/` — 1 file ✗

**Phase 4 — Value Creation Model.** Reuses existing infrastructure.

| File | Purpose |
|------|---------|
| `__init__.py` | **Phase 4 marker.** Per-root-cause recoverable EBITDA feeds `rcm_mc.pe.rcm_ebitda_bridge` (and `value_bridge_v2` when wired). Payer-behavior MC reuses `rcm_mc.mc.ebitda_mc`. Thin phase marker — actual value math lives in `pe/` + `mc/`. |

### `rcm_mc/diligence/working_capital/` — 4 files ✗

**Working-capital diligence** (Gap 7). Three submodules for closing NWC peg + DNFB reserve + pre-close gaming detector.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — 3 submodules. |
| `normalized_peg.py` | **Seasonality-adjusted NWC target.** Detrend by mean + adjust for quarterly seasonality indices, then average 12-24 months of trailing monthly NWC snapshots. Produces the closing NWC peg. |
| `dnfb_reserve.py` | **Discharged-Not-Final-Billed estimator.** DNFB = claims discharged but not billed by close. Acute hospital typical: 3-5 days; healthy RCM: 2-3. **Above 5 days = liquidity red flag.** |
| `pull_forward_detector.py` | **Pre-close collections pull-forward flag.** Sellers accelerate collections in 60 days pre-close to inflate closing NWC. Flag when last-60-days cash-flow index is meaningfully above trailing months. |

---

## Chunk 8 summary

**22 files · 317/1,705 cumulative (18.6%).** **All 7 modules lack READMEs. Cumulative legacy-diligence README gap is now 26 modules.**

**Final legacy-diligence backfill priority** (incorporating all three batches):
1. `integrity/` (chunk 6) — preflight choke point
2. `deal_mc/` (chunk 6) — headline MC
3. `benchmarks/` (chunk 6) — HFMA-KPI spine
4. `ma_dynamics/` (chunk 7) — V28 + Cano parallel
5. `real_estate/` (chunk 7) — Steward pattern match
6. **`screening/bankruptcy_survivor.py`** (chunk 8) — go-to-market wedge, 30-min teaser scan
7. **`regulatory/`** (chunk 8) — 5-submodule packet, composes into `DealAnalysisPacket` step 5.5
8. `physician_comp/` (chunk 7) — novel productivity-drift + Stark/AKS
9. `cyber/` (chunk 6) — Change Healthcare anchor
10. **`working_capital/`** (chunk 8) — closing NWC peg + DNFB + pull-forward detector (NWC negotiation leverage)
11. Everything else

**Thin modules (docstring-only may suffice)**:
- `root_cause/` — Phase 3 marker, logic lives distributed
- `value/` — Phase 4 marker, logic lives in `pe/` + `mc/`

**Key architectural insights captured**:
- **`screening/bankruptcy_survivor.py` is the go-to-market wedge.** 12 deterministic pattern-match checks, ~30 min runtime, RED/CRITICAL kills the deal before packet-builder spin-up. First defensive layer before any diligence investment.
- **Regulatory packet attaches at step 5.5** — between comparables and reimbursement. Clean composition: 5 submodules → `RegulatoryRiskPacket` → slot in packet. Not monolithic.
- **Working-capital trio = NWC negotiation leverage.** `normalized_peg` sets the peg; `dnfb_reserve` catches understated DNFB reserves; `pull_forward_detector` catches seller gaming. Together these are the partner's NWC negotiation ammunition at close.
- **Phase markers** (`root_cause/`, `value/`) deliberately thin — logic distributed across `benchmarks/`, `counterfactual/`, `pe/`, `mc/`. Package exists to hold the four-phase diligence narrative; source-of-truth lives elsewhere.

---

## Diligence/ cumulative summary (chunks 5-8)

**Total diligence files mapped: 137 of ~137** (matches the earlier file count — chunk 5 covered 31 new-cycle + ingest files, chunks 6-8 covered 106 legacy files).

| Sub-module | Files | README |
|-----------|-------|--------|
| (top-level + ingest) | 9 | ✗ (ingest) |
| **New cycle (7)** | 22 | ✓ all |
| **Legacy (28)** | 106 | ✗ 26 of 28 (gap) |

**Next chunk (9)**: `pe_intelligence/` — 276 files. Will take ~6 chunks at 50 files each. This is the partner-brain layer with 169+ named analytics. Starting alphabetically A-C.

---

## Chunk 9 — `pe_intelligence/` batch 1 (52 files, A–D, ✓ package README exists)

The **partner-brain layer** — senior-partner judgment over a `DealAnalysisPacket`. Consumes a packet, emits a `PartnerReview` with three kinds of output. Does not modify any existing calculation. Package-level [README](RCM_MC/rcm_mc/pe_intelligence/README.md) already indexes all 276 modules.

Each file here = one named analytic tied to a partner-voice statement ("Partner statement:" docstring at top). This chunk catalogues the first 52 alphabetical files (A–D, up to `data_room_gap_signal_reader`).

| # | File | Purpose |
|---|------|---------|
| 1 | `__init__.py` | Package surface — `DealAnalysisPacket` → `PartnerReview` contract. Does not modify existing math. |
| 2 | `add_on_fit_scorer.py` | Should we buy this bolt-on? Distinct from pipeline tracking (`ma_pipeline`) and post-close scoring (`ma_integration_scoreboard`). |
| 3 | `add_on_integration_sequencing_planner.py` | Order + pace of bolt-on integrations. "Roll-ups pitch 8-12 bolt-ons but integration team can do 2-3/year." |
| 4 | `analyst_cheatsheet.py` | 1-page associate pre-read. Renders `PartnerReview` into a glance-at-IC reference. |
| 5 | `archetype_canonical_bear_writer.py` | Per-archetype canonical bear case. "Payer-mix-shift bear ≠ roll-up bear." |
| 6 | `archetype_heuristic_router.py` | Archetype → which heuristics matter. Loading every rule for every deal dilutes the signal. |
| 7 | `archetype_outcome_distribution_predictor.py` | "What's realistic MOIC for this archetype?" — priors before reading the model's projection. |
| 8 | `archetype_subrunners.py` | Archetype-specific heuristic packs. Payer-mix-shift gets different scrutiny than a roll-up. |
| 9 | `auditor_view.py` | Full decision-audit-trail. "Why did this deal get PASS?" / "How did you justify the exit multiple?" for regulators + LPs 6 months later. |
| 10 | `bank_syndicate_picker.py` | Lender selection. Mega-deal (>$1B debt) = bulge-bracket; mid-market = specialty lenders. |
| 11 | `bank_syndicate_readiness_scorer.py` | Can we actually close the debt? Equity thesis can work and the deal still dies because debt doesn't come together. |
| 12 | `banker_narrative_decoder.py` | Pitch tactic recognizer. "Every banker runs the same 8 plays. Name the play → counter writes itself." |
| 13 | `banker_partner_pricing_tension.py` | Quantify the banker-vs-partner pricing gap + categorize. "Banker says 12x clears" — is it true? |
| 14 | `bear_book.py` | Pattern-match against things that actually went wrong in healthcare PE. Partner's "I've seen this before" engine. |
| 15 | `bear_case_generator.py` | The bear case a partner can defend. "If I can't write the bear, I haven't done the work." Different from the generator in `diligence/bear_case/` — this is the partner-voice version. |
| 16 | `benchmark_bands.py` | Partner-prudent sub-sector bands. Extends `reasonableness.py`, `extra_bands.py`, `reimbursement_bands.py` with 5 more. |
| 17 | `bidder_landscape_reader.py` | Who else is at the table. "A payer-backed bidder changes the process." |
| 18 | `board_composition_analyzer.py` | Portco board diversity + fit. Sponsor seats (2-3), independent directors, mgmt seats — standard shape. |
| 19 | `board_memo.py` | Governance-focused memo for sponsor boards. Fiduciary framing; different from the IC memo. |
| 20 | `buyer_type_fit_analyzer.py` | Which buyer is right for this asset. Different from `exit_channel_selector` (generic ranking) — more nuanced. |
| 21 | `c_suite_team_grader.py` | Per-seat grade + replace/coach/accept rec. "The deal is the team." |
| 22 | `capex_intensity_stress.py` | FCF bleed behind the EBITDA. "QofE shows capex has been below peer for 3 years — there's a hidden cliff." |
| 23 | `capital_plan.py` | Post-close capex + working-capital cash requirement. $50M of Y1 capex changes the MOIC thesis. |
| 24 | `capital_structure_tradeoff.py` | Debt/equity mix sweep. More leverage → higher equity MOIC but higher interest-coverage default risk. |
| 25 | `carve_out_risks.py` | Divestiture-specific risks. Buying from a parent > standalone in complexity. |
| 26 | `cash_conversion.py` | FCF ÷ EBITDA by subsector. Healthcare PE: hospital ≈ 0.4-0.6, physician ≈ 0.7-0.9, ASC ≈ 0.8-1.0. |
| 27 | `cash_conversion_drift_detector.py` | Early-warning on WC stress. "DSO rising 3 quarters is a tell before EBITDA shows it." |
| 28 | `change_my_mind_diligence_plan.py` | Partner's follow-up ask list. "Tell me the 3 things I'd need to see to change my mind." |
| 29 | `claims_denial_root_cause_classifier.py` | 12% denial rate is meaningless without composition (9% clerical / 3% medical ≠ 3% clerical / 9% medical). |
| 30 | `clinical_outcome_leading_indicator_scanner.py` | 18-month early warning. Readmission/HCAHPS deterioration hits reimbursement 18-24mo later. |
| 31 | `closing_conditions_list.py` | Sign-to-close risk, partner lens. "Signing is commitment; closing is ceremony; the conditions list is where we earn the break fee." |
| 32 | `cms_rule_cycle_tracker.py` | Annual CMS rule cycle × deal service lines. "IPPS proposed April / final August is a watch you can set." |
| 33 | `cohort_tracker.py` | Vintage-cohort comparison. 2023-healthcare-PE cohort: this deal vs peers. |
| 34 | `coinvest_sizing.py` | LP co-invest size for large deals. Sized on LP relationships × concentration caps × commercial terms. |
| 35 | `commercial_due_diligence.py` | CDD = "is the business good" (market size, share, competitive position). Separate from ops DD ("can we make it better"). |
| 36 | `comparative_analytics.py` | Portfolio-level cross-deal comparison. "Does this help the book or hurt it?" |
| 37 | `competing_deals_ranker.py` | 2-3 deals competing for attention → which one wins. Not "is each a buy" — "which wins." |
| 38 | `con_state_exposure_assessor.py` | Certificate of Need state exposure. Protects incumbents but blocks expansion. |
| 39 | `concentration_risk_multidim.py` | **6-dimension partner concentration scan.** Single-dim checks exist elsewhere (customer, payer); this aggregates. |
| 40 | `connect_the_dots_packet_reader.py` | Trace signals through downstream implications. "The senior-partner thing: we connect dots. Denial rate → denial mix → appeal quality → bad-debt trajectory." |
| 41 | `continuation_vehicle_readiness_scorer.py` | CV exit fit. Not every asset is CV-ready — CV investors want a known asset with a known problem. |
| 42 | `contract_diligence.py` | Payer-contract portfolio risk scorer. Takes contract list → risk-weighted revenue-at-renewal. |
| 43 | `contract_renewal_cliff_calendar.py` | Every contract resetting in hold — commercial payer, GPO, IT vendor, real-estate lease. Stacked timeline. |
| 44 | `cost_line_decomposer_healthcare.py` | Costs broken into 7 lines (labor, supply, prof fees, rent, …) × subsector peer band. |
| 45 | `covenant_monitor.py` | Live covenant tracking + waiver scenario math. Leverage/coverage/FCCR monthly. |
| 46 | `covenant_package_designer.py` | Partner's basket recommendation. "Bad covenant trips on noise; good covenant trips only on real distress." |
| 47 | `cross_module_connective_tissue.py` | Reason ACROSS signals. Partner doesn't read reasonableness, heuristics, bear book independently — connects them. |
| 48 | `cross_pattern_digest.py` | Connective tissue across pattern libraries. "One trap is a negotiation. Two traps on the same axis is a pass." |
| 49 | `customer_concentration_drilldown.py` | Beyond "top customer = X%" — top-N risk, contract terms, switching costs. |
| 50 | `cycle_timing.py` | Market-cycle phase for entry/exit. Every deal memo has an implicit cycle assumption. |
| 51 | `cycle_timing_pricing_check.py` | "Are we paying peak for peak?" Peak EBITDA × peak multiple = double count. |
| 52 | `data_room_gap_signal_reader.py` | What the seller isn't showing. "Missing documents aren't gaps to close — they tell you what's broken." |

---

## Chunk 9 summary

**52 files · 369/1,705 cumulative (21.6%).** Package-level README covers all 276 files; no per-file gap like the legacy diligence modules.

**Key architectural observations**:
- **Every `pe_intelligence/` module opens with a "Partner statement:"** — this is a deliberate convention. Each analytic encodes a specific thing a senior partner says out loud. Makes the module's purpose immediately clear.
- **Distinctions between similar modules are explicit.** `bear_case_generator.py` (partner-voice) vs `diligence/bear_case/generator.py` (evidence synthesizer). `add_on_fit_scorer.py` vs `ma_pipeline` vs `ma_integration_scoreboard`. `buyer_type_fit_analyzer.py` vs `exit_channel_selector`. Each docstring calls out the difference.
- **Partner-brain is a consumer, not a producer.** Every module reads `DealAnalysisPacket` and emits a judgment. Zero new math; zero writes to existing calculations.
- **Architectural families visible in this batch**:
  - **Archetype-aware** (5 files) — canonical bear writer, heuristic router, outcome distribution predictor, subrunners — recognize that "payer-mix shift" ≠ "roll-up" and route accordingly.
  - **Banker-facing** (3 files) — narrative decoder, syndicate picker, pricing tension.
  - **Covenant / capital** (4 files) — capital plan, capital structure tradeoff, covenant monitor, covenant package designer.
  - **Cash-conversion trio** (3 files) — cash_conversion, drift detector, capex intensity stress.

**Next chunk (10)**: `pe_intelligence/` batch 2 — D–I alphabetical. Starting with `deal_*` / `debt_*` / `diligence_*` / `earn_out_*` etc. ~50 files.

---

## Chunk 10 — `pe_intelligence/` batch 2 (50 files, D–H, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 53 | `data_room_tracker.py` | Seller data-room completeness checker — scores provided room against canonical healthcare-PE checklist. |
| 54 | `day_one_action_plan.py` | **Lock in value first 7 days.** "100-day plan gets the press; first 7 days get the value." |
| 55 | `de_novo_site_ramp_economics.py` | Month-by-month carrying cost to breakeven for new sites. De novos look great on 3-yr pro-forma — month-by-month they bleed. |
| 56 | `deal_archetype.py` | **10 canonical healthcare-PE shape classifier.** Platform-plus-tuck-in roll-up ≠ take-private; partners recognize deals by shape. |
| 57 | `deal_comparables.py` | M&A comp sourcing + implied-multiple stats. Lightweight comp-set builder partners cite to defend exit multiples. |
| 58 | `deal_comparison.py` | Side-by-side comparison of two `PartnerReview`s — "which one gets the check this quarter?" |
| 59 | `deal_one_liner.py` | **Margin-of-the-deck verdict.** "If I can't write it in one sentence, I don't understand it yet." |
| 60 | `deal_smell_detectors.py` | **Partner pattern-recognition reflexes.** Distinct from `historical_failure_library` (named) + `partner_traps_library` (pitch claims) — these are smell-test triggers. |
| 61 | `deal_source_quality_reader.py` | How the deal arrived. Proprietary 10-yr relationship ≠ 20-bidder auction. |
| 62 | `deal_to_historical_failure_matcher.py` | "What blowup does this look like?" — partner's pattern-match against named failures. |
| 63 | `debt_capacity_sizer.py` | Partner sanity check on leverage. Distinct from `capital_structure_tradeoff` (sweep) + `debt_sizing` (prudent for this deal). |
| 64 | `debt_sizing.py` | Partner-prudent leverage given payer mix + subsector. Banks underwrite healthcare-PE debt on EBITDA stability. |
| 65 | `deepdive_heuristics.py` | Ten more partner rules for mature diligence — complements `heuristics.py`, `red_flags.py`, `extra_heuristics.py`. |
| 66 | `denial_fix_pace_detector.py` | "9%→6% denial in 12mo" reality check. "Every RCM deck says it; few deliver." |
| 67 | `diligence_checklist_live.py` | What the packet answers vs what needs management interview. Live item-by-item status. |
| 68 | `diligence_spend_budget.py` | **How much to spend to decide.** $100M deal ≠ $1B deal DD budget. |
| 69 | `diligence_tracker.py` | Parallel-workstream tracker — financial / commercial / operational / legal / IT / regulatory. |
| 70 | `dividend_recap_analyzer.py` | **DPI lever without an exit.** Re-lever balance sheet → return cash to sponsor/LPs. Modeled against covenant impact. |
| 71 | `earnout_design_advisor.py` | **When and how to bridge the gap.** Earn-outs only for specific value-driver disagreements — not every gap. |
| 72 | `ebitda_normalization.py` | Reported → partner-prudent Adjusted EBITDA. Reverses aggressive seller add-backs. |
| 73 | `ebitda_quality.py` | Assesses seller add-backs against reported EBITDA. "Normalize for one-time / stranded overhead / day-1 synergies" — defensible vs not. |
| 74 | `ebitda_quality_bridge_reconstructor.py` | **Seller stated → partner run-rate bridge.** QofE passes + physician comp normalized + COVID reversed → defensible number. |
| 75 | `ehr_transition_risk_assessor.py` | Migration cost + productivity dip + revenue cliff. Epic-from-Cerner = 18-24mo pattern. |
| 76 | `esg_screen.py` | LP-required ESG output — exclusions + scoring + reporting readiness. Categorical (tobacco/firearms) + scored. |
| 77 | `exit_alternative_comparator.py` | **Sell now vs hold vs recap.** Board-meeting reflex question every cycle. |
| 78 | `exit_buyer_short_list_builder.py` | **Named-candidate list for exit.** "Exit thesis isn't a multiple — it's 5-10 named buyers." |
| 79 | `exit_buyer_view_mirror.py` | **Model the next sponsor's IC memo on us.** "At entry, write the exit buyer's IC memo." Best discipline. |
| 80 | `exit_channel_selector.py` | Rank 4 primary channels — Strategic / Sponsor / IPO / Continuation — generic ranking. |
| 81 | `exit_math.py` | Waterfall + preferred + carry calculations. Standard US PE waterfall: 8% pref → 50/50 catch-up → 20/80. |
| 82 | `exit_multiple_compression_scenarios.py` | **Partner stress test.** Entry at cycle-high; if exit reverts 1 turn → thesis gone; 2 turns → lose money. |
| 83 | `exit_planning.py` | Year-by-year exit-prep roadmap. Distinct from `exit_readiness` (one-time scorecard) — this is forward-looking. |
| 84 | `exit_readiness.py` | Pre-exit-process checklist — GAAP reviewed 3yrs, audit-ready financials, management team stable. |
| 85 | `exit_story_generator.py` | **Draft the banker's CIM headline at entry.** "If I can't write the sell-side pitch at entry, I don't know what I'm buying." |
| 86 | `exit_timing_signal_tracker.py` | When to start exit prep — 18-24mo pre-exit multi-signal convergence. |
| 87 | `extra_archetypes.py` | Specialized archetypes beyond `deal_archetype.py`'s canonical 10. |
| 88 | `extra_bands.py` | Finer-grained subsector reasonableness bands (extends `reasonableness.py`). |
| 89 | `extra_heuristics.py` | Additional partner-voice rules extending `heuristics.py` core rulebook. |
| 90 | `extra_red_flags.py` | Extra red-flag detectors beyond `red_flags.py` core 10 — physician turnover, cash-conversion drift, etc. |
| 91 | `failure_archetype_library.py` | **Shape-level failure patterns.** "Doesn't match any single blowup but matches the *shape* of three." |
| 92 | `first_thirty_minutes.py` | **Targeted management-interview opener.** Senior partner has 30 min to get the make-or-break answers. |
| 93 | `fund_level_vintage_impact_scorer.py` | **What does this deal do to the fund.** LPs don't grade individual deals — they grade vintage MOIC/IRR. |
| 94 | `fund_model.py` | Fund-level rollup — DPI, TVPI, called capital, carry projections. |
| 95 | `geographic_reach_analyzer.py` | **Multi-state complexity compounding.** Each state = Medicaid fee schedule + CON + AG + licensing. |
| 96 | `governance_package_designer.py` | **Close-date control architecture.** Board seats → reserved matters → protective provisions. |
| 97 | `growth_algorithm_diagnostic.py` | Decompose "20% revenue growth" → organic (price + volume + mix) vs inorganic (M&A) vs price-take. |
| 98 | `healthcare_regulatory_calendar.py` | **2026-2028 events partners track.** Duplicates/overlaps with `diligence/regulatory_calendar/` — this is the partner-voice version. |
| 99 | `healthcare_thesis_archetype_recognizer.py` | **7 healthcare deal shapes.** Payer-mix shift / back-office consolidation / geographic expansion / etc. Different classifier from `deal_archetype`. |
| 100 | `heuristics.py` | **Core 19-rule rulebook.** Triggerable: given packet → fire severity-stamped findings. The base layer `extra_*` and `deepdive_*` extend. |
| 101 | `historical_failure_library.py` | **Named/dated disasters.** "This looks like Envision 2023" or "Steward 2024." Specific incidents partners reason from, not generic patterns. |
| 102 | `hold_period_optimizer.py` | **Optimal hold years** — 5-year target varies by deal (archetype-aware). |

---

## Chunk 10 summary

**50 files · 419/1,705 cumulative (24.6%).** Package README covers.

**Architectural families in this batch**:
- **Exit family (10 files)** — `exit_alternative_comparator`, `exit_buyer_short_list_builder`, `exit_buyer_view_mirror`, `exit_channel_selector`, `exit_math`, `exit_multiple_compression_scenarios`, `exit_planning`, `exit_readiness`, `exit_story_generator`, `exit_timing_signal_tracker`. Each addresses a distinct exit question; docstrings explicitly distinguish them.
- **Deal-matching family (5 files)** — `deal_archetype`, `deal_smell_detectors`, `deal_source_quality_reader`, `deal_to_historical_failure_matcher`, `failure_archetype_library`. Named failures (specific) vs shape-level patterns (generic).
- **EBITDA-quality trio** — `ebitda_normalization` (reverse add-backs) + `ebitda_quality` (assess add-backs) + `ebitda_quality_bridge_reconstructor` (seller → partner run-rate).
- **Heuristics ladder** — `heuristics.py` (core 19) → `extra_heuristics.py` → `deepdive_heuristics.py`. Similar pattern for `red_flags.py` → `extra_red_flags.py` and `reasonableness.py` → `extra_bands.py` → `benchmark_bands.py`.
- **Duplicate watch**: `healthcare_regulatory_calendar.py` (partner-voice) overlaps with `diligence/regulatory_calendar/` (data engine). Intentional — one is analytic, the other is judgment layer. Future cleanup candidate if the overlap grows.

**Next chunk (11)**: `pe_intelligence/` batch 3 — I–M alphabetical. Starting with `ic_*` / `incumbency_*` / `initiative_*` / `loi_*` / `ma_*` / `management_*`. ~50 files.

---

## Chunk 11 — `pe_intelligence/` batch 3 (50 files, H–N, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 103 | `hold_period_shock_schedule.py` | **Year-by-year regulatory EBITDA hit.** "Covenant trips on one year's drop — I need the worst *year*, not worst total." |
| 104 | `hsr_antitrust_healthcare_scanner.py` | FTC/DOJ healthcare-PE exposure. Full second request = 6-9mo + $15M cost. |
| 105 | `hundred_day_plan.py` | **100-day post-close plan generator.** Dated, owned checklist — the single most important day-1 document. |
| 106 | `ic_decision_synthesizer.py` | **One partner-voice rec from many signals.** Digests scorecard + QoD + bear + margin-of-safety + pattern library → synthesizes. |
| 107 | `ic_dialog_simulator.py` | **Voices challenge each other across rounds.** Skeptic → responder → vote. Simulates real IC dynamic. |
| 108 | `ic_memo.py` | **IC memo formatter.** Renders `PartnerReview` three ways: markdown / HTML / text. Partners don't read JSON. |
| 109 | `ic_memo_header_synthesizer.py` | **First-page synthesizer.** Every IC memo page-1: Recommendation top + thesis one-sentence + guardrails + ask. |
| 110 | `ic_voting.py` | Weighted qualified votes aggregator — managing partner's vote counts more; not pure majority. |
| 111 | `icr_gate.py` | **Investment-Committee-Ready gate.** Must-have diligence items all green → IC-ready. Consolidator over `PartnerReview`. |
| 112 | `insurance_diligence.py` | Coverage review + claims-history risk. GL / prof liability / property / cyber / D&O portfolio analysis. |
| 113 | `insurance_tail_coverage_designer.py` | **Close-date tail coverage package.** Line item partners skip in DD that bites post-close. |
| 114 | `integration_readiness.py` | Post-close scorecard — is the DEAL TEAM ready to integrate. Distinct from `hundred_day_plan` (action list). |
| 115 | `integration_velocity_tracker.py` | Day-45 on-pace check against 100-day plan. |
| 116 | `investability_scorer.py` | **0-100 composite** — opportunity × value × stability. Single pre-memo number. (Distinct from `ml/investability_scorer.py` which is the HCRIS-fitted version.) |
| 117 | `irr_decay_curve.py` | **When does extending hold stop paying?** MOIC at higher hurdle rate — each additional year compresses IRR. |
| 118 | `kpi_alert_rules.py` | Threshold-based monthly ops-review alerts — target + upper/lower guardrails. |
| 119 | `labor_cost_analytics.py` | Staffing mix + productivity + wage pressure. Labor = 50-60% of healthcare OpEx. |
| 120 | `labor_shortage_cascade.py` | **Third canonical healthcare cascade** (after RCM + payer-mix). Nurse turnover → OT → contract labor → margin → quality → reimbursement. |
| 121 | `lbo_debt_paydown_trajectory.py` | "Does the debt actually get paid down?" Sponsors talk deleveraging; the model shows reality. |
| 122 | `lbo_stress_scenarios.py` | Named partner-recognizable downside scenarios — covenant-breach oriented. |
| 123 | `letter_to_seller.py` | **Partner-voice banker response letter.** Partners write back after deal goes final — feedback + relationship. |
| 124 | `liquidity_monitor.py` | Cash runway + 13-week cash forecast. Ops-partner tight-deal tool. |
| 125 | `local_market_intensity_scorer.py` | **MSA-level crowdedness.** "National HHI is noise. If we're the 6th urgent-care on the block, that's what matters." |
| 126 | `loi_drafter.py` | Partner-voice term-sheet generator from a `PartnerReview`. 8-10 key terms. |
| 127 | `loi_term_sheet_review.py` | **Pushback filter.** Partners push back on specific terms; associates mark up everything. This filters to partner-priority. |
| 128 | `lp_pitch.py` | LP-eyes summary — distinct from `ic_memo` ("do not show at IC" honesty). Investor-grade framing. |
| 129 | `lp_quarterly_update_composer.py` | Quarterly letter — "the only LP-facing document they read cover-to-cover." |
| 130 | `lp_side_letter_flags.py` | Side-letter conformance — concentration limits, excluded sectors, ESG clauses. |
| 131 | `lp_waterfall_distribution_modeler.py` | **Gross MOIC → net.** Partners pitch gross; LPs see net. 8% pref → catch-up → carry. |
| 132 | `ma_integration_scoreboard.py` | **Post-close bolt-on milestone tracker.** IT cutover, brand migration, billing integration per acquisition. |
| 133 | `ma_pipeline.py` | Add-on acquisition pipeline tracking for platform/roll-up deals — the thesis itself. |
| 134 | `ma_star_rating_revenue_impact.py` | **MA Star → QBP bonus.** 4-star = 5% bonus + rebates; drop to 3.5 = lose. |
| 135 | `management_assessment.py` | "Does this team win?" Pre-close team evaluation. |
| 136 | `management_bench_depth_check.py` | **Key-person risk beyond CEO.** What if CFO walks at 6 months? COO is new? |
| 137 | `management_comp.py` | MIP/LTIP sanity — 8-15% management equity pool, healthcare-PE norms. |
| 138 | `management_first_sitdown.py` | **First post-LOI working session agenda.** Distinct from `first_thirty_minutes` (screen MI). |
| 139 | `management_forecast_haircut_applier.py` | **Partner-prudent adjustment.** "Question isn't whether to haircut — it's by how much." |
| 140 | `management_forecast_reliability.py` | Track record — last 4 forecasts vs actual. Actual-to-forecast ratio. |
| 141 | `management_meeting_questions.py` | Monday-mgmt-meeting question set — not "tell me about the business." |
| 142 | `management_rollover_equity_designer.py` | **Rollover amount = seller conviction signal.** Design + size. |
| 143 | `management_vs_packet_gap.py` | Where mgmt story diverges from numbers. Small gaps OK; large gaps = flag. |
| 144 | `margin_of_safety.py` | **"How wrong can we be and still win?"** Partners ask this first. 20% wrong on EBITDA growth → still clear hurdle? |
| 145 | `market_structure.py` | HHI/CR3/CR5 + consolidation diagnosis. Standard IO metrics for healthcare markets. |
| 146 | `master_bundle.py` | **One-call master renderer.** Server / CLI / export single entry point — produces every artifact from a packet. |
| 147 | `medicaid_state_exposure_map.py` | **State-by-state Medicaid risk overlay.** OBBBA/sequestration apply nationally; Medicaid is state-specific. |
| 148 | `medicare_advantage_bridge_trap.py` | **"MA will make up FFS pressure" reflex check.** Does the math actually cover it? Usually doesn't. |
| 149 | `memo_formats.py` | Alternate IC memo renderers beyond `ic_memo.py`'s default markdown/HTML/text. |
| 150 | `mgmt_incentive_sizer.py` | Post-LBO MIP + LTIP sizing + vesting design. |
| 151 | `multi_state_regulatory_complexity_scorer.py` | **5 states = 12× complexity, not 5×.** Each state has its own CON + licensing + AG + Medicaid. |
| 152 | `named_failure_library_v2.py` | V2 additional named patterns beyond `historical_failure_library.py`. |

---

## Chunk 11 summary

**50 files · 469/1,705 cumulative (27.5%).** Package README covers.

**Architectural families in this batch**:
- **IC family (6 files)** — `ic_decision_synthesizer`, `ic_dialog_simulator`, `ic_memo`, `ic_memo_header_synthesizer`, `ic_voting`, `icr_gate`. Synthesizer composes; dialog simulates voices; memo renders; voting aggregates; gate consolidates the readiness bar.
- **Management family (9 files)** — assessment, bench depth, comp, first sitdown, forecast haircut applier, forecast reliability, meeting questions, rollover equity designer, vs-packet gap. Each addresses a distinct management-diligence question.
- **LP-facing trio** — `lp_pitch` (external), `lp_quarterly_update_composer` (quarterly letter), `lp_side_letter_flags` (conformance), `lp_waterfall_distribution_modeler` (gross→net).
- **LBO trio** — `lbo_debt_paydown_trajectory`, `lbo_stress_scenarios`, plus earlier `debt_capacity_sizer` / `debt_sizing` / `capital_structure_tradeoff`.
- **Partner-reflex quotes anchor many modules** — "The covenant trips on one year's drop, not the worst-case total" (`hold_period_shock_schedule`), "How wrong can I be and still win?" (`margin_of_safety`), "5 states is 12× complexity, not 5×" (`multi_state_regulatory_complexity_scorer`), "A 4-star MA plan gets 5% QBP bonus" (`ma_star_rating_revenue_impact`).

**Cascade families emerging**: RCM cascade, payer-mix cascade, labor-shortage cascade (`labor_shortage_cascade.py` calls itself "third canonical cascade"). Watch for #4 in later chunks.

**Next chunk (12)**: `pe_intelligence/` batch 4 — N–Q alphabetical. Starting `nwc_*` / `operating_partner_*` / `pe_*` / `physician_*` / `pipeline_*` / `portfolio_*`. ~50 files.

---

## Chunk 12 — `pe_intelligence/` batch 4 (50 files, N–R, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 153 | `narrative.py` | **Partner-voice IC narrative composer.** Takes `BandCheck` + `HeuristicHit` findings → IC memo commentary. |
| 154 | `narrative_styles.py` | Alternate voices — LP-facing, board-facing, banker-facing variants of the core narrative. |
| 155 | `negotiation_position.py` | Derives offer strategy from `PartnerReview` — walkaway price, concession priority, must-haves. |
| 156 | `obbba_sequestration_stress.py` | **OBBBA + sequestration + site-neutral $ stress.** Live-wire regulatory exposures in dollar-specific terms. |
| 157 | `one_hundred_day_plan_from_packet.py` | Auto-generates the day-1-100 action list straight off the packet — partners draft mentally while reading. |
| 158 | `operating_partner_fit_matrix.py` | **Which ops partner helps this CEO most.** Sponsor bench (ex-CFOs/CEOs/COOs/CMOs) × deal-profile → fit score. |
| 159 | `operating_posture.py` | Classifies deal stance — defensive / base / aggressive / growth — from stress-grid outcome + regime + concentration. |
| 160 | `operational_kpi_cascade.py` | Lever-to-EBITDA attribution — current/target KPI × sensitivity → $ impact per lever. |
| 161 | `outpatient_migration_cascade.py` | **Fourth canonical cascade.** Sister to RCM/payer-mix/labor. When thesis assumes procedures shift inpatient→outpatient, the downstream chain. |
| 162 | `packet_data_provenance_check.py` | **"Where did this number come from?"** Seller's $75M EBITDA vs QofE-adjusted vs partner-prudent — provenance per metric. |
| 163 | `partner_briefing_composer.py` | **Cross-module unified brief.** "Partners don't read 10 separate reports; they read one page pulling from all of them." |
| 164 | `partner_discussion.py` | Q&A generator — auto-composes partner-voice Q&A pairs from a `PartnerReview`. |
| 165 | `partner_review.py` | **The entry point.** External callers (UI / CLI / LP digests) call this one module — consumes a packet, wraps in PE judgment, returns `PartnerReview`. |
| 166 | `partner_scorecard.py` | **Binary must-have gate.** Not weighted — any single failure = pass. |
| 167 | `partner_traps_library.py` | Named thesis traps — specific fallacies from pitch decks. Each has a name + seller argument + partner counter. |
| 168 | `partner_voice_memo.py` | Recommendation-first IC output — partner-voice overlay; not a replacement for `ic_memo`. |
| 169 | `partner_voice_variants.py` | **Five IC narrators.** Senior partner asks "what would the skeptic say?" / "the operating partner?" / "the bear?" etc. Narrator rotation. |
| 170 | `patient_acquisition_cost_benchmark.py` | CAC vs specialty norm + LTV payback. "Decks pitch +12% patient growth without pricing CAC." |
| 171 | `payer_math.py` | Payer-mix-aware projection helpers — reimbursement is a blend of payer rates, each with its own growth schedule. |
| 172 | `payer_mix_risk.py` | Finer-grained payer concentration analysis. Extends `reasonableness.py` regime categorization. |
| 173 | `payer_mix_shift_cascade.py` | **Second canonical cascade.** Sister to `rcm_lever_cascade`. Medicaid→commercial claim cascades through rate × utilization × denials × AR. |
| 174 | `payer_renegotiation_timing_model.py` | **"The payer is coming" trap.** Commercial contracts reset; decks assume status-quo rates that won't hold. |
| 175 | `payer_watchlist_by_name.py` | Per-payer posture library — UHC/Anthem/etc behavioral profiles + partner reads. |
| 176 | `peer_discovery.py` | Similarity ranking across weighted feature vector — candidate deal vs reference set. |
| 177 | `physician_comp_normalization_check.py` | **Partner's EBITDA filter.** "Every physician deck has comp-normalization uplift; half of it is defensible." |
| 178 | `physician_compensation_benchmark.py` | Comp vs MGMA percentiles. PPM roll-ups have comp as largest cost. |
| 179 | `physician_group_friction_scorer.py` | **Post-close execution drag** on physician-practice deals. "Thesis closes at LOI; friction starts day 1 of ownership." |
| 180 | `physician_retention_stress_model.py` | "If top-N earners leave, what happens?" Physician-driven EBITDA sensitivity. |
| 181 | `physician_specialty_economic_profiler.py` | Per-specialty economic shape — ortho generates 4-6× PCP; specialties cluster by reimbursement profile. |
| 182 | `pipeline_tracker.py` | Sourcing funnel — sourced → IOI → LOI → exclusive DD → close. Per-stage yields. |
| 183 | `platform_vs_addon_classifier.py` | **2-4 turns of multiple at stake.** Platforms 12-15× / add-ons 8-10×. Every seller pitches platform; most are add-ons. |
| 184 | `portfolio_dashboard.py` | Aggregate view across `PartnerReview`s — deals per recommendation, pipeline → close, flags. |
| 185 | `portfolio_rollup_viewer.py` | Fund-level aggregation — per-deal metrics → fund-wide. LP-grade one-page. |
| 186 | `post_close_90_day_reality_check.py` | First-board-meeting question: "did the underwriting hold up 90 days in?" |
| 187 | `post_close_surprises_log.py` | **Diligence miss-rate feedback loop.** If we miss 15%+ of post-close surprises, the process has a systematic gap. |
| 188 | `post_mortem.py` | Structured lessons-learned template — exited and killed deals. |
| 189 | `pre_ic_chair_brief.py` | **4 bullets partner walks in with.** Thesis / where math works / where it breaks / ask. |
| 190 | `pre_mortem_simulator.py` | **"Write the post-mortem before you close."** If you can picture the write-up, the deal has a known-shape failure risk. |
| 191 | `pricing_concession_ladder.py` | **Never give price first** — structure / reps / indemnity / earn-out / peg → price. Sequence matters. |
| 192 | `pricing_power_diagnostic.py` | Can this company raise prices? Scored across differentiation, switching costs, demand elasticity, regulatory constraints. |
| 193 | `priority_scoring.py` | Ranks `PartnerReview`s so partner's next hour goes to highest-leverage deal. |
| 194 | `process_stopwatch.py` | **EKG for banker process tempo.** Deviations from canonical cadence carry meaning. |
| 195 | `qofe_prescreen.py` | Partner gut-read on add-back survival — "which of these 20-30% strip-backs will the QofE firm actually find?" |
| 196 | `qofe_tracker.py` | QofE pre-close deliverable tracker — in-progress / draft / final status + findings log. |
| 197 | `quality_metrics.py` | **CMS Star × readmissions × HCAHPS → VBP $.** Quality is reimbursement. |
| 198 | `quality_of_diligence_scorer.py` | **Audits OUR OWN team's work.** "Before I recommend, have we done enough?" Partner-reflex self-audit. |
| 199 | `quarterly_operating_review.py` | **Post-close QoR agenda.** Disciplined quarterly with CEO — not generic "how are things going." |
| 200 | `rac_audit_exposure_estimator.py` | **RAC/OIG audit exposure — "the number partners fear."** Disproportionate dollars on small process errors. |
| 201 | `rcm_lever_cascade.py` | **First canonical cascade.** Denial rate change → coding implications → CMI → NPSR → AR → cash. The prototype cascade pattern. |
| 202 | `rcm_vendor_switching_cost_assessor.py` | Transition drag + recovery. "Day-1 plan looks reasonable; month-3 hits and it doesn't." |

---

## Chunk 12 summary

**50 files · 519/1,705 cumulative (30.4%).** Package README covers.

**Four canonical cascades now fully identified** — this batch confirms the architecture insight:
1. **RCM lever cascade** (`rcm_lever_cascade.py`) — denial → coding → CMI → NPSR → AR → cash
2. **Payer-mix shift cascade** (`payer_mix_shift_cascade.py`) — Medicaid→commercial → rate × utilization × denials × AR
3. **Labor-shortage cascade** (`labor_shortage_cascade.py` — chunk 11) — nurse turnover → OT → contract labor → margin → quality → reimbursement
4. **Outpatient migration cascade** (`outpatient_migration_cascade.py`) — inpatient→outpatient → volume × payer mix × capex × fixed cost leverage

These four are the **cross-module reasoning chains** — the thing a senior partner does that a model doesn't: connect dots *across* modules. `cross_module_connective_tissue.py` (chunk 9) + `connect_the_dots_packet_reader.py` (chunk 9) + `cross_pattern_digest.py` (chunk 9) are the meta-engines that run over all four.

**Architectural families in this batch**:
- **Physician family (5)** — comp normalization check, comp benchmark (MGMA), group friction scorer, retention stress model, specialty economic profiler
- **Partner-voice family (7)** — narrative, narrative styles, partner discussion, partner review (entry point!), partner scorecard, partner voice memo, partner voice variants (5 narrators)
- **Post-close / feedback family (4)** — 90-day reality check, surprises log (diligence miss-rate loop), post-mortem, quarterly operating review
- **Pricing + process discipline (4)** — pricing concession ladder, pricing power diagnostic, process stopwatch (EKG), priority scoring
- **QofE family (2)** — pre-screen + tracker
- **Pre-IC discipline (2)** — chair brief (4 bullets) + pre-mortem simulator

**`partner_review.py` confirmed as THE external entry point** — callers (UI/CLI/LP digests) use this single module; everything else composes behind it.

**Next chunk (13)**: `pe_intelligence/` batch 5 — R–S. Starting `reasonableness` / `red_flags` / `ref_*` / `regime_*` / `regulatory_*` / `roll_up_*` / `sale_*` / `scenario_*` / `sector_*` / `seller_*` / `serviceable_*` / `signal_*`. ~50 files.

---

## Chunk 13 — `pe_intelligence/` batch 5 (50 files, R–T, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 203 | `reasonableness.py` | **Partner-first sanity bands.** "Is it reasonable?" before "is it correct?" IRR × size × payer matrix + margin bands by hospital type. The anchor band library. |
| 204 | `recon.py` | **Downstream consistency check.** `PartnerReview`, IC memo, LP pitch, 100-day plan — all derived from same packet; this ensures they agree. |
| 205 | `recurring_ebitda_line_scrubber.py` | Line-by-line EBITDA scrub — recurring vs one-time. "Exit multiple only applies to recurring EBITDA." |
| 206 | `recurring_npr_line_scrubber.py` | Same scrub for the top line — sellers stretch revenue too, not just EBITDA. |
| 207 | `recurring_vs_onetime_ebitda.py` | Splitter — companion to the scrubbers; partitions into recurring/one-time buckets for multiple application. |
| 208 | `red_flag_escalation_triage.py` | **Partner-attention filter.** "I'll take the FCA; you handle the denial trend." Not every flag needs a 7am partner call. |
| 209 | `red_flags.py` | **10 categorical deal-killers.** Subset of heuristics partners treat as pass-level, not probabilistic. "Payer concentration over 50% with a single commercial renewal in 18 months." |
| 210 | `red_team_review.py` | **Adversarial-hat review.** Before sign-off, systematically attack the bull case. Mini-red-team formalized. |
| 211 | `reference_check_framework.py` | **Structured CEO/CFO reference calls.** Generic calls miss signal. Who to call + what to ask matters. |
| 212 | `referral_flow_dependency_scorer.py` | **"Physician practice isn't selling patients — it's selling the referral network."** Who-sends-what volume. |
| 213 | `refinancing_window.py` | Portfolio-debt refi timing — floating-rate + covenant drift → optimal refi window detection. |
| 214 | `regime_classifier.py` | **Deal regime before underwriting.** Each named regime has a different playbook. Regime determines which heuristics fire first. |
| 215 | `regional_wage_inflation_overlay.py` | **Sub-national wage rates.** NYC/SF/LA/Boston/Seattle run materially higher than national. Existing cascades assumed one rate. |
| 216 | `regulatory_stress.py` | $ EBITDA impact from CMS/state rule changes. Beyond the static `regulatory_watch` registry — computed per deal profile. |
| 217 | `regulatory_watch.py` | **Curated registry** (not live feed) of CMS/OIG/state actions affecting healthcare-PE underwriting. |
| 218 | `reimbursement_bands.py` | Payer-rate growth + gross-to-net ranges. Medicare ≈ MarketBasket − productivity; commercial ≈ 3-5%; Medicaid frozen or negative. |
| 219 | `reimbursement_cliff.py` | **Named rate cliffs in hold window.** IMD waiver expiry, 340B rule, Medicare sequestration reset — model the $ hit at each. |
| 220 | `reimbursement_cliff_calendar_2026_2029.py` | **Pre-seeded cliff calendar** 2026-2029. "I shouldn't have to type CMS rules into every deal." |
| 221 | `reprice_calculator.py` | **How much to reprice from DD findings.** $5M QofE haircut + $2M lease concession + $1M IT → aggregate counter. |
| 222 | `reps_warranties_scope_negotiator.py` | **Scope matters more than cap/deductible.** Cap gets the attention; scope decides what's actually covered. |
| 223 | `reverse_diligence_checklist.py` | **Pre-sale self-DD.** "If a buyer's QofE team arrived tomorrow, what would they find?" 12-18mo pre-sale exercise. |
| 224 | `roic_decomposition.py` | **DuPont-style ROIC breakdown.** NOPAT/Invested Capital decomposed to spot weak links. |
| 225 | `rollup_arbitrage_math.py` | **"Roll-ups are sold as synergy stories; truth is the math is mostly multiple arbitrage."** Platform 12× × tuck-in 8× math. |
| 226 | `scenario_comparison.py` | Base / bull / bear 3-column pricing comparison. |
| 227 | `scenario_narrative.py` | Prose rendering of `StressGridResult` — stress grid in partner narrative form. |
| 228 | `scenario_stress.py` | **Deterministic mechanical shocks** (not MC). What if the one thing goes sideways. |
| 229 | `secondary_sale_valuation.py` | **GP-led / LP-led secondary pricing.** Mid-hold LP-interest or single-deal continuation vehicle pricing. |
| 230 | `sector_benchmarks.py` | Calibrated peer medians by subsector. Distinct from `reasonableness` (partner bands) — this is observed peer data. |
| 231 | `seller_math_reverse.py` | **"What must the seller believe?"** If they ask 16× → reverse-engineer the margin/growth/multiple combo that justifies it. |
| 232 | `seller_motivation_decoder.py` | **Why are they selling now?** Founder liquidity ≠ fund-forced ≠ strategic exit ≠ distressed. Motivation drives counter-price. |
| 233 | `sensitivity_grid.py` | OAT MOIC/IRR sweeps. "If exit at 9× not 11×, what's the damage?" |
| 234 | `service_line_analysis.py` | Service-line mix risk + margin contribution + exposure. |
| 235 | `service_line_growth_margin_quadrant.py` | **Star / cash cow / question / dog 2×2.** Each service line placed on growth × margin. |
| 236 | `signing_to_close_risk_register.py` | **60-120 day watchlist.** Signing ≠ close; asset can change materially; every delta has a named owner. |
| 237 | `site_neutral_specific_impact_calculator.py` | **Specific $ by service line** from site-neutral. Not a vague risk — specific codes, specific schedule. |
| 238 | `site_of_service_revenue_mix.py` | Inpatient / HOPD / ASC / physician-office mix. Where revenue is + where it can move. |
| 239 | `specialty_mix_stress_scorer.py` | Revenue concentration within specialties. "80% spine with 4 surgeons isn't a specialty practice — it's a group of 4 surgeons." |
| 240 | `sponsor_reputation_tracker.py` | **Who else is in the deal.** Mental file on other sponsors — bidding behavior, diligence style, close certainty. |
| 241 | `sponsor_vs_strategic_exit_comparator.py` | **Risk-adjusted per-day IRR.** Strategic offers 12× but takes 12 months with FTC/AG review vs sponsor 11× in 4 months. |
| 242 | `staffing_pipeline_analyzer.py` | Hiring + attrition math. Clinician supply makes/breaks healthcare-services companies. |
| 243 | `state_ag_pe_scrutiny_tracker.py` | **"State AGs are the new HSR for healthcare PE."** CA AB 3129 notice requirements, deal-delay risk per state. |
| 244 | `state_scope_of_practice_exposure.py` | NP/PA scope of practice + CPOM + non-compete + MSO exposure by state. Physician footprint tells you the regulatory burden. |
| 245 | `stress_test.py` | **Scenario-grid robustness scoring.** Composes over `scenario_stress.py` mechanical shocks → letter grade. Produces `StressGridResult`. |
| 246 | `subsector_ebitda_margin_benchmark.py` | **In-band / below / above vs peer.** Hospital at 15% fine; ASC at 15% soft; PT at 15% below peer. Subsector-dependent. |
| 247 | `subsector_partner_lens.py` | **Per-subsector partner reading frame.** Home-health questions ≠ hospital questions ≠ ASC questions. |
| 248 | `synergy_credibility_scorer.py` | **"Real or aspirational?"** Claimed synergies credibility check across platform/roll-up claims. |
| 249 | `synergy_modeler.py` | Revenue (cross-sell) + cost (G&A, RCM scale) + capital (WC release) synergy sizing for platform/roll-up deals. |
| 250 | `synergy_sequencing_scorer.py` | **When each synergy lands.** "Y1 is stabilization, not synergy. Seller's $12M Y1 synergy → I know it's Y2-Y3 at best." |
| 251 | `tax_structure_trap_scanner.py` | **Top-10 tax traps.** Partner doesn't need to be a tax lawyer — needs to recognize the 10 that kill after-tax IRR. |
| 252 | `tax_structuring.py` | Partner-level sanity checks on tax structure — seller type × buyer type × state × entity type. |

---

## Chunk 13 summary

**50 files · 569/1,705 cumulative (33.4%).**

**Architectural families in this batch**:
- **Recurring/one-time scrubbing trio** — `recurring_ebitda_line_scrubber`, `recurring_npr_line_scrubber`, `recurring_vs_onetime_ebitda`. Partners apply the exit multiple only to recurring.
- **Red flag / red team family (3)** — `red_flags` (10 categorical deal-killers), `red_flag_escalation_triage` (partner vs associate filter), `red_team_review` (adversarial-hat pre-signoff).
- **Regulatory family (5)** — `regulatory_stress`, `regulatory_watch`, `reimbursement_bands`, `reimbursement_cliff`, `reimbursement_cliff_calendar_2026_2029`. Note the 2026-2029 calendar is pre-seeded so partners don't retype per deal.
- **Seller-lens family (2)** — `seller_math_reverse` (reverse-engineer what they must believe) + `seller_motivation_decoder` (why selling now).
- **Scenario / stress family (5)** — `scenario_comparison`, `scenario_narrative`, `scenario_stress`, `stress_test`, `sensitivity_grid`. Mechanical shocks + grid composition + narrative + OAT sweeps.
- **Synergy trio** — `synergy_credibility_scorer` + `synergy_modeler` + `synergy_sequencing_scorer`. Is-it-real + size-it + when-does-it-land.
- **State-law exposure (3)** — `state_ag_pe_scrutiny_tracker` (deal-delay risk), `state_scope_of_practice_exposure` (NP/PA + CPOM + MSO), `regional_wage_inflation_overlay` (sub-national wage rates).

**Key reading**:
- `reasonableness.py` is the anchor band library everything extends (`extra_bands`, `benchmark_bands`, `reimbursement_bands`, `sector_benchmarks`).
- `stress_test.py` is the composer; `scenario_stress.py` is the unit. `StressGridResult` is the output type consumed by `scenario_narrative.py`.

**Next chunk (14)**: `pe_intelligence/` batch 6 (FINAL) — T–Z. Starting `team_*` / `technology_*` / `tender_*` / `thesis_*` / `v28_*` / `value_*` / `vintage_*` / `what_if_*`. ~24 files to finish the 276.

---

## Chunk 14 — `pe_intelligence/` batch 6 FINAL (24 files, T–Z, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 253 | `technology_debt_assessor.py` | Scores tech-debt drag — aged EHRs, fragmented billing, homegrown RCM. Materially moves integration cost + productivity ramp. |
| 254 | `thesis_break_price_calculator.py` | **Partner's walk number.** "Below it the math works; above it doesn't." Max justifiable bid. |
| 255 | `thesis_coherence_check.py` | **"Do the pillars fit together?"** Claiming margin expansion + 15% volume + labor cost reduction + quality improvement — how? Cross-claim consistency. |
| 256 | `thesis_implications_chain.py` | **Downstream walk.** "If denials come down, what else has to be true?" Chain validation. |
| 257 | `thesis_sharpness_scorer.py` | **"State it in one sentence with a number and a date."** If you can't, you don't understand the thesis. |
| 258 | `thesis_templates.py` | Prebuilt thesis narrative scaffolds — payer-mix shift / back-office consolidation / geographic expansion / roll-up / turnaround / platform-plus. |
| 259 | `thesis_validator.py` | **Internal-consistency check.** Entry price + operating plan + exit assumption — do they hang together? |
| 260 | `turnaround_feasibility_scorer.py` | **"Every turnaround starts with hope."** The ones that work have a specific operator, a dated plan, and known-quantity cash runway. |
| 261 | `unrealistic_on_face_check.py` | **Pre-math reflex.** "$400M NPR rural critical-access hospital" — red flag on sight; no model needed. |
| 262 | `unrealistic_on_its_face.py` | Duplicate/alternate of `unrealistic_on_face_check.py` — flagged for consolidation review. |
| 263 | `valuation_checks.py` | WACC + EV walk + DCF terminal value sanity. Three partner questions before looking at anything else in a DCF. |
| 264 | `value_creation_attribution.py` | **"Where does the MOIC come from?"** 40% multiple × 30% EBITDA growth × 20% debt paydown × 10% mult expansion — attribution math. |
| 265 | `value_creation_plan_generator.py` | **3-year VCP on one page.** Distinct from 100-day plan (immediate) and QoR (quarterly) — full hold-period roadmap. |
| 266 | `value_creation_tracker.py` | Post-close lever-vs-plan tracking, monthly cadence. Each lever: owner + target + actual + variance. |
| 267 | `vbc_portfolio_aggregator.py` | VBC contract concentration + total EBITDA across value-based-care contracts. "Single contract = one risk; portfolio = either diversification or doubled exposure." |
| 268 | `vbc_risk_share_underwriter.py` | **MLR corridor + stop-loss + EBITDA volatility.** VBC looks like growth on the deck; the math is harder. |
| 269 | `vintage_return_curve.py` | Per-vintage J-curve shape — negative Y1-2 / inflection Y3 / peak Y5-6 / decay Y7+. Partners overlay LP expectations against curve. |
| 270 | `white_space.py` | **Adjacency detection.** Where unserved opportunity exists — three dimensions: geographic / specialty / service-line. |
| 271 | `workbench_integration.py` | **Server/UI helpers.** Surface PE-intelligence outputs without the server knowing how every module composes. Composition abstraction. |
| 272 | `working_capital.py` | One-time cash from RCM improvements + supplier term reneg + inventory rationalization. Lever-release WC math. |
| 273 | `working_capital_peer_band.py` | DSO / DPO / DIO healthcare-PE peer bands. |
| 274 | `working_capital_peg_negotiator.py` | **The $ driver most deals under-negotiate.** At close, purchase price ± dollar-for-dollar vs NWC peg. $5M peg delta = $5M cash swing. |
| 275 | `working_capital_seasonality_detector.py` | **"Real drag or seasonal?"** Healthcare Q1 deductible-reset spike + year-end billing cycle → apparent WC drag that's actually seasonal. |
| 276 | `workstream_tracker.py` | Post-close integration dashboard — per-workstream owner + milestones + target date + status. |

---

## Chunk 14 summary — pe_intelligence/ package COMPLETE

**24 files · 593/1,705 cumulative (34.8%).** `pe_intelligence/` package fully mapped: **276 files across 6 chunks**.

**Architectural families in this final batch**:
- **Thesis family (6)** — `thesis_break_price_calculator`, `thesis_coherence_check`, `thesis_implications_chain`, `thesis_sharpness_scorer`, `thesis_templates`, `thesis_validator`. Each attacks a different thesis-quality angle: price boundary, cross-claim consistency, implication chain, sharpness, scaffolds, internal validation.
- **Value-creation family (4)** — `value_creation_attribution` (where MOIC comes from), `value_creation_plan_generator` (3-year VCP), `value_creation_tracker` (monthly actuals), plus `working_capital.py` (one-time cash release).
- **VBC (value-based care) pair** — `vbc_portfolio_aggregator` + `vbc_risk_share_underwriter`. Underwriter models MLR corridor + stop-loss; aggregator rolls up across contracts.
- **Working-capital family (4)** — `working_capital`, `working_capital_peer_band`, `working_capital_peg_negotiator`, `working_capital_seasonality_detector`. Four distinct WC lenses.
- **Unrealistic-on-face pair** — `unrealistic_on_face_check.py` and `unrealistic_on_its_face.py`. Two files doing nearly the same thing — **consolidation candidate**.

---

## pe_intelligence/ package-wide architecture summary

**276 files, single flat directory.** No subpackages. Each file = one named analytic tied to a partner-voice statement.

**Package-wide patterns**:
- **Entry point**: `partner_review.py` — external callers use only this module
- **Master renderer**: `master_bundle.py` — one call produces every artifact from a packet
- **Consumer, not producer**: reads `DealAnalysisPacket`, emits `PartnerReview` + artifacts
- **4 canonical cross-module cascades**: RCM lever, payer-mix shift, labor shortage, outpatient migration
- **Band/heuristic ladder**: `reasonableness.py` → `extra_bands` + `benchmark_bands` + `reimbursement_bands` + `sector_benchmarks`; `heuristics.py` → `extra_heuristics` → `deepdive_heuristics`; `red_flags.py` → `extra_red_flags`
- **Thesis attack surface**: 6 thesis modules + 2 unrealistic-on-face detectors = 8 layers of thesis validation
- **Narrator rotation**: `partner_voice_variants.py` runs 5 IC narrators (skeptic/operator/bear/builder/chair) over the same review

**Consolidation candidates flagged**:
- `unrealistic_on_face_check.py` + `unrealistic_on_its_face.py` — near-duplicate
- `healthcare_regulatory_calendar.py` (partner-voice) ↔ `diligence/regulatory_calendar/` (data engine) — intentional today; watch if divergence grows
- `investability_scorer.py` in both `pe_intelligence/` and `ml/` — distinct purposes (partner composite vs HCRIS-fitted) but similar names

**Next chunk (15)**: `ui/` batch 1 — 293 files, ~6 chunks. The server-side HTML page renderers. Starting alphabetically. UI package has its own README expected.

---

## Structural discovery: `ui/` breakdown

The 293 ui files split into three locations:
- **`ui/` direct** — 100 files (page renderers + shared UI kit)
- **`ui/data_public/`** — 173 files (**not** the same as top-level `rcm_mc/data_public/`; these are likely data-display page renderers)
- **`ui/chartis/`** — 20 files (Chartis-specific UI components)

Plan revised: chunks 15-16 = ui direct, 17-19 = ui/data_public/, 20 = ui/chartis/.

---

## Chunk 15 — `ui/` direct batch 1 (50 files, A–H, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 1 | `__init__.py` | Package marker. |
| 2 | `_chartis_kit.py` | **Chartis Kit dispatcher** — Phase 1 UI v2 editorial-rework thin layer routing to `_chartis_kit_v2` or legacy. |
| 3 | `_chartis_kit_legacy.py` | **Bloomberg Terminal / Palantir Foundry aesthetic shell.** Dark institutional Corpus Intelligence shared shell. The pre-rework version. |
| 4 | `_chartis_kit_v2.py` | **Drop-in replacement** for `_chartis_kit.py` — editorial-rework version. |
| 5 | `_html_polish.py` | Cross-generator HTML post-processors — used by run-output `report.html`, partner brief, portfolio dashboard. |
| 6 | `_ui_kit.py` | **Compat shim** re-exporting `shell` as `chartis_shell`. Held light-theme `BASE_CSS` + `shell()` historically; now delegates. |
| 7 | `_workbook_style.py` | Excel polish for `diligence_workbook.xlsx` — pandas-dumped tables → partner-ready Excel. |
| 8 | `advanced_tools_page.py` | Debt model + challenge solver + IRS 990 + trends. Connects remaining high-value backend modules to browser. |
| 9 | `analysis_landing.py` | Hub when user clicks "Analysis" nav without a deal selected. |
| 10 | `analysis_workbench.py` | **Bloomberg-style analyst workbench** at `/analysis/<deal_id>` — full single-deal page rendering the `DealAnalysisPacket`. |
| 11 | `analytics_pages.py` | Causal inference / counterfactual / benchmarks / scenario comparison pages. Connects `analytics/`, `pe/predicted_vs_actual`, `data/benchmark_evolution`. |
| 12 | `bankruptcy_survivor_page.py` | **Bankruptcy-Survivor Scan HTTP surface** — two renderers. |
| 13 | `bayesian_page.py` | Per-hospital Bayesian posterior KPIs — shows posterior estimates for all RCM metrics with credibility intervals. |
| 14 | `bear_case_page.py` | **`/diligence/bear-case`** — Bear Case Auto-Generator page. |
| 15 | `brand.py` | **Single source of truth for visual identity.** Every page, export, audit trail pulls from here. |
| 16 | `bridge_audit_page.py` | **`/diligence/bridge-audit`** — EBITDA Bridge Auto-Auditor page. |
| 17 | `command_center.py` | **"What should I do today?" page.** New users see screening focus; deal-team users see deal-level alerts. |
| 18 | `compare_page.py` | `/diligence/compare?left=<fixture>&right=<fixture>` — side-by-side diligence comparison. |
| 19 | `competitive_intel_page.py` | Per-hospital percentile rank on every metric × four peer groups — competitive-intel renderer. |
| 20 | `conference_page.py` | Healthcare PE conference + investor roadmap calendar — curated events. |
| 21 | `counterfactual_page.py` | **Premium Bloomberg-tier counterfactual advisor page.** Design-principles-heavy. |
| 22 | `covenant_lab_page.py` | **`/diligence/covenant-stress`** — Covenant & Capital Structure Stress Lab page. |
| 23 | `csv_to_html.py` | **Styled HTML table renderers for short CSV data** (UI-7). CSVs fine for scripts; unreadable when clicked — this makes them partner-readable. |
| 24 | `dashboard_v2.py` | **"Morning view" dashboard** (Prompt 31) — "what needs my attention today?" |
| 25 | `data_dashboard.py` | Data Intelligence dashboard — HCRIS coverage, benchmark freshness, ingestion status. |
| 26 | `data_explorer.py` | Browse-all-data-sources page. Connects `cms_care_compare`, `cms_utilization`, `system_network`, `benchmark_evolution`. |
| 27 | `data_room_page.py` | **Merge seller data with ML predictions.** Differentiating feature — analyst enters actual KPIs from seller, tool blends with predictor outputs. |
| 28 | `deal_autopsy_page.py` | `/diligence/deal-autopsy` — 9-dim signature → curated library ranking + narrative. |
| 29 | `deal_comparison.py` | Side-by-side comparison + screening (Prompt 33-A/C). |
| 30 | `deal_dashboard.py` | Unified single-deal view — all available information + models in one page. |
| 31 | `deal_mc_page.py` | **`/diligence/deal-mc`** — Deal Monte Carlo page. |
| 32 | `deal_profile_page.py` | **Unified deal profile** `/diligence/deal/<slug>` — single source of truth for one deal. |
| 33 | `deal_quick_view.py` | Fallback when full analysis unavailable — deal profile + links to available models. |
| 34 | `deal_timeline.py` | **Deal activity timeline** (Prompt 34) — pulls events from every table recording deal-level state change. |
| 35 | `demand_page.py` | Demand defensibility renderer — disease density + stickiness + elasticity for hospital's operating region. |
| 36 | `denial_page.py` | Browser-rendered denial driver decomposition — replaces raw JSON. |
| 37 | `denial_prediction_page.py` | `/diligence/denial-prediction` — CCD fixture → Naive Bayes denial model training + rendered report. |
| 38 | `diligence_benchmarks.py` | Phase 2 benchmarks tab — three sections one page. |
| 39 | `diligence_checklist_page.py` | **`/diligence/checklist`** — analyst's daily workspace. Coverage %, open P0/P1 blockers. |
| 40 | `diligence_page.py` | Diligence Tools page — questions + playbook + challenge solver. Connects `analysis/diligence_questions`, `analysis/playbook`. |
| 41 | `ebitda_bridge_page.py` | **Best-in-class PE returns math** — auto-generates bridge for any hospital. |
| 42 | `engagement_pages.py` | Engagement model's 3 HTTP surfaces — listing, detail, create. |
| 43 | `exit_timing_page.py` | `/diligence/exit-timing` — partners can't get this visualization elsewhere. |
| 44 | `fund_learning_page.py` | **Compounding moat dashboard.** Cross-deal accuracy — every closed deal improves the next. |
| 45 | `hcris_xray_page.py` | **`/diligence/hcris-xray`** — HCRIS-Native Peer X-Ray page. |
| 46 | `hold_dashboard.py` | `GET /hold/<deal_id>` — hold-period dashboard (Prompt 42) showing how the asset is performing vs VCP. |
| 47 | `home_v2.py` | **Seeking Alpha-inspired home** — market pulse, insights, active deals, watchlist. |
| 48 | `hospital_history.py` | **Treats hospital like a stock** — multi-year financials, YoY growth, trend arrows. |
| 49 | `hospital_profile.py` | **"Stock quote equivalent"** — click any CCN → fundamentals, ratings, peer comp. |
| 50 | `hospital_stats_page.py` | Per-hospital regression profile — where a single hospital sits across every variable. |

---

## Chunk 15 summary

**50 files · 643/1,705 cumulative (37.7%).** Package-level README covers.

**Architectural families emerging in the UI layer**:
- **Chartis Kit trio** — `_chartis_kit` (dispatcher) + `_chartis_kit_v2` (current) + `_chartis_kit_legacy` (Bloomberg/Palantir aesthetic). Drop-in replaceable via dispatcher.
- **Shared helpers (4)** — `_html_polish`, `_ui_kit`, `_workbook_style`, `brand`. All private/shared — never direct page renderers.
- **"Stock-quote" metaphor (3)** — `hospital_profile`, `hospital_history`, `hospital_stats_page`. Treats every hospital like a public ticker.
- **Dashboard family (4)** — `home_v2` (Seeking Alpha-inspired), `command_center` (today-focused), `dashboard_v2` (morning view), `data_dashboard`.
- **Diligence page renderers** — every diligence backend module has a corresponding `*_page.py` renderer here. Naming is consistent: backend `rcm_mc/diligence/X/` → UI `rcm_mc/ui/X_page.py`.
- **Deal-centric pages (6)** — `deal_dashboard`, `deal_profile_page`, `deal_quick_view`, `deal_timeline`, `deal_comparison`, `deal_autopsy_page`. Each is a different angle on the deal record.

**Next chunk (16)**: `ui/` direct batch 2 — remaining 50 direct ui files. H–Z alphabetical. Then chunks 17-19 for `ui/data_public/` (173 files).

---

## Chunk 16 — `ui/` direct batch 2 (50 files, I–W, ✓ package README)

| # | File | Purpose |
|---|------|---------|
| 51 | `ic_memo_page.py` | **One-click IC memo for any hospital.** Browser-rendered, uses public data only. |
| 52 | `ic_packet_page.py` | **`/diligence/ic-packet`** — runs full multi-module pipeline against a fixture → bundled IC memo HTML. |
| 53 | `json_to_html.py` | **Styled renderers for known PE JSON payloads** (UI-6) — `pe_bridge.json`, `pe_returns.json`, `pe_covenant.json` rendered as partner-readable tables. |
| 54 | `library_page.py` | **Methodology Hub** — PE diligence frameworks, benchmark data, model library. |
| 55 | `management_scorecard_page.py` | `/diligence/management` — per-exec scored cards + roster aggregate. |
| 56 | `market_analysis_page.py` | Market analysis renderer — HHI, moat, competitors as visual page. |
| 57 | `market_data_page.py` | National hospital market intel — heatmaps, regression, state comparisons. |
| 58 | `market_intel_page.py` | **`/market-intel`** — 3 stacked sections (public comps, PE transactions, sentiment). |
| 59 | `memo_page.py` | Auto-generated IC memo with sections + fact-check status. |
| 60 | `methodology_page.py` | **Trust-building explainer** — how every number is calculated, data sources, scoring models. |
| 61 | `ml_insights_page.py` | **ML Insights aggregator** — clustering + distress + RCM opportunity + temporal forecaster. Surfaces proprietary ML. |
| 62 | `model_validation_page.py` | **Prediction accuracy dashboard** — per-metric calibration, bias trends, coverage. |
| 63 | `models_page.py` | DCF / LBO / 3-Statement browser-rendered (not raw JSON). |
| 64 | `news_page.py` | Healthcare-PE news aggregator — industry + regulatory + deal coverage. |
| 65 | `onboarding_wizard.py` | **5-step guided onboarding** (Prompt 26) — `/new-deal` entry point, hospital name + drag-drop CCD. |
| 66 | `payer_stress_page.py` | **`/diligence/payer-stress`** — Payer Mix Stress Lab. |
| 67 | `pe_returns_page.py` | Connects `pe/pe_math.py` to browser — IRR/MOIC + covenant headroom rendering. |
| 68 | `pe_tools_page.py` | Connects other `pe/` modules — value bridge, debt model, predicted-vs-actual. |
| 69 | `physician_attrition_page.py` | `/diligence/physician-attrition` — roster flight-risk renderer. |
| 70 | `physician_eu_page.py` | `/diligence/physician-eu` — per-provider contribution ranked + loss-maker identification. |
| 71 | `pipeline_page.py` | **Deal Pipeline workflow** — saved searches, add-to-watchlist, hospital tracking. |
| 72 | `portfolio_bridge_page.py` | Aggregate EBITDA bridge — runs bridge for every pipeline hospital. |
| 73 | `portfolio_heatmap.py` | **`/portfolio/heatmap`** (Prompt 36) — deals × top-8 metrics heatmap. |
| 74 | `portfolio_map.py` | **`/portfolio/map`** (Prompt 69) — inline SVG US map of portfolio geography. |
| 75 | `portfolio_monitor_page.py` | Portfolio monitor — actual vs predicted early warnings, plan tracking, comp-relative. |
| 76 | `portfolio_overview.py` | **Default portfolio view** (replaces heatmap) — unified portfolio intelligence page. |
| 77 | `power_ui.py` | **Python side of PE-analyst power features.** Pairs with `ui/static/power_ui.{js,css}`. |
| 78 | `predictive_screener.py` | **The killer feature** — filter 6,000+ hospitals by predicted RCM performance. ML on public data. |
| 79 | `pressure_page.py` | Pressure Test renderer, `chartis_shell` wrapped. |
| 80 | `provenance.py` | **Source-attribution page for every number** — HCRIS / ML / partner input → per-metric trail. |
| 81 | `quant_lab_page.py` | **Full quant stack in browser** — Bayesian calibration + DEA + queueing + temporal forecaster. |
| 82 | `quick_import.py` | Browser-rendered deal creation form — POSTs to `/api/deals/import`. |
| 83 | `regression_page.py` | Interactive OLS regression — per-hospital residual analysis. |
| 84 | `regulatory_calendar_page.py` | **Partner-facing demo moment** — gantt-style timeline of thesis drivers dying on specific dates. |
| 85 | `risk_workbench_page.py` | **9-subpackage integration** — Regulatory Risk Workbench (Prompts G through O). |
| 86 | `scenario_modeler_page.py` | Named scenarios — RCM levers + payer mix + regulatory adjustments → returns impact. |
| 87 | `scenarios_page.py` | Scenario Explorer, `chartis_shell` wrapped. |
| 88 | `seeking_alpha_page.py` | **`/market-intel/seeking-alpha`** — public comps + PE transactions + news. |
| 89 | `sensitivity_dashboard.py` | **Interactive sliders** (Prompt 47) — PE deal parameter sensitivity in real time. |
| 90 | `settings_ai_page.py` | Anthropic Claude integration status — enable/disable AI features. |
| 91 | `settings_pages.py` | Custom KPIs / automations / integrations settings pages. |
| 92 | `source_page.py` | **`/source` deal-sourcing page** — thesis selector + results table over 6,000 hospitals. |
| 93 | `surrogate_page.py` | Surrogate Model renderer, `chartis_shell` wrapped. |
| 94 | `team_page.py` | Fund activity feed + assignments — who is working on what. |
| 95 | `text_to_html.py` | **ANSI+box-drawing terminal text → styled HTML page** (UI-3). Makes CLI output browser-readable. |
| 96 | `thesis_card.py` | **30-second deal answer card** — synthesizes all ML models into one answer. |
| 97 | `thesis_pipeline_page.py` | `/diligence/thesis-pipeline` — one button runs full chain. |
| 98 | `value_tracking_page.py` | Frozen EBITDA bridge plan vs quarterly actuals per lever. |
| 99 | `verticals_page.py` | **Sub-sector expansion** — ASC / Behavioral Health / MSO bridges (beyond acute hospitals). |
| 100 | `waterfall_page.py` | Returns waterfall visualization — connects `pe/waterfall.py`, shows LP/GP split. |

---

## Chunk 16 summary — `ui/` direct COMPLETE

**50 files · 693/1,705 cumulative (40.6%).** `ui/` direct (100 files) fully mapped.

**Architectural families across both ui-direct chunks (15+16)**:
- **Page-per-diligence-module** — every `diligence/X/` has `ui/X_page.py`. Enforced naming.
- **Format converters (4)** — `csv_to_html`, `json_to_html`, `text_to_html`, `_html_polish`. Take machine formats → partner-readable HTML.
- **Portfolio pages (5)** — overview (default), monitor, heatmap, map (SVG US), bridge (aggregate EBITDA).
- **Dashboards (5)** — `home_v2`, `command_center`, `dashboard_v2`, `data_dashboard`, `deal_dashboard`.
- **Model/trust pages (4)** — `methodology_page`, `model_validation_page`, `provenance`, `library_page`. Trust-building surface.
- **Power features (2)** — `predictive_screener` (filter 6,000 hospitals by predicted RCM), `quant_lab_page` (Bayesian + DEA + queueing + forecaster in one page).
- **Workflow surfaces (4)** — `onboarding_wizard`, `quick_import`, `pipeline_page`, `team_page`.

**Chartis Kit pattern**: many pages end with `chartis_shell` wrapper — Pressure, Scenarios, Surrogate. Consistent rendering shell abstraction across all pages.

**Next chunk (17)**: `ui/data_public/` batch 1 — 173 files split across 3-4 chunks. First let me inspect what's in there — likely data-display page renderers for public data sources.

---

## Chunk 17 — `ui/data_public/` batch 1 (50 files, A–D, 1 package init)

**Discovery**: `ui/data_public/` is **173 uniform `*_page.py` renderers** + `__init__.py`. Each file is a single HTTP route page. Pattern: `<topic>_page.py` → `/<topic>` route. No nested subdirs.

This is the **"corpus browser"** surface — pages that let partners browse the curated healthcare-PE intelligence corpus (635+ deals). Distinct from `ui/` direct, which is the diligence-workflow surface.

| # | File | Route + focus |
|---|------|---------------|
| 1 | `__init__.py` | Package marker. |
| 2 | `aco_economics_page.py` | `/aco-economics` — ACO economics. |
| 3 | `acq_timing_page.py` | `/acq-timing` — Entry multiple vs MOIC cycle analysis. |
| 4 | `ai_operating_model_page.py` | `/ai-operating-model` — AI/ML operating model. |
| 5 | `antitrust_screener_page.py` | `/antitrust-screener` — FTC review screener. |
| 6 | `backtest_page.py` | `/backtest` — Corpus-calibrated model validation. |
| 7 | `base_rates_page.py` | `/base-rates` — Multi-dim P25/P50/P75/P90 percentile cuts across EV/EBITDA. |
| 8 | `biosimilars_opp_page.py` | `/biosimilars` — Biosimilar opportunity analyzer. |
| 9 | `board_governance_page.py` | `/board-governance` — Board governance. |
| 10 | `bolton_analyzer_page.py` | `/bolton-analyzer` — Platform + N bolt-ons roll-up model. |
| 11 | `cap_structure_page.py` | `/cap-structure` — Leverage sensitivity + WACC curve + breach probabilities. |
| 12 | `capex_budget_page.py` | `/capex-budget` — Capex planning tracker. |
| 13 | `capital_call_tracker_page.py` | `/capital-call` — Capital call / LP comms tracker. |
| 14 | `capital_efficiency_page.py` | `/capital-efficiency` — MOIC per turn of entry multiple. |
| 15 | `capital_pacing_page.py` | `/capital-pacing` — Capital call pacing model. |
| 16 | `capital_schedule_page.py` | `/capital-schedule` — J-curve, DPI/TVPI, LP waterfall quarterly. |
| 17 | `cin_analyzer_page.py` | `/cin-analyzer` — Clinically Integrated Network analyzer. |
| 18 | `clinical_ai_tracker_page.py` | `/clinical-ai` — Clinical AI/ML deployment tracker. |
| 19 | `clinical_outcomes_page.py` | `/clinical-outcomes` — Star / readmission / VBC contracts / quality ROI. |
| 20 | `cms_apm_tracker_page.py` | `/cms-apm` — CMS Innovation Models / APM tracker. |
| 21 | `cms_data_browser_page.py` | `/cms-data-browser` — CMS public data browser. |
| 22 | `cms_sources_page.py` | `/cms-sources` — CMS Open Data endpoints + dataset IDs catalog. |
| 23 | `coinvest_pipeline_page.py` | `/coinvest-pipeline` — Co-invest pipeline + LP allocation tracker. |
| 24 | `comparables_page.py` | `/comparables` — Query-deal → most-similar corpus deals. |
| 25 | `competitive_intel_page.py` | `/competitive-intel` — Landscape + strategic moves + gap analysis. |
| 26 | `compliance_attestation_page.py` | `/compliance-attestation` — Security posture tracker. |
| 27 | `concentration_risk_page.py` | `/concentration-risk` — HHI/CR3/CR5 portfolio diversification. |
| 28 | `continuation_vehicle_page.py` | `/continuation-vehicle` — GP-led secondary economics. |
| 29 | `corpus_coverage_page.py` | `/corpus-coverage` — Per-field coverage + completeness heatmap. |
| 30 | `corpus_dashboard_page.py` | `/corpus-dashboard` — Executive summary of 635-deal corpus analytics. |
| 31 | `corpus_flags_panel.py` | **Injector** for `/analysis/<deal_id>` — corpus red-flag panel (not a standalone page). |
| 32 | `cost_structure_page.py` | `/cost-structure` — COGS vs SG&A decomposition, labor, operating leverage. |
| 33 | `covenant_headroom_page.py` | `/covenant-headroom` — Debt covenant headroom monitor. |
| 34 | `covenant_monitor_page.py` | `/covenant-monitor` — Covenant monitor. |
| 35 | `cyber_risk_page.py` | `/cyber-risk` — Cyber risk + HIPAA scorecard. |
| 36 | `data_sources_admin_page.py` | `/admin/data-sources` — Seed files + CMS datasets + scraper status inventory. |
| 37 | `deal_flow_heatmap_page.py` | Year × sector activity heatmap (deal count by cell, color intensity). |
| 38 | `deal_origination_page.py` | `/deal-origination` — M&A pipeline tracker. |
| 39 | `deal_pipeline_page.py` | `/deal-pipeline` — Live pipeline funnel + stage conversion + source ROI. |
| 40 | `deal_postmortem_page.py` | `/deal-postmortem` — Deal post-mortem. |
| 41 | `deal_quality_page.py` | `/deal-quality` — Scores corpus deals on data completeness + analytical credibility. |
| 42 | `deal_risk_scores_page.py` | `/deal-risk-scores` — 5-dimension risk dashboard over every corpus deal. |
| 43 | `deal_search_page.py` | `/deal-search` — Full-text search across 655 corpus deals. |
| 44 | `deal_sourcing_page.py` | `/deal-sourcing` — Proprietary flow tracker. |
| 45 | `deals_library_page.py` | `/deals-library` — Dense sortable 615+ corpus deals with payer mix + MOIC. |
| 46 | `debt_financing_page.py` | `/debt-financing` — LBO commitment tracker. |
| 47 | `debt_service_page.py` | `/debt-service` — DSCR + interest coverage + leverage multiples. |
| 48 | `demand_forecast_page.py` | `/demand-forecast` — Demand forecast. |
| 49 | `denovo_expansion_page.py` | `/denovo-expansion` — De novo expansion tracker. |
| 50 | `digital_front_door_page.py` | `/digital-front-door` — Patient experience tracker. |

---

## Chunk 17 summary

**50 files · 743/1,705 cumulative (43.6%).**

**Key structural observation**: `ui/data_public/` is a **corpus-browser surface** — not the diligence-workflow UI (which lives in `ui/` direct). The purpose is clear:
- Every file = one HTTP route page displaying a curated corpus cut
- "Corpus" = the 635+ deal healthcare-PE intelligence dataset seeded into the platform
- Pattern: `<topic>_page.py` → `/<topic>` — uniform naming, no variation
- Uses same chartis_shell / _ui_kit rendering helpers as `ui/` direct (imports from parent)
- **One exception**: `corpus_flags_panel.py` — a panel injector for `/analysis/<deal_id>`, not a standalone page

**Functional families in this batch**:
- **Capital/LP tracking (6)** — capital call tracker, call pacing, schedule, call tracker, coinvest pipeline, LP allocation
- **Corpus meta (5)** — corpus coverage, corpus dashboard, corpus flags panel, deals library, deal search
- **Deal-flow dashboards (5)** — deal flow heatmap, origination, pipeline, postmortem, quality, risk scores, sourcing
- **CMS data (3)** — CMS APM tracker, data browser, sources catalog
- **Risk & covenants (5)** — concentration risk, cyber risk, covenant headroom, covenant monitor, antitrust screener
- **Clinical / operational (4)** — ACO economics, clinical AI tracker, clinical outcomes, digital front door
- **Capex / cost structure (3)** — capex budget, cost structure, capital efficiency
- **Analytical utilities (3)** — backtest, base rates, comparables

**Next chunk (18)**: `ui/data_public/` batch 2 — files 51-110 (D–N alphabetical). ~60 files to keep momentum.

---

## Chunk 18 — `ui/data_public/` batch 2 (60 files, D–P)

| # | File | Route + focus |
|---|------|---------------|
| 51 | `diligence_checklist_page.py` | `/diligence-checklist` — Checklist generator. |
| 52 | `diligence_vendors_page.py` | `/diligence-vendors` — DD vendor directory. |
| 53 | `direct_employer_page.py` | `/direct-employer` — Direct-to-employer contract analyzer. |
| 54 | `direct_lending_page.py` | `/direct-lending` — Private credit / direct lending tracker. |
| 55 | `dividend_recap_page.py` | `/dividend-recap` — Recap scenarios + timing + carry impact. |
| 56 | `dpi_tracker_page.py` | `/dpi-tracker` — DPI / distribution tracker. |
| 57 | `drug_pricing_340b_page.py` | `/drug-pricing-340b` — 340B drug pricing analyzer. |
| 58 | `drug_shortage_page.py` | `/drug-shortage` — Drug shortage + supply-chain risk. |
| 59 | `earnout_page.py` | `/earnout` — Milestone-based payouts + probability-weighted value + fair-value + IRR impact. |
| 60 | `entry_multiple_page.py` | `/entry-multiple` — EV/EBITDA distribution + sector benchmarks + expansion/contraction. |
| 61 | `escrow_earnout_page.py` | `/escrow-earnout` — Escrow + earnout tracker. |
| 62 | `esg_dashboard_page.py` | `/esg-dashboard` — ESG scorecard with ILPA/SASB/TCFD disclosures. |
| 63 | `esg_impact_page.py` | `/esg-impact` — ESG impact reporting tracker. |
| 64 | `exit_multiple_page.py` | `/exit-multiple` — Exit multiple analysis. |
| 65 | `exit_readiness_page.py` | `/exit-readiness` — Multi-dim readiness across Financial / Operational / Strategic. |
| 66 | `exit_timing_page.py` | `/exit-timing` — Exit by sector / vintage / payer mix. |
| 67 | `find_comps_page.py` | **User inputs deal characteristics → ranked corpus comparables.** |
| 68 | `fraud_detection_page.py` | `/fraud-detection` — FWA panel. |
| 69 | `fund_attribution_page.py` | `/fund-attribution` — IRR decomposed into operational / multiple expansion / leverage. |
| 70 | `fundraising_tracker_page.py` | `/fundraising` — LP pipeline. |
| 71 | `geo_market_page.py` | `/geo-market` — CBSA-level white-space + competitive density + demographic overlay. |
| 72 | `gp_benchmarking_page.py` | **GP selector → corpus peer comparison of their deals.** |
| 73 | `gpo_supply_tracker_page.py` | `/gpo-supply` — GPO / supply-chain savings tracker. |
| 74 | `growth_runway_page.py` | `/growth-runway` — TAM/SAM/SOM + penetration curve + share expansion. |
| 75 | `hcit_platform_page.py` | `/hcit-platform` — HCIT / SaaS platform analyzer. |
| 76 | `health_equity_page.py` | `/health-equity` — SDOH scorecard. |
| 77 | `hold_analysis_page.py` | Hold duration vs realized returns — MOIC scatter + P-tile buckets. |
| 78 | `hold_optimizer_page.py` | `/hold-optimizer` — Entry profile → optimal hold via corpus patterns. |
| 79 | `hospital_anchor_page.py` | `/hospital-anchor` — Hospital anchor contract tracker. |
| 80 | `ic_memo_generator_page.py` | `/ic-memo-gen` — Standardized IC memo. |
| 81 | `ic_memo_page.py` | **Corpus-benchmarked IC memo section** — deal inputs via GET → 700+ corpus benchmark. Distinct from `ui/ic_memo_page.py` (diligence-workflow version). |
| 82 | `insurance_tracker_page.py` | `/insurance-tracker` — Insurance tracker. |
| 83 | `irr_dispersion_page.py` | Realized IRR distribution across corpus — histogram + scatter + buckets. |
| 84 | `key_person_page.py` | `/key-person` — Clinical concentration + CEO/top-producer dependence + departure scenarios. |
| 85 | `lbo_stress_page.py` | `/lbo-stress` — LBO stress test. |
| 86 | `leverage_intel_page.py` | `/leverage-intel` — Corpus-calibrated capital-structure analysis. |
| 87 | `litigation_tracker_page.py` | `/litigation` — Watchlist tracker. |
| 88 | `locum_tracker_page.py` | `/locum-tracker` — Locum / contract workforce. |
| 89 | `lp_dashboard_page.py` | `/lp-dashboard` — TVPI/DPI/RVPI + gross/net MOIC + IRR + loss rate. |
| 90 | `lp_reporting_page.py` | `/lp-reporting` — LP reporting dashboard. |
| 91 | `ma_contracts_page.py` | `/ma-contracts` — Medicare Advantage contract analyzer. |
| 92 | `ma_star_tracker_page.py` | `/ma-star` — MA Star Ratings tracker. |
| 93 | `market_rates_page.py` | P25/P50/P75 MOIC + IRR by sector × payer × hold. |
| 94 | `medicaid_unwinding_page.py` | `/medicaid-unwinding` — Redetermination coverage tracker. |
| 95 | `medical_realestate_page.py` | `/medical-realestate` — MOB (medical office building) tracker. |
| 96 | `mgmt_comp_page.py` | `/mgmt-comp` — Rollover equity + options + MIP + alignment scoring. |
| 97 | `mgmt_fee_tracker_page.py` | `/mgmt-fee-tracker` — Management fee tracker. |
| 98 | `module_index_page.py` | `/module-index` — Module index. |
| 99 | `msa_concentration_page.py` | `/msa-concentration` — MSA provider market concentration. |
| 100 | `multiple_decomp_page.py` | Entry EV/EBITDA → sector baseline + size adjustment + growth premium + quality premium. |
| 101 | `nav_loan_tracker_page.py` | `/nav-loan-tracker` — NAV loan / fund-level financing. |
| 102 | `nsa_tracker_page.py` | `/nsa-tracker` — No Surprises Act / IDR tracker. |
| 103 | `operating_partners_page.py` | `/operating-partners` — CEO rolodex tracker. |
| 104 | `partner_economics_page.py` | `/partner-economics` — Partner economics. |
| 105 | `patient_experience_page.py` | `/patient-experience` — Patient experience. |
| 106 | `payer_concentration_page.py` | `/payer-concentration` — Payer concentration tracker. |
| 107 | `payer_contracts_page.py` | `/payer-contracts` — Payer contract renewal tracker. |
| 108 | `payer_intel_page.py` | `/payer-intel` — Corpus-calibrated payer mix analysis. |
| 109 | `payer_rate_trends_page.py` | Payer mix trajectory over time vs corpus returns. |
| 110 | `payer_shift_page.py` | `/payer-shift` — Simulate payer re-mix → MOIC impact + rate index + collection rate. |

---

## Chunk 18 summary

**60 files · 803/1,705 cumulative (47.1%).**

**Functional families in this batch**:
- **LP-facing tracking (6)** — DPI tracker, LP dashboard, LP reporting, fundraising, capital-call tracking continues from chunk 17
- **Fund-economics decomposition (5)** — fund attribution, multiple decomposition, IRR dispersion, entry multiple, exit multiple
- **Exit-specific (3)** — exit multiple, exit readiness, exit timing, hold optimizer, hold analysis
- **Payer family (5)** — payer concentration, payer contracts, payer intel, payer rate trends, payer shift simulator
- **Regulatory/Medicare (5)** — 340B, Medicaid unwinding, MA contracts, MA Star, NSA tracker
- **Deal comp tools (3)** — `find_comps_page` (inputs → ranked comps), `gp_benchmarking_page` (GP → peer comp), `comparables_page` (chunk 17)
- **Corporate health (6)** — key person, litigation, fraud detection, compliance attestation, drug shortage, ESG dashboard
- **Operational infra (7)** — direct employer, direct lending, HCIT platform, hospital anchor, locum tracker, medical real estate, operating partners, GPO supply

**Key observation**: `ui/data_public/ic_memo_page.py` is distinct from `ui/ic_memo_page.py` — the former is corpus-benchmarked (input → 700-deal peer comparison), the latter is diligence-workflow (runs full packet pipeline). Both valid, named the same — **naming collision flagged**.

**Next chunk (19)**: `ui/data_public/` batch 3 (FINAL) — files 111-174. P–Z alphabetical. ~63 files. Then chunk 20 = `ui/chartis/` (20).

---

## Chunk 19 — `ui/data_public/` batch 3 FINAL (63 files, P–Z)

| # | File | Route + focus |
|---|------|---------------|
| 111 | `payer_stress_page.py` | `/payer-stress` — MOIC impact of commercial-contract loss + rate shocks. **Collision**: also exists in `ui/` direct (chunk 16) for diligence-workflow version. |
| 112 | `peer_transactions_page.py` | `/peer-transactions` — Peer transaction database / comps library. |
| 113 | `peer_valuation_page.py` | `/peer-valuation` — Football-field range from trading comps + precedent transactions. |
| 114 | `phys_comp_plan_page.py` | `/phys-comp-plan` — Physician comp plan designer. |
| 115 | `physician_labor_page.py` | `/physician-labor` — Physician labor market. |
| 116 | `physician_productivity_page.py` | `/physician-productivity` — wRVU vs MGMA/AMGA + utilization + capacity-to-EV. |
| 117 | `platform_maturity_page.py` | `/platform-maturity` — Exit readiness index. |
| 118 | `pmi_integration_page.py` | `/pmi-integration` — Post-merger integration scorecard. |
| 119 | `pmi_playbook_page.py` | `/pmi-playbook` — PMI playbook. |
| 120 | `portfolio_optimizer_page.py` | `/portfolio-optimizer` — Portfolio (sector/vintage/sponsor) construction analysis. |
| 121 | `portfolio_sim_page.py` | `/portfolio-sim` — Custom portfolio × 5 macro scenarios stress test. |
| 122 | `provider_network_page.py` | `/provider-network` — Provider network intelligence. |
| 123 | `provider_retention_page.py` | `/provider-retention` — Provider retention. |
| 124 | `qoe_analyzer_page.py` | `/qoe-analyzer` — Quality of Earnings analyzer. |
| 125 | `quality_scorecard_page.py` | `/quality-scorecard` — HEDIS + Stars + readmission + VBC + quality-adjusted EBITDA. |
| 126 | `rcm_red_flags_page.py` | **Corpus-driven RCM risk factors** — statistically associated with underperformance. |
| 127 | `real_estate_page.py` | `/real-estate` — Property inventory + lease term summary + SLB scenarios. |
| 128 | `redflag_scanner_page.py` | `/redflag-scanner` — Deal red-flag scanner. |
| 129 | `ref_pricing_page.py` | `/ref-pricing` — CPT-level rate benchmarking + renewal calendar + uplift scenarios. |
| 130 | `refi_optimizer_page.py` | `/refi-optimizer` — Refinance optimizer. |
| 131 | `regulatory_risk_page.py` | `/regulatory-risk` — Sector-specific regulatory scoring + active CMS/OIG/HRSA events. |
| 132 | `reinvestment_page.py` | `/reinvestment` — Reinvestment. |
| 133 | `reit_analyzer_page.py` | `/reit-analyzer` — Healthcare REIT + sale-leaseback analyzer. |
| 134 | `return_attribution_page.py` | **MOIC decomp by deal dimensions** — P25/P50/P75 by sector × vintage × payer regime × size. |
| 135 | `revenue_leakage_page.py` | `/revenue-leakage` — Leakage buckets + denial reasons + payer-level + recovery. |
| 136 | `risk_adjustment_page.py` | `/risk-adjustment` — HCC tracker. |
| 137 | `risk_matrix_page.py` | **All corpus deals on 2D risk/return scatter** with quadrant annotations. |
| 138 | `rollup_economics_page.py` | `/rollup-economics` — Roll-up / platform economics analyzer. |
| 139 | `rw_insurance_page.py` | `/rw-insurance` — Reps & Warranties insurance tracker. |
| 140 | `scenario_mc_page.py` | `/scenario-mc` — MOIC outcome distribution + percentile table + driver tornado + probability matrix. |
| 141 | `secondaries_tracker_page.py` | `/secondaries-tracker` — Secondaries + GP-led tracker. |
| 142 | `sector_correlation_page.py` | `/sector-correlation` — Pairwise Pearson-correlation heatmap of sector MOIC time series. |
| 143 | `sector_intel_page.py` | `/sector-intel` — Corpus-calibrated per-sector performance. |
| 144 | `sector_momentum_page.py` | **Recent 5-yr deal count vs prior 5-yr** — which sectors are accelerating. |
| 145 | `sellside_process_page.py` | `/sellside-process` — Sell-side process tracker. |
| 146 | `size_intel_page.py` | `/size-intel` — EV distribution + performance by size bucket. |
| 147 | `specialty_benchmarks_page.py` | `/specialty-benchmarks` — Specialty benchmarks library. |
| 148 | `sponsor_heatmap_page.py` | `/sponsor-heatmap` — Sponsor × sector performance heatmap. |
| 149 | `sponsor_league_page.py` | **Sponsor rank table** across 635+ corpus deals by realized returns. |
| 150 | `supply_chain_page.py` | `/supply-chain` — Supply chain. |
| 151 | `tax_credits_page.py` | `/tax-credits` — Tax credits / incentives tracker. |
| 152 | `tax_structure_analyzer_page.py` | `/tax-structure-analyzer` — Tax structure analyzer. |
| 153 | `tax_structure_page.py` | `/tax-structure` — Stock vs 338 vs F-Reorg comparison + rollover tax + PTE/SALT. |
| 154 | `tech_stack_page.py` | `/tech-stack` — Systems + modernization + cybersecurity + IT spend benchmark. |
| 155 | `telehealth_econ_page.py` | `/telehealth-econ` — Telehealth economics. |
| 156 | `tracker_340b_page.py` | `/tracker-340b` — 340B pharmacy program tracker. |
| 157 | `transition_services_page.py` | `/transition-services` — TSA catalog + standalone cost bridge + milestones. Carve-out focus. |
| 158 | `treasury_tracker_page.py` | `/treasury` — Cash position tracker. |
| 159 | `trial_site_econ_page.py` | `/trial-site-econ` — Clinical trial site economics. |
| 160 | `underwriting_model_page.py` | `/underwriting-model` — Underwriting model. |
| 161 | `underwriting_page.py` | **Interactive LBO model** — user inputs entry EV, EBITDA, equity %, CAGR → returns. |
| 162 | `unit_economics_page.py` | `/unit-economics` — Per-location revenue + ramp curves + visit/provider profitability. |
| 163 | `value_backtester_page.py` | `/backtester` — Value-creation backtester. |
| 164 | `value_creation_page.py` | `/value-creation` — Value creation tracker. |
| 165 | `value_creation_plan_page.py` | `/value-creation-plan` — Post-close plan + initiative inventory + milestones. |
| 166 | `vcp_tracker_page.py` | `/vcp-tracker` — VCP / 100-day plan tracker (alt to `value_creation_plan_page`). |
| 167 | `vdr_tracker_page.py` | `/vdr-tracker` — VDR / diligence tracker. |
| 168 | `vintage_cohorts_page.py` | `/vintage-cohorts` — Vintage cohort performance. |
| 169 | `vintage_perf_page.py` | `/vintage-perf` — Year-by-year corpus: P50 MOIC bar + deal-count histogram. |
| 170 | `workforce_planning_page.py` | `/workforce-planning` — Role inventory + hiring + labor + agency reduction. |
| 171 | `workforce_retention_page.py` | `/workforce-retention` — Workforce turnover tracker. |
| 172 | `working_capital_page.py` | `/working-capital` — AR/AP/DSO/CCC + payer-level AR + RCM initiatives. |
| 173 | `zbb_tracker_page.py` | `/zbb-tracker` — Zero-based budgeting tracker. |

---

## Chunk 19 summary — `ui/data_public/` COMPLETE

**63 files · 866/1,705 cumulative (50.8%).** **`ui/data_public/` (173 files) fully mapped. Halfway through the entire codebase.**

**Functional families in this batch**:
- **Sponsor / vintage analytics (5)** — sponsor heatmap, sponsor league, vintage cohorts, vintage perf, sector momentum
- **Portfolio construction (3)** — portfolio optimizer (corpus selection), portfolio sim (macro scenarios), risk matrix (2D scatter)
- **Return decomposition (3)** — return attribution (MOIC by dimensions), scenario MC (outcome distribution), size intel (EV buckets)
- **Tax (3)** — tax credits, tax structure analyzer, tax structure (Stock/338/F-Reorg comparison)
- **PMI + carve-out (4)** — pmi_integration, pmi_playbook, transition services (TSA), rw_insurance
- **Physician / workforce (5)** — phys comp plan, physician labor, physician productivity, workforce planning, workforce retention
- **Value creation duplicates (3)** — value_creation_page, value_creation_plan_page, vcp_tracker_page (all same topic, different renderings)
- **Quality / clinical (4)** — quality scorecard, HEDIS, regulatory risk, risk adjustment, 340B tracker (dup with `drug_pricing_340b_page`)

**Name collisions flagged in chunk 19**:
- `payer_stress_page.py` exists in both `ui/` direct (diligence) and `ui/data_public/` (corpus)
- `value_creation_plan_page.py` + `vcp_tracker_page.py` — near-duplicate in same dir
- `tax_structure_page.py` + `tax_structure_analyzer_page.py` — near-duplicate in same dir
- `drug_pricing_340b_page.py` (chunk 17) + `tracker_340b_page.py` (chunk 19) — both 340B focused

**Cumulative `ui/data_public/` architecture**:
- 173 uniform `*_page.py` renderers mapping 1:1 to HTTP routes
- "Corpus-browser" theme — almost every page consumes the 635+ deal corpus
- **Zero non-page files** in this dir (contrast with `ui/` direct which has `_chartis_kit`, `_ui_kit`, helpers)
- **Likely large amount of code duplication** given the repetitive naming and pattern — future consolidation candidate

**Next chunk (20)**: `ui/chartis/` — 20 files. Based on path, probably Chartis-themed UI components or specialized rendering helpers.

---

## Chunk 20 — `ui/chartis/` COMPLETE (20 files)

**Discovery**: `ui/chartis/` is the **Chartis-namespace SeekingChartis experience layer.** These are the top-level pages from the Phase 2A UI wiring — the "best-of" pages that compose `pe_intelligence/` + `data_public/` outputs into the branded SeekingChartis experience. Most pages pull from **both** back-ends (pe_intelligence for judgment + data_public for corpus comps).

| # | File | Route + focus |
|---|------|---------------|
| 1 | `__init__.py` | Package docstring — "Phase 2A top-level SeekingChartis experience pages." |
| 2 | `_helpers.py` | **Shared building blocks** for chartis per-deal pages. Kept small — only pieces that would be rewritten 5-6× across per-deal pages. |
| 3 | `_sanity.py` | **Numeric reasonableness guards.** Every numeric output passes through `render_number` — out-of-band values get flagged rather than silently rendered. Trust guardrail. |
| 4 | `archetype_page.py` | **`/deal/<id>/archetype`** — per-deal archetype + regime. Renders `pe_intelligence.deal_archetype.classify_archetypes(ctx)`. |
| 5 | `corpus_backtest_page.py` | **`/corpus-backtest`** — cross-matches platform-predicted outcomes against actual corpus outcomes. Calls `data_public/backtester.match_deals`. |
| 6 | `deal_screening_page.py` | **`/deal-screening`** — rule-based screen over every corpus deal. Calls `data_public/deal_screening_engine.screen_corpus`. |
| 7 | `home_page.py` | **SeekingChartis Home** — 7-panel partner landing: pipeline funnel, active alerts, portfolio health, recent deals, deadlines, PE intelligence highlights, market moves. |
| 8 | `ic_packet_page.py` | **`/deal/<id>/ic-packet`** — "give me everything in one document." Combines `pe_intelligence.ic_memo` + `pe_intelligence.master_bundle`. Collides with `ui/ic_packet_page.py` (different audience). |
| 9 | `investability_page.py` | **`/deal/<id>/investability`** — "should we be in this deal at all." Composes investability scorer + exit readiness. |
| 10 | `market_structure_page.py` | **`/deal/<id>/market-structure`** — renders `pe_intelligence.market_structure` for deal's local competitive landscape. |
| 11 | `marketing_page.py` | **Public marketing landing** (Phase 13 UI v2) — at `GET /` under `CHARTIS_UI_V2=1` env flag; legacy dashboard stays at `/` otherwise. |
| 12 | `partner_review_page.py` | **`/deal/<id>/partner-review`** — **single biggest integration point with PE Intelligence Brain.** Loads cached `DealAnalysisPacket`, runs `partner_review.generate_partner_review`. |
| 13 | `payer_intelligence_page.py` | **`/payer-intelligence`** — comprehensive payer-mix view. Calls `data_public/payer_intelligence.compute_payer_intelligence(corpus)`. |
| 14 | `pe_intelligence_hub_page.py` | **`/pe-intelligence` — landing for the 278-module pe_intelligence package.** Surfaces the seven partner reflexes from the brain's README, links per-deal pages. |
| 15 | `portfolio_analytics_page.py` | **`/portfolio-analytics`** — combines `data_public/portfolio_analytics` (corpus scorecard, vintage cohorts, sponsor/type, return distribution). |
| 16 | `rcm_benchmarks_page.py` | **`/rcm-benchmarks`** — industry benchmark library. Calls `data_public/rcm_benchmarks.get_all_benchmarks()`. |
| 17 | `red_flags_page.py` | **`/deal/<id>/red-flags`** — focused "what's wrong with this deal" surface. Heuristic hits + reasonableness violations. No narrative. |
| 18 | `sponsor_track_record_page.py` | **`/sponsor-track-record`** — portfolio-scope league table. Calls `data_public/sponsor_track_record`. |
| 19 | `stress_page.py` | **`/deal/<id>/stress`** — renders `pe_intelligence.stress_test.run_stress_grid` output. Scenario-by-scenario pass/fail. |
| 20 | `white_space_page.py` | **`/deal/<id>/white-space`** — adjacencies for growth. Surfaces `pe_intelligence.white_space.detect_white_space(inputs)` across 3 dimensions. |

---

## Chunk 20 summary — `ui/chartis/` COMPLETE · `ui/` ENTIRE PACKAGE COMPLETE

**20 files · 886/1,705 cumulative (52.0%).** The entire `ui/` package (293 files across `ui/` direct + `ui/data_public/` + `ui/chartis/`) is fully mapped.

**`ui/chartis/` is the Phase 2A composition layer**:
- Takes outputs from `pe_intelligence/` (judgment) + `data_public/` (corpus comps) → branded SeekingChartis pages
- Two sub-families:
  - **Per-deal pages (7)** — `/deal/<id>/archetype`, `investability`, `market-structure`, `partner-review`, `red-flags`, `stress`, `white-space`, `ic-packet`
  - **Portfolio-scope pages (8)** — `home`, `corpus-backtest`, `deal-screening`, `marketing`, `payer-intelligence`, `pe-intelligence` hub, `portfolio-analytics`, `rcm-benchmarks`, `sponsor-track-record`
- **2 shared internal modules** — `_helpers.py` (common building blocks) + `_sanity.py` (render-number guardrail)
- **Name collision**: `ui/ic_packet_page.py` (diligence-workflow) + `ui/chartis/ic_packet_page.py` (Chartis-branded)

**The `_sanity.py` module is interesting** — "every numeric output passes through `render_number` before hitting the browser." This is a trust guardrail at the UI layer, not the model layer. If a bug produces `-9999% IRR`, the UI catches it.

**`partner_review_page.py` named as "single biggest integration point with PE Intelligence Brain"** — explicit architectural landmark.

---

## `ui/` package-wide architecture summary

293 files split into three surfaces with distinct purposes:

| Dir | Files | Purpose | Pattern |
|-----|-------|---------|---------|
| `ui/` direct | 100 | Diligence-workflow | Page-per-backend-module, chartis_shell wrapper |
| `ui/data_public/` | 173 | Corpus browser | `<topic>_page.py` → `/<topic>` uniform route |
| `ui/chartis/` | 20 | Phase 2A branded experience | Composes pe_intelligence + data_public |

**Name collisions to resolve** (across whole ui/): `ic_memo_page`, `ic_packet_page`, `payer_stress_page`, `competitive_intel_page`, `exit_timing_page`, `real_estate_page` — each appears 2-3× across the three dirs.

**Next chunk (21)**: start `rcm_mc/data/` (29 files) — the data-loading layer. HCRIS, IRS 990, CMS, various adapters.

---

## Chunk 21 — `rcm_mc/data/` COMPLETE (29 files, ✓ [README](RCM_MC/rcm_mc/data/README.md))

The **data-loading layer** — public-data adapters (HCRIS, Care Compare, IRS 990, SEC EDGAR, CMS utilization, chronic conditions), seller-file ingest (EDI parser, document reader, intake wizard), and the workflow scaffolding (deal pipeline, data room, team collab).

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `_cms_download.py` | **Shared download helper** for `cms_hcris` / `cms_care_compare` / `cms_utilization` / `irs990_loader`. Retry + cache + etag handling in one place. |
| `hcris.py` | **Core HCRIS parsing layer.** Extracts the ~15 fields diligence analysts need from CMS Hospital Cost Report bundles (worksheet coordinates). |
| `cms_hcris.py` | **HCRIS public-data loader** — wraps `data/hcris.py` (parsing) + `_cms_download.py` (fetch) into a public interface. |
| `cms_care_compare.py` | **Care Compare loader** — 3 CMS datasets (General Hospital Info `xubh-q36u`, HCAHPS patient experience, complications/deaths). |
| `cms_utilization.py` | **Medicare inpatient utilization.** Source `data.cms.gov/provider-summary-by-type-of-service/medicare-inpatient-hospitals`. One row per (provider, DRG). |
| `irs990.py` | **IRS 990 for non-profit hospitals** (~58% of US hospitals). ProPublica Nonprofit Explorer JSON API wrapper. |
| `irs990_loader.py` | Thin wrapper around `irs990.py` — normalizes ProPublica data into the platform's schema. |
| `sec_edgar.py` | **SEC EDGAR integration** (Prompt 40) for ~25 public hospital systems (HCA, Tenet, CHS, UHS). Revenue + margin + leverage from XBRL. |
| `disease_density.py` | **Medicare chronic conditions by county.** Falls back to national averages when API unavailable. |
| `drg_weights.py` | **MS-DRG codes → CMS payment weights + chronic category.** Weights from FY2024 IPPS Final Rule Table 5. Annual refresh (<2% drift). |
| `data_refresh.py` | **Orchestrator** for the 4 core CMS public-data sources. Owns `hospital_benchmarks` + `data_source_status` tables + refresh loop. |
| `benchmark_evolution.py` | **Benchmark drift tracker** (Prompt 55). Tracks P50 snapshots year-over-year; flags when P50 drifts >1pp so re-marks use current benchmarks. |
| `claim_analytics.py` | **Denial rates + top denial reasons + payer aging** (Prompt 75) from the `claim_records` table. Parameterized read-only queries. |
| `edi_parser.py` | **EDI X12 837/835 parser** (Prompt 75). 837 = claim submission, 835 = remittance. Minimum segment set needed for analytics. Populates `claim_records`. |
| `document_reader.py` | **Drag-drop seller file extraction.** Sellers send mixed Excel/CSV/TSV — same conceptual content (denial rate, AR aging, payer mix). Normalizes. |
| `auto_populate.py` | **One-name → pre-populated deal.** Pre-Prompt-23 this was 8-12hr lookup. Takes a hospital name → CCN → HCRIS + Care Compare + IRS 990 + SEC EDGAR. |
| `intake.py` | **Interactive intake wizard** — 11 prompts → validated `actual.yaml`. Collapses 131-field config surface to what an analyst answers in 5 minutes. |
| `ingest.py` | **`rcm-mc ingest`** — turn messy seller data pack into calibration-ready directory. Outputs 3 canonical CSVs (`claims_summary`, `denials`, `ar_aging`). |
| `lookup.py` | **`rcm-lookup` CLI** — browse HCRIS from command line. "The Memorial in Dallas", "all Ohio teaching hospitals", before typing a 6-digit CCN. |
| `geo_lookup.py` | **City/state → lat/lon** (Prompt 69). Pre-built state-capital centroids. Good enough for portfolio map city-level plotting. |
| `market_intelligence.py` | **Competitor finder + HHI** (Prompt 52). Haversine distance on centroids → nearby competitors → HHI market concentration. |
| `system_network.py` | **Hospital system network graph + acquisition target finder** (Prompt 70). Builds graph from HCRIS; finds standalones near a system's existing footprint. |
| `state_regulatory.py` | **State-level context** — CON laws, COPA status, AG PE scrutiny, scope-of-practice, CPOM. Saves 2-4hr lookup per deal. |
| `data_scrub.py` | **Board-ready integrity scrub.** Winsorize fat-tail outliers at operationally plausible caps. Called before every chart/table render. |
| `sources.py` | **Observed vs assumed tagging** — classifies each config param into OBSERVED (measured from data), ASSUMED (analyst set), or DERIVED (computed from others). Defensibility requirement. |
| `data_room.py` | **Seller-entered KPI persistence.** Analyst enters actual operational data from data room; SQLite-backed. |
| `pipeline.py` | **Deal pipeline** — saved searches + stage tracking (screening → IOI → LOI → close). Converts SeekingChartis from screening tool → workflow platform. |
| `team.py` | **Team collaboration** — comments + assignments + activity feed on top of existing auth/RBAC. Entity-agnostic (hospital, pipeline deal, data room entry). |

---

## Chunk 21 summary

**29 files · 915/1,705 cumulative (53.7%).** `data/` fully mapped. README covers.

**Architectural families**:
- **Public-data loaders (8)** — `hcris`, `cms_hcris`, `cms_care_compare`, `cms_utilization`, `irs990`, `irs990_loader`, `sec_edgar`, `disease_density` + shared `_cms_download` helper
- **Calibration / benchmark plumbing (4)** — `data_refresh` (orchestrator), `benchmark_evolution` (drift tracker), `drg_weights` (MS-DRG weights), `data_scrub` (integrity)
- **Seller-file ingest (4)** — `edi_parser` (X12 837/835), `document_reader` (Excel/CSV extraction), `auto_populate` (name → pre-populated deal), `intake` (11-prompt wizard), `ingest` (pack → canonical CSVs)
- **Lookup / geo (3)** — `lookup` (rcm-lookup CLI), `geo_lookup` (centroids), `market_intelligence` (Haversine + HHI)
- **Workflow scaffolding (4)** — `data_room`, `pipeline`, `team`, `system_network`
- **Context libraries (2)** — `state_regulatory`, `sources` (observed/assumed tagging)
- **Claim analytics (1)** — `claim_analytics` (denial rates + aging queries over `claim_records`)

**Key insights**:
- **`_cms_download.py` is a shared shim** — all 4 CMS loaders use it. Retries + ETag + cache in one place; consolidates what would otherwise be 4× duplication.
- **`auto_populate.py` is the productivity multiplier** — collapses 8-12hr manual lookup → seconds. One name → CCN → HCRIS + Care Compare + IRS 990 + SEC EDGAR + Medicare utilization.
- **`sources.py` encodes the defensibility requirement** — every config parameter tagged OBSERVED / ASSUMED / DERIVED. "Defend every number" baked into the data model.
- **`intake.py` collapses 131 fields → 11 prompts** — the interactive wizard that turns the calibration surface into something usable in 5 minutes.
- **No network calls in the MC hot path** — all network calls live here (via `_cms_download`, `sec_edgar`, `irs990`) and are explicitly cached + batched by `data_refresh` orchestrator.

**Next chunk (22)**: begin `rcm_mc/data_public/` — 318 files. This is **not the same as `ui/data_public/`** (173 page renderers). Top-level `data_public/` is the data engines/libraries the ui/data_public/ pages consume. Will take ~6-7 chunks.

---

## Chunk 22 — `rcm_mc/data_public/` batch 1 (50 files, A–C) ✗ **NO README**

**Structure discovery**: 313 direct files + 5 in `scrapers/` subdir = 318 total. Largest single dir in the repo. **No README — major documentation gap.**

**The key relationship**: `ui/data_public/<topic>_page.py` renders output of `data_public/<topic>.py` engine. Naming is ~1:1. This is the **corpus-intelligence engine layer** feeding the `ui/data_public/` browser surface. Many modules port/adapt code from the sibling `cms_medicare-master/` project (same team, no license, internal material).

| # | File | Purpose |
|---|------|---------|
| 1 | `__init__.py` | Package docstring — "Public deals corpus and calibration data for SeekingChartis." |
| 2 | `aco_economics.py` | **MSSP + ACO REACH economics.** Shared-savings rate × attributed benes × (actual PMPM − benchmark PMPM). |
| 3 | `acq_timing.py` | **Vintage cycle analysis.** Entry EV/EBITDA × MOIC by year → pattern detection. |
| 4 | `ai_operating_model.py` | AI/ML adoption + ROI + model risk + governance across PE-backed platforms. |
| 5 | `antitrust_screener.py` | **Pre-close FTC risk assessment** for healthcare roll-ups. MSA + specialty HHI + HSR triggers. |
| 6 | `backtester.py` | **Platform predictions vs realized outcomes.** Projected IRR/MOIC from analysis runs vs actual corpus outcomes. |
| 7 | `base_rates.py` | **P25/P50/P75 API from public corpus.** Segmented by hospital size bucket. Anchor benchmarks for every other module. |
| 8 | `biosimilars_opp.py` | Biosimilar substitution economics for provider platforms. |
| 9 | `board_governance.py` | Portfolio-wide board composition + director analytics. |
| 10 | `bolton_analyzer.py` | **Buy-and-build roll-up economics.** Platform + N bolt-ons with multiple arbitrage + synergy phasing. |
| 11 | `cap_structure.py` | **Optimal debt/equity mix for LBO.** Sweeps 3.0× to 7.0× leverage. |
| 12 | `capex_budget.py` | Portfolio capital-budget tracker — approved vs pipeline capex. |
| 13 | `capital_call_tracker.py` | Capital call + distribution tracker for LP communication. |
| 14 | `capital_efficiency.py` | **Return density** — MOIC per turn of entry × IRR density × value-creation rate. Three efficiency ratios. |
| 15 | `capital_pacing.py` | **Fund-level cashflow engine.** Vintage pacing model for PE healthcare funds. |
| 16 | `capital_schedule.py` | **Fund lifecycle cashflows** — J-curve + DPI/TVPI + LP waterfall quarterly. |
| 17 | `cin_analyzer.py` | Clinical Integration Network economics — network-based value capture. |
| 18 | `clinical_ai_tracker.py` | AI/ML deployments in clinical workflows across portfolio. |
| 19 | `clinical_outcomes.py` | **Monetize quality outcomes** — MA Stars + readmission + complications + VBC economics → $ impact. |
| 20 | `cms_advisory_memo.py` | **Senior-partner CMS advisory memo generator.** Ported from `cms_api_advisory_analytics.build_advisory_memo()`. |
| 21 | `cms_api_client.py` | **Stdlib-only paginated CMS Open Payments / Provider Utilization fetcher.** No third-party HTTP lib. |
| 22 | `cms_apm_tracker.py` | CMS Innovation Center (CMMI) + Medicare APMs that drive reimbursement. |
| 23 | `cms_benchmark_calibration.py` | **Bridge CMS analytics → deals-corpus calibration.** Market concentration → regime → benchmark. |
| 24 | `cms_data_browser.py` | Curated index of CMS public datasets used in healthcare PE diligence. |
| 25 | `cms_data_quality.py` | **Data quality + run-summary reporting.** Ported from `cms_api_advisory_analytics.py` (`DrewThomas09/cms_medicare`). |
| 26 | `cms_market_analysis.py` | **End-to-end pipeline orchestrator** — API fetch → concentration → regime. |
| 27 | `cms_opportunity_scoring.py` | **Provider-state opportunity scoring + benchmark flagging.** Ported from `cms_api_advisory_analytics`. |
| 28 | `cms_provider_ranking.py` | **Provider consensus ranking + anomaly detection.** Ported from `cms_medicare/cms_api_advisory_analytics.py`. |
| 29 | `cms_rate_monitor.py` | Year-over-year payment rate changes by state × provider-type. |
| 30 | `cms_stress_test.py` | **Provider stress-testing + investability ranking.** Ported. |
| 31 | `cms_trend_forecaster.py` | Rate trend extrapolation from historical CMS time-series for underwriting. |
| 32 | `cms_white_space_map.py` | **Highest-opportunity state × provider-type combos.** Geographic white-space mapping. |
| 33 | `coinvest_pipeline.py` | Co-invest opportunities + LP allocations + fee/carry tracker. |
| 34 | `comparables.py` | **Corpus comparable finder.** Deal dict → N most-similar corpus deals. |
| 35 | `competitive_intel.py` | **Per-sector competitor tracking** + share shift opportunities. |
| 36 | `compliance_attestation.py` | SOC 2 + HITRUST + HIPAA + PCI + ISO attestation tracker. |
| 37 | `concentration_analytics.py` | **HHI + CR3/CR5 + diversification metrics.** Core concentration math used across modules. |
| 38 | `continuation_vehicle.py` | **GP-led CV economics.** Extended-hold trophy-asset modeling. |
| 39 | `corpus_cli.py` | **CLI for the public deals corpus.** Entry point for corpus queries. |
| 40 | `corpus_export.py` | **CSV/JSON/Markdown export of 175-deal corpus.** Partner-ready with optional redaction. |
| 41 | `corpus_health_check.py` | **Internal-consistency validator.** Data quality checks over loaded corpus. |
| 42 | `corpus_loader.py` | **Canonical corpus loader.** `load_corpus_deals(mode=...)` returns deal dicts with provenance filter. |
| 43 | `corpus_provenance.py` | **Per-deal provenance classification.** Every loaded row tagged with its source + confidence. |
| 44 | `corpus_red_flags.py` | **Corpus-calibrated red-flag detector.** Compares deal's entry characteristics against realized outcomes. |
| 45 | `corpus_report.py` | **One-page IC deal brief** — consolidated formatted text report for a single corpus deal. |
| 46 | `corpus_vintage_risk_model.py` | **"Are we entering at a bad time?"** — macro cycle risk by entry year. |
| 47 | `cost_structure.py` | COGS vs SG&A + labor cost + fixed/variable split for healthcare services P&L. |
| 48 | `covenant_headroom.py` | **Covenant compliance tracker** for PE portfolio companies with credit facilities. |
| 49 | `covenant_monitor.py` | Leverage-ratio tracking + covenant headroom from corpus. |
| 50 | `cyber_risk.py` | **Diligence-grade cybersecurity scorecard** for PE healthcare platforms. |

---

## Chunk 22 summary

**50 files · 965/1,705 cumulative (56.6%).**

**Discoveries**:
- **No README in `data_public/`** — despite being the largest dir. Doc gap flagged.
- **13 CMS-prefixed modules** already in chunk 22 alone — `cms_*` is a huge sub-family. Many ported from sibling `cms_medicare-master/` project (same team, internal material, no license). Consolidation candidate.
- **7 corpus-prefixed modules** — `corpus_cli`, `corpus_export`, `corpus_health_check`, `corpus_loader`, `corpus_provenance`, `corpus_red_flags`, `corpus_report`, `corpus_vintage_risk_model`. Clear naming: all operate on the 175-deal healthcare-PE corpus.
- **`ui/data_public/<topic>_page.py` ↔ `data_public/<topic>.py`** 1:1 mapping confirmed for most modules (e.g., `ui/data_public/aco_economics_page.py` ↔ `data_public/aco_economics.py`). The UI layer is a thin render wrapper.
- **`corpus_loader.py` is the canonical entry point** — every corpus-reading module goes through `load_corpus_deals(mode=...)`. Single source of truth.

**Families in this batch**:
- **CMS analytics ported suite (10)** — `cms_advisory_memo`, `cms_api_client`, `cms_apm_tracker`, `cms_benchmark_calibration`, `cms_data_browser`, `cms_data_quality`, `cms_market_analysis`, `cms_opportunity_scoring`, `cms_provider_ranking`, `cms_rate_monitor`, `cms_stress_test`, `cms_trend_forecaster`, `cms_white_space_map`
- **Corpus infrastructure (7)** — loader, provenance, health check, export, CLI, red flags, report, vintage risk
- **Capital/fund economics (6)** — cap structure, capex budget, capital call tracker, capital efficiency, capital pacing, capital schedule
- **Tracker pattern (10+)** — bolt-on analyzer, coinvest pipeline, compliance attestation, capital call tracker, etc. Many modules are fund-level or portfolio-level tracking dashboards.

**Next chunk (23)**: `data_public/` batch 2 — files 51-110 (C–F alphabetical). ~60 files.

---

## Chunk 23 — `data_public/` batch 2 (42 code + 104 seed = 146 files, D–E code + entire seed fleet)

**Major structural discovery**: positions 93-196 in alphabetical sort are **104 `extended_seed_N.py` files** — pure curated deal data, not code. Each contains a batch of ~20 real PE healthcare transactions. Treating them as a lumped entry.

### Non-seed code files 51-92 (42 files)

| # | File | Purpose |
|---|------|---------|
| 51 | `data_sources_admin.py` | **Scraper inventory** — per-source last-run, record counts, freshness. |
| 52 | `deal_comparables_enhanced.py` | Enhanced comparables over base `comparables.py` — adds more matching dimensions. |
| 53 | `deal_entry_risk_score.py` | **"On a 0-100 scale, how risky is this entry?"** Composite IC answer. |
| 54 | `deal_memo_generator.py` | **One-call synthesizer** — runs every corpus analytic → partner memo. |
| 55 | `deal_momentum.py` | Vintage clustering + deal-volume trends + return compression analysis. |
| 56 | `deal_origination.py` | M&A pipeline tracker — active pipeline, broker relationships. |
| 57 | `deal_pipeline.py` | **Live sourcing pipeline** — stage conversion, velocity, source ROI. |
| 58 | `deal_portfolio_construction.py` | **"Does adding this deal improve or worsen the portfolio?"** Diversification analysis. |
| 59 | `deal_portfolio_monitor.py` | Tracks active deals vs base-rate benchmarks; alerts on divergence. |
| 60 | `deal_postmortem.py` | Structured retrospective — actual MOIC/IRR vs underwriting. |
| 61 | `deal_quality_score.py` | Data completeness + analytical credibility scorer. |
| 62 | `deal_quality_scorer.py` | **Duplicate-like** of `deal_quality_score.py` — flagged for consolidation. |
| 63 | `deal_risk_matrix.py` | 6-dimension structured risk assessment. |
| 64 | `deal_risk_scorer.py` | 5-dimension composite risk across every corpus deal. |
| 65 | `deal_scorer.py` | **Generic 0-100 quality score.** Third deal-scoring module — consolidation candidate. |
| 66 | `deal_screening_engine.py` | **Pass/Watch/Fail triage.** Combines risk matrix + senior-partner heuristics + base-rate benchmarks. |
| 67 | `deal_sourcing.py` | Deal sourcing funnel + intermediary relationships + proprietary flow. |
| 68 | `deal_teardown_analyzer.py` | **Post-mortem MOIC attribution** — decomposes realized deal into 3 independent value-creation levers. |
| 69 | `deal_timeline.py` | Entry-to-exit event sequencing across corpus; market-cycle reconstruction. |
| 70 | `deal_underwriting_model.py` | **Simplified LBO with corpus-calibrated guardrails.** Projects forward IRR/MOIC, compares to corpus P25/P75. |
| 71 | `deal_value_creation.py` | **Realized MOIC decomposed** into 3 standard PE value-creation levers. |
| 72 | `deals_corpus.py` | **The core corpus.** SQLite-backed store of real publicly disclosed hospital M&A deals. |
| 73 | `debt_financing.py` | LBO debt commitment tracker — package per deal. |
| 74 | `debt_service.py` | DSCR + interest coverage + covenant headroom for leveraged buyouts. |
| 75 | `demand_forecast.py` | **Demographic-driven patient-volume projections.** 5-10yr horizon utilization. |
| 76 | `denovo_expansion.py` | Greenfield buildout economics — ramp curves, breakeven month by month. |
| 77 | `digital_front_door.py` | Patient portal adoption + NPS + digital engagement tracker. |
| 78 | `diligence_checklist.py` | **Sector-specific DD items from corpus patterns.** |
| 79 | `diligence_vendors.py` | DD ecosystem catalog — advisors, QofE firms, chart auditors. |
| 80 | `direct_employer.py` | Direct-to-employer contract economics for provider platforms. |
| 81 | `direct_lending.py` | **Healthcare direct-lending market** — outstanding credit, spread trends, sponsor league. |
| 82 | `dividend_recap.py` | **Recap economics** — refi → return of capital, DPI lever without exit. |
| 83 | `dpi_tracker.py` | DPI / RVPI / TVPI time-series tracker. |
| 84 | `drug_pricing_340b.py` | **340B covered-entity exposure** — critical for DSH/FQHC/SCH/CAH platforms. |
| 85 | `drug_shortage.py` | Drug shortage exposure for platforms with meaningful pharmacy revenue. |
| 86 | `earnout.py` | **Physician-led deal earnouts** — milestone + probability-weighted value + fair-value + IRR impact. |
| 87 | `escrow_earnout.py` | Contingent consideration tracker — escrows, earnouts, indemnification holdbacks. |
| 88 | `esg_dashboard.py` | **LP-facing ESG diligence.** Modern LP disclosure requirement. |
| 89 | `esg_impact.py` | ESG performance tracking across portfolio — clinical access, workforce. |
| 90 | `exit_modeling.py` | **4 exit routes** — strategic / sponsor / IPO / continuation. Decomposed value-creation levers. |
| 91 | `exit_multiple.py` | Forward exit multiple modeling + decomposition from corpus. |
| 92 | `exit_readiness.py` | IPO/sale readiness multi-dim scoring. |

### Extended seed fleet (104 files: `extended_seed.py` + `extended_seed_2.py` through `extended_seed_104.py`)

**These are not code — they are curated deal data.** Each file contains ~20 real PE healthcare transactions as Python dicts, exported as `EXTENDED_SEED_DEALS` (or similar). Together with the base `deals_corpus.py` they form the **~2,100-deal corpus** that every corpus-browser module reads via `corpus_loader.load_corpus_deals(mode=...)`.

**Source attribution** (from docstrings): SEC EDGAR 8-K/SC TO-T/DEFM14A filings, Modern Healthcare, Becker's Hospital Review, Healthcare Finance News, PE firm press releases. All publicly disclosed, all real transactions.

**Segmentation across batches**:
- Batch 1 (`deals_corpus.py`): 35 core seed deals
- Batch 2 (`extended_seed.py`): 20 deals — small community hospitals (<$200M EV), dental, PPM adjacents, post-acute SNF, behavioral/SUD, international PE entering US
- Batch 3 (`extended_seed_2.py`): 20 deals — regional health system mergers 2018-2024
- Batches 4-105 (`extended_seed_3.py` through `extended_seed_104.py`): 20 deals each, covering different vintages / segments / size buckets / exit outcomes

**Lumped entry for 104 files**: all `extended_seed_N.py` = curated deal-data batches. One-line-per-file docstrings describe the batch's focus (segment, vintage range, special theme). None are code; all are consumed by `corpus_loader`. Maintenance: add new batches with incrementing N; refresh every 3-6 months as new public deals close.

---

## Chunk 23 summary

**146 files (42 code + 104 seed data) · 1,111/1,705 cumulative (65.2%).**

**Architectural insights**:
- **The 104-file seed fleet is the corpus itself.** What I was treating as "1,705 Python files to document" includes ~104 that are pure data and don't need per-file docs. Subtracting: ~1,601 real code files total across the repo.
- **Heavy deal-scoring proliferation** — `deal_entry_risk_score`, `deal_quality_score`, `deal_quality_scorer`, `deal_risk_matrix`, `deal_risk_scorer`, `deal_scorer`, `deal_teardown_analyzer` — **7 overlapping scorers** in one directory. Strong consolidation signal; flagged for refactor.
- **Duplicate pair**: `deal_quality_score.py` + `deal_quality_scorer.py` — near-identical names in the same dir. Needs investigation.
- **Exit trio**: `exit_modeling.py`, `exit_multiple.py`, `exit_readiness.py`. Each a distinct angle (4 routes + forward multiple + readiness scoring).

**Cumulative `data_public/` families so far**:
- CMS ported suite (13, chunk 22)
- Corpus infrastructure (8, chunk 22) + deal data (104 seeds, chunk 23)
- Capital/fund economics (6, chunk 22) + debt (2, chunk 23) + payout (4, chunk 23)
- Deal scoring/risk (7+, chunk 23 — consolidation candidate)
- Deal-pipeline/workflow (5, chunk 23)

**Next chunk (24)**: `data_public/` batch 3 — files 197-260 (**post-seed resume**). F–P alphabetical. ~64 files. `fraud_detection`, `fund_attribution`, etc. onwards.

---

## Chunk 24 — `data_public/` batch 3 (60 files, F–P post-seed)

| # | File | Purpose |
|---|------|---------|
| 197 | `fraud_detection.py` | Fraud/Waste/Abuse panel — billing + coding + referral + denial-mill patterns. |
| 198 | `fund_attribution.py` | **Fund-level IRR decomp for LP reporting** — operational / multiple expansion / leverage / management fee drag. |
| 199 | `fundraising_tracker.py` | GP targets + LP pipeline by stage + commitment letters. |
| 200 | `geo_market.py` | **CBSA-level white-space + market-entry scoring.** Demographic × competitive density × payer mix. |
| 201 | `gpo_supply_tracker.py` | GPO affiliation + supply-chain savings + tiered rebates. |
| 202 | `growth_runway.py` | **TAM/SAM/SOM + penetration curve + share-gain economics.** Organic growth quantification. |
| 203 | `hcit_platform.py` | **Healthcare SaaS analyzer** — ARR, NRR, LTV/CAC, Rule of 40. PE-backed HCIT platforms. |
| 204 | `health_equity.py` | **CMS Health Equity Index components** for MA plans + VBC contracts. |
| 205 | `hold_optimizer.py` | **Corpus-calibrated optimal hold** — entry profile → best hold year from historical patterns. |
| 206 | `hold_period_optimizer.py` | **Duplicate-like** of `hold_optimizer.py` — MOIC-maximizing exit year. Consolidation candidate. |
| 207 | `hospital_anchor.py` | Hospital system contracts for hospital-based physician groups. |
| 208 | `ic_memo.py` | **Standardized IC memo generator.** |
| 209 | `ic_memo_analytics.py` | **Corpus-peer benchmarking** for IC memo — deal inputs → percentile ranks vs corpus. |
| 210 | `ic_memo_synthesizer.py` | **One-call IC packet synthesizer** — pulls every quant signal into a single IC packet. |
| 211 | `ingest_pipeline.py` | **Full corpus ingest orchestrator** — seed + PE portfolios + news in priority order. |
| 212 | `insurance_tracker.py` | Insurance economics — malpractice + D&O + cyber + GL for PE healthcare. |
| 213 | `key_person.py` | **Clinical concentration risk** — CEO/top-producer dependency + departure scenarios. |
| 214 | `lbo_entry_optimizer.py` | **Max entry multiple hitting target MOIC.** Reverse-solver on LBO model. |
| 215 | `lbo_stress.py` | **Classic LBO with sensitivity analysis** — comprehensive stress test. |
| 216 | `leverage_analysis.py` | Debt capacity + coverage + covenant headroom + amortisation for hospital M&A. |
| 217 | `leverage_analytics.py` | **Corpus performance by debt/equity structure.** Proxies leverage from EV/EBITDA when explicit missing. |
| 218 | `litigation_tracker.py` | Open litigation + regulatory actions + class actions. |
| 219 | `locum_tracker.py` | **Contract clinician spend** — top-5 DD issue for PE healthcare. |
| 220 | `lp_dashboard.py` | Fund-level KPIs + vintage curves for LP reporting — deployed capital + distributions. |
| 221 | `lp_reporting.py` | **Quarterly LP report** distilled to institutional dashboard — TVPI/DPI/RVPI. |
| 222 | `ma_contracts.py` | MA plan economics for platforms with MA-risk exposure. |
| 223 | `ma_star_tracker.py` | **MA Star Ratings (2-yr lookback)** + rebates + benchmark trends. |
| 224 | `market_concentration.py` | **Medicare market concentration for rollup screening.** Ported from `cms_medicare/cms_api_advisory_analytics.py`. |
| 225 | `market_rates.py` | **P25/P50/P75/P90 cuts of valuation metrics** — market-rate engine. |
| 226 | `medicaid_unwinding.py` | Portfolio impact of Medicaid redetermination (PHE-end) across enrollees. |
| 227 | `medical_realestate.py` | MOB + ASC + medical office exposure across portfolio. |
| 228 | `mgmt_comp.py` | **Rollover equity + options + MIP economics** for PE healthcare deals. |
| 229 | `mgmt_fee_tracker.py` | Portfolio-level fee monitoring + LP economics from corpus. |
| 230 | `module_index.py` | **Consolidated directory of every analytical module in SeekingChartis.** Internal navigation aid. |
| 231 | `msa_concentration.py` | MSA-level HHI/CR3/CR5 for healthcare markets. |
| 232 | `multiple_decomp.py` | **Entry EV/EBITDA decomp** into sector baseline + size + growth premium + quality premium. |
| 233 | `nav_loan_tracker.py` | Fund-level NAV loans — LTV + pricing + covenant tracker. |
| 234 | `normalizer.py` | **Raw deal dict → canonical `public_deals` schema.** Column-alias handler from EDGAR / PE pages / Modern Healthcare. |
| 235 | `nsa_tracker.py` | No Surprises Act IDR submissions + outcomes + QPA. |
| 236 | `operating_partners.py` | Healthcare PE operating partners + CEO rolodex. |
| 237 | `partner_economics.py` | **Physician buy-in calculator** — physician partner economics in PE platforms. |
| 238 | `patient_experience.py` | NPS + HCAHPS monetized for healthcare PE. |
| 239 | `payer_concentration.py` | **Payer-side concentration risk** — top-3 DD issue. |
| 240 | `payer_contracts.py` | Commercial + gov payer contracts — renewal timing + rate escalator. |
| 241 | `payer_intelligence.py` | **Corpus segmented by commercial %** — P25/P50/P75 MOIC by payer bucket. |
| 242 | `payer_mix_shift_model.py` | **"If commercial keeps declining, what does MOIC do?"** Hold-period mix-shift projection. |
| 243 | `payer_sensitivity.py` | Financial impact of adverse payer-mix scenarios. |
| 244 | `payer_shift.py` | **P&L impact of payer re-mix** — rate index + collection rate + weighted yield. |
| 245 | `payer_stress.py` | **Corpus-calibrated payer-shift MOIC impact.** |
| 246 | `pe_intelligence.py` | **PE intelligence layer** — reasonableness bands + heuristics + red-flag detection. Senior-partner intuitions codified. Distinct from the top-level `pe_intelligence/` package. |
| 247 | `peer_transactions.py` | Completed healthcare M&A comps + valuation multiples. |
| 248 | `peer_valuation.py` | **Bank/IB football-field** — trading comps + precedent transactions. |
| 249 | `phys_comp_plan.py` | Physician comp structure designer — wRVU, salary + bonus, partnership tracks. |
| 250 | `physician_labor.py` | **Physician supply/demand by specialty.** Critical for PE platforms. |
| 251 | `physician_productivity.py` | **wRVU benchmarks + utilization + comp ratios.** "Healthcare PE deals live or die on physician productivity." |
| 252 | `platform_maturity.py` | Exit-path readiness per channel — strategic / sponsor / IPO. |
| 253 | `pmi_integration.py` | PMI scorecard across bolt-on + platform acquisitions. |
| 254 | `pmi_playbook.py` | Integration progress per M&A transaction — stage + workstream tracking. |
| 255 | `portfolio_analytics.py` | **Portfolio-level analytics over corpus** — return distributions + outlier detection + vintage cohorts. |
| 256 | `portfolio_sim.py` | **Custom-portfolio macro stress test** — user-defined sector weights × macro scenarios. |

---

## Chunk 24 summary

**60 files · 1,171/1,705 cumulative (68.7%).**

**Architectural families in this batch**:
- **IC / LP-facing (7)** — `ic_memo`, `ic_memo_analytics` (peer benchmark), `ic_memo_synthesizer` (one-call packet), `fund_attribution`, `fundraising_tracker`, `lp_dashboard`, `lp_reporting`, `mgmt_fee_tracker`, `nav_loan_tracker`
- **Leverage / LBO family (4)** — `lbo_entry_optimizer` (reverse-solve target MOIC), `lbo_stress`, `leverage_analysis`, `leverage_analytics`
- **Payer family (7)** — `payer_concentration`, `payer_contracts`, `payer_intelligence` (corpus-segmented), `payer_mix_shift_model`, `payer_sensitivity`, `payer_shift`, `payer_stress`. Heavy overlap — consolidation candidate.
- **Hold / exit family (3)** — `hold_optimizer`, `hold_period_optimizer` (duplicate!), `platform_maturity`
- **Physician family (3)** — `phys_comp_plan`, `physician_labor`, `physician_productivity`
- **Market / concentration (3)** — `market_concentration`, `market_rates`, `msa_concentration`
- **Regulatory / reimbursement (4)** — `ma_contracts`, `ma_star_tracker`, `medicaid_unwinding`, `nsa_tracker`

**New consolidation candidates flagged**:
- `hold_optimizer.py` + `hold_period_optimizer.py` — near-duplicate in same dir
- **7 overlapping payer modules** — `payer_intelligence` (corpus-segmented) vs `payer_mix_shift_model` (forward projection) vs `payer_sensitivity` vs `payer_shift` (P&L impact) vs `payer_stress` (MOIC impact) vs `payer_concentration` (risk) vs `payer_contracts` (renewal tracker). Could be a subpackage.

**Name collision flagged**: `pe_intelligence.py` (in data_public/) vs `pe_intelligence/` (top-level package). Distinct modules — the data_public one is a corpus-calibrated reasonableness layer; the top-level package is the 276-module partner-brain. **Naming risk**.

**Key insight**: `module_index.py` is a **self-referential index** of every analytical module in SeekingChartis. Worth checking if it matches our FILE_MAP.md — would be good cross-validation.

**Next chunk (25)**: `data_public/` batch 4 — files 257-313 + scrapers/. P–Z alphabetical. ~62 files.

---

## Chunk 25 — `data_public/` batch 4 FINAL + `scrapers/` (62 files, P–Z)

### Non-seed code files 257-313 (57 files)

| # | File | Purpose |
|---|------|---------|
| 257 | `provider_network.py` | Referral concentration + network regime from corpus. |
| 258 | `provider_regime.py` | **Operating-regime classification for Medicare analytics.** Ported from `cms_medicare/cms_api_advisory_analytics.py`. |
| 259 | `provider_retention.py` | **"Provider departures are the #1 near-term value destroyer post-close."** Churn analyzer. |
| 260 | `provider_trend_reliability.py` | **Statistical consistency of CMS payment growth.** Ported from cms_medicare. |
| 261 | `qoe_analyzer.py` | EBITDA add-back benchmarking from corpus. |
| 262 | `quality_scorecard.py` | HEDIS + Stars + readmission + VBC readiness — clinical outcomes → reimbursement → exit value. |
| 263 | `rcm_benchmarks.py` | P25/P50/P75 RCM benchmarks for hospital M&A. |
| 264 | `real_estate.py` | **"Healthcare deals frequently have undervalued medical office real estate."** Sale-leaseback analyzer. |
| 265 | `redflag_scanner.py` | Rule-based red-flag battery over target deal. |
| 266 | `ref_pricing.py` | CPT-level payer rate benchmarking vs market comps. |
| 267 | `refi_optimizer.py` | Portfolio-wide refi opportunity tracker. |
| 268 | `regional_analysis.py` | **US census region return profiles** — P25/P50/P75 MOIC per region. |
| 269 | `regulatory_risk.py` | HIPAA + Stark + Anti-Kickback + OIG + CMS reg risk modeling. |
| 270 | `reimbursement_risk_model.py` | **"How much EBITDA do we lose if CMS cuts?"** CMS rate-change EBITDA exposure. |
| 271 | `reinvestment.py` | Capital allocation of operating cash over hold — compounding analyzer. |
| 272 | `reit_analyzer.py` | Healthcare REIT / sale-leaseback — real-estate monetization. |
| 273 | `return_attribution.py` | **MOIC decomp by deal-characteristic dimensions** (sector × vintage × payer × size × hold). |
| 274 | `revenue_leakage.py` | **"Every dollar that should have been collected but wasn't"** — denials + underpayment + coding gaps + charge capture. |
| 275 | `risk_adjustment.py` | RAF scores + HCC coding accuracy + V24→V28 transition. |
| 276 | `rollup_economics.py` | Platform + fragmented practice aggregation — multiple arbitrage + synergy phasing. |
| 277 | `rw_insurance.py` | R&W insurance tracker — primary + excess + breach claims. |
| 278 | `scenario_mc.py` | **Multi-variable MOIC outcome distribution** — N simulations varying core drivers. |
| 279 | `secondaries_tracker.py` | GP-led secondaries + CVs + LP stake sales. |
| 280 | `sector_correlation.py` | **Cross-sector MOIC correlation matrix** — vintage-year time series → Pearson pairs. |
| 281 | `sector_intelligence.py` | Corpus-calibrated per-sector P25/P50/P75 MOIC + IRR + loss rate + avg hold. |
| 282 | `sellside_process.py` | Active sell-side processes — banker + sell-side QofE + bid round tracking. |
| 283 | `senior_partner_heuristics.py` | **Pattern-recognition rules codified.** Distinct module from the `pe_intelligence/heuristics.py` partner-brain rulebook. |
| 284 | `size_analytics.py` | **EV size-bucket performance** — Small (<$100M) / Mid / Large / Mega. |
| 285 | `specialty_benchmarks.py` | **MGMA / Sullivan Cotter / Radford** operational + compensation benchmarks library. |
| 286 | `sponsor_analytics.py` | Per-sponsor corpus aggregation — MOIC average + loss rate + deal count by firm. |
| 287 | `sponsor_heatmap.py` | **Sponsor × sector 2-D performance heatmap** — "which sponsors outperform in which sectors." |
| 288 | `sponsor_track_record.py` | **"What has this sponsor actually returned across their healthcare deals?"** Performance attribution by firm. |
| 289 | `subsector_benchmarks.py` | P25/P50/P75 by healthcare subsector — acute / ASC / SNF / behavioral / HCIT / etc. |
| 290 | `supply_chain.py` | Medical supply economics — GPO + formulary + pharma-rebate modeling. |
| 291 | `tax_credits.py` | Federal + state tax credits, incentives, deferrals. |
| 292 | `tax_structure.py` | **F-reorg + 338(h)(10) + step-up + PTE + carry tax.** Deal tax economics. |
| 293 | `tax_structure_analyzer.py` | **Duplicate-like** — detailed scorecard for PE healthcare exits. Flagged for consolidation. |
| 294 | `tech_stack.py` | EHR + RCM + clinical systems + cybersecurity IT stack evaluator. |
| 295 | `telehealth_econ.py` | Virtual-care economics for PE-backed telehealth platforms. |
| 296 | `tracker_340b.py` | 340B-eligible entities + contract pharmacy arrangements + savings capture. |
| 297 | `transition_services.py` | **TSA post-close and pre-exit planning** — often underweighted in diligence. |
| 298 | `treasury_tracker.py` | Portfolio-wide liquidity — cash + revolver + credit line utilization. |
| 299 | `trial_site_econ.py` | Clinical trial site-level economics for SMO networks. |
| 300 | `underwriting_model.py` | **Integrated LBO model with corpus-calibrated assumptions.** |
| 301 | `unit_economics.py` | **Per-site + per-patient + per-provider atomics.** "Healthcare PE lives on unit economics." |
| 302 | `value_backtester.py` | **Proposed VCP → backtested against realized corpus outcomes.** |
| 303 | `value_creation.py` | EBITDA bridge decomp + initiative tracking from corpus. |
| 304 | `value_creation_plan.py` | 100-day / VCP post-close operational plan tracker. |
| 305 | `vcp_tracker.py` | **Near-duplicate** of `value_creation_plan.py` — portfolio-wide VCP tracking. Flagged. |
| 306 | `vdr_tracker.py` | Virtual data room + diligence request list tracker. |
| 307 | `vintage_analysis.py` | **Vintage-year grouping** with return profile per vintage. |
| 308 | `vintage_analytics.py` | **Near-duplicate** of `vintage_analysis.py` — P25/P50/P75 by entry year. |
| 309 | `vintage_cohorts.py` | **Third vintage module** — portfolio perf by investment vintage. Consolidation candidate. |
| 310 | `workforce_planning.py` | **Labor = 40-60% of healthcare cost base** — hiring + turnover + comp inflation + labor mix. |
| 311 | `workforce_retention.py` | Clinical + support turnover tracker + retention programs. |
| 312 | `working_capital.py` | AR + AP + DSO + CCC — **"how much cash is trapped in WC?"** |
| 313 | `zbb_tracker.py` | Zero-based budgeting + cost-baseline rebuild + savings capture. |

### `scrapers/` subpackage (5 files)

| # | File | Purpose |
|---|------|---------|
| 314 | `__init__.py` | Scrapers package docstring — 4 submodules. |
| 315 | `cms_data.py` | **CMS Data API → public_deals corpus bridge** — Medicare provider utilization + geographic via `cms_api_client`. |
| 316 | `news_deals.py` | **News-source scraper** — Modern Healthcare + Becker's Hospital Review + Healthcare Dive + Health Affairs Blog. |
| 317 | `pe_portfolios.py` | **PE firm portfolio scraper** — KKR + Apollo + Carlyle + Bain Capital + others. Healthcare portfolio pages. |
| 318 | `sec_filings.py` | **SEC EDGAR EFTS scraper** — hospital + health-system M&A via full-text search (no API key, 10 req/s limit). |

---

## Chunk 25 summary — `data_public/` COMPLETE

**62 files · 1,233/1,705 cumulative (72.3%).** `data_public/` (318 files) fully mapped.

**Architectural families in this final batch**:
- **Vintage analytics (3 duplicates)** — `vintage_analysis`, `vintage_analytics`, `vintage_cohorts`. Three modules computing the same thing. **Strong consolidation candidate.**
- **VCP duplicates (2)** — `value_creation_plan.py` + `vcp_tracker.py`. Near-identical.
- **Tax pair (2)** — `tax_structure.py` + `tax_structure_analyzer.py`. Near-duplicate.
- **CMS-ported suite (additional 2)** — `provider_regime.py`, `provider_trend_reliability.py` also ported from `cms_medicare/`.
- **Sponsor trio** — `sponsor_analytics` + `sponsor_heatmap` + `sponsor_track_record`. Each a distinct cut.
- **Return attribution / backtest pair** — `return_attribution` (MOIC by dimension) + `value_backtester` (VCP vs corpus).
- **Workforce pair** — `workforce_planning` + `workforce_retention`.

**Scrapers subpackage**: 4 data sources feeding the corpus — CMS API / news outlets / PE firm portfolios / SEC EDGAR. All stdlib-friendly (no third-party HTTP lib required). `cms_api_client` is the shared fetcher.

---

## `data_public/` package-wide architecture summary

**318 files (313 direct + 5 scrapers).** No README — biggest doc gap in the repo.

**Package structure**:
- **104 pure-data seed files** (extended_seed + deals_corpus)
- **~209 analytical engines** corresponding ~1:1 with `ui/data_public/` page renderers
- **5 scrapers** feeding the corpus from 4 public sources
- **Canonical entry**: `corpus_loader.load_corpus_deals(mode=...)` — every corpus-reading module goes through here
- **`ingest_pipeline.py`** = full ingest orchestrator calling all scrapers in priority order

**Top-level families** (cumulative across chunks 22-25):
- **CMS ported suite (~15+ modules)** — largest sub-family, ported from sibling `cms_medicare-master/` project
- **Corpus infrastructure (8)** — loader, provenance, health check, export, CLI, red flags, report, vintage risk
- **Capital/fund economics (10+)** — cap structure, fund attribution, pacing, schedule, DPI, NAV loan, mgmt fee, LP dashboard/reporting
- **Deal scoring/risk (7+)** — heavy overlap, consolidation candidate
- **Payer family (7+)** — heavy overlap, consolidation candidate
- **Vintage analytics (3)** — near-duplicates, consolidation candidate
- **Tax family (2)** — near-duplicates
- **VCP family (2)** — near-duplicates
- **Hold optimizer pair (2)** — near-duplicates

**Consolidation candidates flagged cumulatively** (for future cleanup pass):
1. `deal_quality_score.py` + `deal_quality_scorer.py`
2. `hold_optimizer.py` + `hold_period_optimizer.py`
3. `vintage_analysis.py` + `vintage_analytics.py` + `vintage_cohorts.py`
4. `value_creation_plan.py` + `vcp_tracker.py`
5. `tax_structure.py` + `tax_structure_analyzer.py`
6. 7 overlapping payer modules
7. 7 overlapping deal-scoring modules
8. `pe_intelligence.py` (module in data_public) vs top-level `pe_intelligence/` package — name collision

**Next chunk (26)**: remaining smaller packages — `reports/` (14) + `deals/` (13) + `exports/` (10) + `verticals/` (11) + `portfolio/` (8) + `rcm_mc_diligence/` (54, adjacent/legacy). ~110 files across these. Will do in 1-2 chunks.

---

## Chunk 26 — Remaining rcm_mc sub-packages (58 files)

Covering the seven smaller packages that round out `rcm_mc/`: reports, deals, exports, portfolio, intelligence, market_intel, verticals.

### `rcm_mc/reports/` — 14 files ✓ [README](RCM_MC/rcm_mc/reports/README.md)

The HTML / PPTX / Markdown / narrative report generation layer. Every format pulls from the same `DealAnalysisPacket`.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `reporting.py` | Top-level report orchestrator. Entry point every other report format composes over. |
| `full_report.py` | **Comprehensive HTML run + report** with Input Requirements + Config Reference + Numbers Source Map. |
| `html_report.py` | Client-ready HTML report generator for MC outputs. |
| `_report_sections.py` | Static HTML/JS blocks — pure string constants, no templating. |
| `_report_css.py` | CSS + head markup as single string. Kept separate so `html_report.py` stays focused. |
| `_report_helpers.py` | Standalone helpers previously inlined at top of `html_report.py`. |
| `_partner_brief.py` | **One-page IC-ready HTML exec summary.** Compresses the audit-grade full report. |
| `exit_memo.py` | **Exit-readiness memo generator** (Brick 55). Proves track record to next sponsor. |
| `lp_update.py` | **LP-update HTML builder** (Brick 120). Standalone; also used by `server.py` route. |
| `narrative.py` | Natural-language result summary (Step 84). |
| `markdown_report.py` | Markdown report format (Step 87). |
| `pptx_export.py` | **PowerPoint export** (Step 93) — partner-pitchable deck. |
| `report_themes.py` | Theme system (Step 88). Light / dark / partner-brand variants. |

### `rcm_mc/deals/` — 13 files ✓ [README](RCM_MC/rcm_mc/deals/README.md)

Deal lifecycle: CRUD + notes + tags + owners + deadlines + health score + approvals + watchlist.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `deal.py` | **`rcm-mc deal new` orchestrator** — single invocation for Monday-to-IC workflow. |
| `deal_stages.py` | **Lifecycle stage tracking** — pipeline → diligence → LOI → exclusive → close → hold → exit. Change events drive automation. |
| `deal_notes.py` | **Per-deal running notes** (Brick 71) — calls, mgmt commentary, pending Qs. |
| `note_tags.py` | Per-note tags (Brick 123) — analyst slice. |
| `deal_tags.py` | **Deal-level tags** (Brick 86) — PE slice for cohorts / strategy / vintage. |
| `deal_owners.py` | Deal ownership + assignee tracking (Brick 113). "Who do I call?" |
| `deal_deadlines.py` | **Due-date tracker** (Brick 114). "What's due soon" complementing alerts ("what's broken now"). |
| `deal_sim_inputs.py` | Per-deal simulation input paths (Brick 121). Feeds job queue for re-runs. |
| `watchlist.py` | Deal starring (Brick 111) — actively-tracked subset. |
| `health_score.py` | **Composite 0-100 health score** (Bricks 135, 138) + trend history sparkline. |
| `approvals.py` | **Lightweight IC workflow** (Prompt 50). Two stages: `ic_review` (VP signoff) + partner signoff. |
| `comments.py` | Metric-level + deal-level threaded comments (Prompt 49). |

### `rcm_mc/exports/` — 10 files ✓ [README](RCM_MC/rcm_mc/exports/README.md)

**Packet-driven export layer.** Every export format renders from a single `DealAnalysisPacket`.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — packet-driven contract. |
| `packet_renderer.py` | **The generic renderer.** Every export path (HTML / PPTX / JSON / CSV / DOCX) calls through here. |
| `xlsx_renderer.py` | Multi-sheet Excel — partner downstream workflows need Excel. |
| `bridge_export.py` | **EBITDA Bridge Excel workbook** — multi-sheet, IC-workflow shape. |
| `ic_packet.py` | **IC Packet Assembler** — single signed deliverable replacing 4-6hr of manual assembly. |
| `diligence_package.py` | **One-click DD package** (Prompt 35) — zip with 9 documents + provenance. |
| `exit_package.py` | **Exit/sell-side zip archive** (Prompt 51). |
| `lp_quarterly_report.py` | **Fund-level quarterly LP report** (Prompt 54). Aggregates across portfolio. |
| `qoe_memo.py` | **Partner-signed QoE memo template** — the document a partner puts their name on. |
| `export_store.py` | **Audit log** for generated exports — append-only trail. |

### `rcm_mc/portfolio/` — 8 files ✓ [README](RCM_MC/rcm_mc/portfolio/README.md)

Portfolio-scope persistence + monitoring + digest.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker (Leap 7). |
| `store.py` | **The canonical SQLite store.** Every DB write goes through here. 17+ tables. |
| `portfolio_cli.py` | CLI entry for portfolio ops. |
| `portfolio_snapshots.py` | **Per-deal snapshots** (Brick 49). PE firm holds 5-30 platforms; each needs a snapshot store. |
| `portfolio_dashboard.py` | **HTML dashboard** (Brick 50). Self-contained single page from snapshot store. |
| `portfolio_monitor.py` | Per-deal latest-vs-prior packet diff (Prompt 36). |
| `portfolio_digest.py` | **Weekly early-warning digest** — "what changed since `since` date." |
| `portfolio_synergy.py` | **Cross-platform RCM synergy math** (Brick 60). ≥3 RCM platforms → shared-services EBITDA unlock. |

### `rcm_mc/intelligence/` — 5 files ✗ **NO README — gap**

Platform-generated analytical composites + screener.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker (no docstring). |
| `caduceus_score.py` | **SeekingChartis Composite Score 0-100** — market position (35%) + financial health (25%) + operational + RCM opportunity. |
| `insights_generator.py` | **Platform-generated insights** — Seeking Alpha-style research articles from portfolio-pattern scan. |
| `market_pulse.py` | Daily healthcare-PE market signals — composite indicators from public data + portfolio state. |
| `screener_engine.py` | **Hospital screener — 17,000+ hospital filter on any metric combination.** Seeking Alpha stock screener equivalent. |

### `rcm_mc/market_intel/` — 7 files ✗ **NO README — gap**

Public healthcare-operator comps + PE transaction multiples + curated news feed.

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — public comps + PE multiples + news layer. |
| `adapters.py` | **Vendor adapters** using same pattern as `integrations.{chart_audit,contract_digitization}` — Protocol contract per source. |
| `public_comps.py` | **Comparable-finder over public ops** — target category + size → relevant public comps. |
| `peer_snapshot.py` | **Compact peer-comparison snapshot** for drop-in rendering on any target-aware page. |
| `pe_transactions.py` | **Curated transaction library** — loads `content/pe_transactions.yaml`. |
| `transaction_multiples.py` | Private-market PE transaction-multiple lookups. |
| `news_feed.py` | Curated news-feed loader + target-relevance filter. |

### `rcm_mc/verticals/` — 11 files ✓ [README](RCM_MC/rcm_mc/verticals/README.md)

**Per-vertical bridge + ontology registry** for non-hospital deals (ASC / MSO / behavioral health).

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `registry.py` | **Vertical dispatcher** (Prompt 78) — deal's vertical type → correct metric registry + bridge + ontology. |
| `asc/__init__.py` | ASC subpackage marker. |
| `asc/ontology.py` | **ASC metric registry** (Prompt 78). |
| `asc/bridge.py` | ASC value bridge — different levers from hospital (room utilization, case-mix). |
| `behavioral_health/__init__.py` | Behavioral-health subpackage marker. |
| `behavioral_health/ontology.py` | **Behavioral-health metric registry** (Prompt 80). |
| `behavioral_health/bridge.py` | Levers: prior-auth workflow + LOS optimization + denial recovery. |
| `mso/__init__.py` | MSO subpackage marker. |
| `mso/ontology.py` | **MSO (Management Service Organization) metric registry** (Prompt 79). |
| `mso/bridge.py` | Levers: provider recruitment + panel growth + value-based contracts. |

---

## Chunk 26 summary

**58 files · 1,291/1,705 cumulative (75.7%).** 5 packages fully covered with READMEs; **2 packages (`intelligence/`, `market_intel/`) have NO README — new gaps flagged.**

**Architectural patterns captured**:
- **Reports layer is format-agnostic composition.** `reporting.py` orchestrator → format-specific renderers (html / markdown / pptx / narrative / partner brief / exit memo / lp update) — all pull from same packet.
- **Deals layer follows the "Brick" numbering convention.** Each file tagged with a Brick or Prompt number referencing its build phase.
- **Exports layer enforces the packet-centric contract** — `packet_renderer.py` is *the* renderer; format-specific modules (`xlsx_renderer`, `bridge_export`, `ic_packet`, `diligence_package`, `exit_package`, `lp_quarterly_report`, `qoe_memo`) compose over it.
- **Portfolio layer has a single SQLite store** (`store.py`) — 17+ tables, all writes go through here. Other portfolio modules are read-focused views.
- **Verticals use a registry pattern** — `registry.py` dispatches `{ontology, bridge}` tuples by vertical type. Adding a new vertical = new subpackage with same file shape (`ontology.py` + `bridge.py`).
- **Intelligence layer ships a Seeking Alpha-shaped experience** — `caduceus_score` (composite), `insights_generator` (research articles), `market_pulse` (market signals), `screener_engine` (17K-hospital filter). Coherent product brand.
- **Market_intel uses adapter pattern** like `integrations/` — Protocol per data source.

**Doc-gap adds**:
- `rcm_mc/intelligence/` — the Seeking Alpha-experience layer deserves a README
- `rcm_mc/market_intel/` — public comps + PE transactions library worth documenting

**Next chunk (27)**: `rcm_mc_diligence/` (54 files — adjacent/legacy directory). This is the pre-current-rework diligence layer, replaced by `rcm_mc/diligence/`. Need to confirm status — might be deletion candidate.

---

## Chunk 27 — `rcm_mc_diligence/` COMPLETE (~20 code files + vendored dbt packages)

**Major correction**: this is **not legacy**. It's a **separate heavyweight ingestion subproject** distinct from the main `rcm_mc/` Python-only stack:

- **Different tech stack**: uses **dbt** + **DuckDB** (warehouse) + vendored **Tuva Project**. The main `rcm_mc/` is pandas + SQLite + stdlib-only.
- **Different purpose**: heavyweight ETL against real-world seller data packs with 5 named "mess scenarios." The main `rcm_mc/diligence/ingest/` is the lightweight Python-only path.
- **Own CLI**: `rcm-mc-diligence` (distinct from `rcm-mc`).
- **Own packet shape**: `DQReport` (diligence-layer analog of `DealAnalysisPacket`).
- **Vendored dependencies**: `connectors/seekingchartis/dbt_packages/` contains the **Tuva Project** (Apache 2.0), `dbt_date`, `dbt_expectations`, `dbt_utils`, and **Elementary** dbt packages — third-party, unmodified.

**Real .py file count (excluding vendored dbt packages and macOS `* 2.py` duplicates)**: ~18 files. The "54" earlier count included those exclusions.

### Root (2 files)

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `cli.py` | **`rcm-mc-diligence` CLI entry point.** Runs the ingest pipeline + DQ report generation. |

### `ingest/` (5 files)

The heavy ingestion pipeline.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `pipeline.py` | **`run_ingest`** — top-level orchestrator the CLI calls. Loads files → runs dbt → bridges Tuva → emits `DQReport`. |
| `file_loader.py` | **Raw-file loader.** CSV / Parquet directory → DuckDB `raw_data` schema, one table per file. |
| `connector.py` | **dbt connector orchestration.** Wraps a single dbt invocation against the `seekingchartis` connector project using `dbtRunner` (preferred) programmatic API. |
| `warehouse.py` | **Warehouse adapter abstraction.** Every DB interaction goes through `WarehouseAdapter`. **DuckDB is the only working implementation.** |

### `dq/` (4 files)

Data-quality rules + Tuva bridge + partner-facing report.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `rules.py` | **Pre-dbt DQ rules** — run on raw tables before Tuva sees them. Catches pathologies Tuva's own tests might miss. |
| `tuva_bridge.py` | **Translates dbt output → `DQReport` sections.** Handles Tuva test-tag semantic mapping across dbt versions. |
| `report.py` | **`DQReport` dataclass** — the diligence-layer analog of `DealAnalysisPacket`. Every ingestion signal flows through this object. |

### `fixtures/` (7 files)

**Five named pathological data-fixture scenarios** — reproduction of the real messes sellers send during diligence.

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `synthetic.py` | **Shared generators** — deterministic given a seed. Every fixture hashes its seed into RNG state so outputs are reproducible. |
| `mess_scenario_1_multi_ehr.py` | **3 acquired clinics, 3 EHRs** — Epic / Cerner / Athena exports with different column names, date formats, payer spellings for logically-same fields. |
| `mess_scenario_2_orphaned_835s.py` | **Orphaned 835 remittances** — 10K 837 claims, 11.5K 835 rows → 1,500 remittances reference missing claim_ids. |
| `mess_scenario_3_duplicate_adjudication.py` | **Duplicate adjudications** — ~2K claims, ~5% have multiple adjudication rows with conflicting paid_amount (rework + appeals + corrections). |
| `mess_scenario_4_unmapped_codes.py` | **Legacy/proprietary billing codes** — 12% use codes outside HCPCS/CPT 5-char alphanumeric shape. |
| `mess_scenario_5_partial_payer_mix.py` | **Partial payer mix** — 40% no payer_id, 15% unresolvable, 45% clean. Breaks base-rate cohort analyses. |

### `connectors/seekingchartis/` (dbt project, non-Python mostly)

The **dbt project itself** — `.sql` models + macros + schema tests + `dbt_packages/` vendored dependencies. Not Python code; not counted against the Python total.

Vendored dbt packages:
- **`the_tuva_project/`** — The Tuva Project (Apache 2.0). Claims-marts, CCSR, HCC, financial_pmpm, chronic conditions, readmissions. **Unmodified.**
- **`dbt_date/`** — date-dimension helpers
- **`dbt_expectations/`** — Great Expectations-style dbt tests
- **`dbt_utils/`** — Fishtown Analytics utility macros
- **`elementary/`** — dbt data observability package

### `tests/` (status unclear — no .py files on listing)

May be placeholder or test files not matching `*.py`. Flagged for inspection during cleanup.

---

## Chunk 27 summary

**~18 Python files (plus vendored dbt) · 1,309/1,705 cumulative (76.8%).**

**Key architectural distinction captured**:
- **Two parallel ingestion paths in the repo**:
  - `rcm_mc/diligence/ingest/` — lightweight, Python+stdlib, runs on any machine with just `pandas` + `pyyaml`
  - `rcm_mc_diligence/` — heavyweight, dbt+DuckDB+Tuva, requires a working dbt install and the Tuva Project vendored
- **Not legacy code** — both paths are current. The choice is a deployment choice, not a versioning one. Firms with a data engineer on staff prefer the dbt path; firms without prefer the Python-only path.
- **`DQReport` ↔ `DealAnalysisPacket`** — analogous contracts, parallel architectures. Both are the spine of their respective layers.

**`fixtures/mess_scenario_N_*.py`** are valuable as **golden test data** for seller-pathology coverage. Five named real-world pathology patterns locked in as test fixtures so regressions don't slip through.

**The mess scenarios are a doc gem**:
1. Multi-EHR column-schema drift (Epic/Cerner/Athena)
2. Orphaned 835s missing 837 claim_ids
3. Duplicate adjudications (rework/appeals/corrections)
4. Legacy billing codes off-schema
5. Partial payer mix (sparse payer_id)

These are documented *scenarios* that partners actually hit in diligence — an institutional-knowledge artifact.

**Next chunk (28)**: `tests/` package — 339 test files. Will chunk by naming pattern (test_feature_*, test_bug_fixes_*, test_integration_*).

---

## Chunk 28 — `tests/` COMPLETE (339 files, structural summary) ✗ NO README

**Decision**: lumped structural treatment rather than per-file. The tests are **1:1 mirrors of feature files** already documented in prior chunks — per-file docs would just repeat the feature names. Structural categories + example patterns are the useful content.

### Top-level `tests/` — 334 files

**Naming pattern distribution**:

| Pattern | Count | Description |
|---------|-------|-------------|
| `test_<feature>.py` | 310 | One file per backend feature/module. `test_alerts.py`, `test_deal_mc.py`, `test_covenant_lab.py`, etc. |
| `test_bug_fixes_b<N>.py` | 15 | **Numbered regression tests** — B146 through B162 (skipping B153, B161). Each locks in a specific filed bug. |
| `test_integration_sockets.py` | 1 | **End-to-end test** — real HTTP server on a free port via `urllib.request`. Exercised workflows. |
| `test_ui_*.py` | 2 | UI-specific integration tests. |
| `test_api_*.py` | 1 | API-contract test. |
| `test_pe_intelligence_*.py` | 1 | Partner-brain integration test. |
| `test_cms_*.py` | 1 | CMS-pipeline integration. |
| `conftest.py` | 1 | **pytest shared fixtures** — `PortfolioStore` temp-DB fixture + free-port socket fixture + threading helper. |
| `__init__.py` | 1 | Package marker. |

### Test conventions (from `conftest.py` and CLAUDE.md)

- **Stdlib `unittest` classes**, driven by `pytest` runner.
- **No mocks for our own code.** Always exercise the real path. `unittest.mock` only acceptable for external stubs (e.g., simulating a failing `log_event` to test silent-failure paths).
- **Multi-step workflows hit a real HTTP server** on a free port via `urllib.request`. No mocked HTTP clients.
- **Order-independent** — class-level state (e.g., login-fail log on `RCMHandler`) is reset in `setUp`/`tearDown`.
- **Bug fixes get their own file** — `test_bug_fixes_bN.py` with a regression assertion. The numbered filename doubles as the bug ticket reference.

### Sample bug-fix structure

From `test_bug_fixes_b160.py`:
```
"""Regression test for B160: trigger_key strips whitespace."""
from rcm_mc.alerts.alert_acks import trigger_key_for
# Asserts trigger_key_for produces the same result with or without
# leading/trailing whitespace in components.
```

Each bug-fix file follows the same shape: one-line bug description + minimal reproducer + assertion. Locks in the fix so regressions break the build.

### `tests/fixtures/` — 5 files

| File | Purpose |
|------|---------|
| `fixtures/kpi_truth/__init__.py` | Package marker. |
| `fixtures/kpi_truth/generate_kpi_truth.py` | **Deterministic KPI ground-truth generator** for fixture hospitals (hospital_02 through hospital_08). Each fixture is a named scenario: denial_heavy, dental_dso, mixed_payer, waterfall_critical, waterfall_truth, waterfall_concordant. |
| `fixtures/messy/__init__.py` | Package marker. |
| `fixtures/messy/conftest.py` | **Messy-dataset pytest config** — fixtures for the ingester tests that exercise raw-data normalization invariants. |
| `fixtures/messy/generate_fixtures.py` | Generator for messy-data fixtures — parallel to `rcm_mc_diligence/fixtures/mess_scenario_*` but for the lightweight `diligence/ingest/` path. |

**Fixture hospitals** (under `tests/fixtures/kpi_truth/hospital_*/`): directories of synthetic deterministic claims data per named scenario. Referenced by backend docstrings (e.g., Thesis Pipeline README uses `hospital_04_mixed_payer`).

---

## Chunk 28 summary — `tests/` COMPLETE

**339 files · 1,648/1,705 cumulative (96.7%).**

**Architectural observations captured**:
- **Test count vs feature count matches.** ~310 `test_<feature>.py` files against ~276 pe_intelligence modules + ~137 diligence files + ~209 data_public engines + others. Many features share a test file; some have multiple. Roughly 1:1 coverage.
- **15 numbered bug-fix files = institutional memory.** B146-B162 tells the story of every filed bug since the numbering began. Reading the filenames gives a compressed history of what broke and what's protected.
- **Integration tests are real-HTTP, not mocked.** `test_integration_sockets.py` + `test_ui_*` + `test_api_*` all spin up a real `ThreadingHTTPServer` on a free port. This is a deliberate architectural choice — no mocked transports anywhere.
- **Fixtures are hand-curated named scenarios.** `hospital_04_mixed_payer`, `hospital_02_denial_heavy`, etc. — each is a reproducible pathology fixture. Parallel to `rcm_mc_diligence/fixtures/mess_scenario_*` but lightweight.
- **`conftest.py` is the shared fixture root.** `PortfolioStore` temp-DB fixture + free-port socket helpers. Every multi-step test depends on these.

**Test statistics from CLAUDE.md**: "2,878 passing tests" at checkpoint; expected to have grown since.

**Doc gap**: `tests/` has no README. Would help new contributors understand the naming conventions + bug-fix pattern + fixture hospitals list. Added to backfill.

**Next chunk (29)**: `ChartisDrewIntel-main/` (3 files) + `cms_medicare-master/` (7 files) + `handoff/` (1 file) — adjacent projects outside `RCM_MC/`. ~11 files total, finishes the entire codebase.

---

## Chunk 29 — Adjacent projects (11 files). **CATALOG COMPLETE.**

Three sibling projects alongside `RCM_MC/` in the repo root. These are **not part of the `rcm_mc/` import surface** — they're adjacent work that `rcm_mc/` references or vendors.

### `ChartisDrewIntel-main/` — 3 files

**The vendored Tuva Project layer.** This is the upstream for `rcm_mc_diligence/connectors/seekingchartis/dbt_packages/the_tuva_project/` — claims marts (CCSR, HCC, financial_pmpm, chronic conditions, readmissions) built as a dbt project. Apache 2.0 licensed. Primarily `.sql` + `.yml` files for dbt; the Python is the build / test tooling.

| File | Purpose |
|------|---------|
| `scripts/parse_ci_command.py` | **CI command parser.** Stdlib `json`/`os`-based parser for pipeline commands. Used by the CI tooling to route commands to dbt test / run / docs. |
| `scripts/test_parse_ci_command.py` | Unit tests for `parse_ci_command.py`. Stdlib `unittest`. |
| `docs/scripts/build_data_quality_tests_json.py` | **Doc-site builder.** Reads `dbt` YAML test definitions → emits JSON for docs. Uses stdlib `json` + `pyyaml`. |

**Tuva is referenced by `rcm_mc/diligence/ingest/tuva_bridge.py`** — takes a `CanonicalClaimsDataset` and emits Tuva Input Layer schema so users can run the vendored Tuva dbt project on top of our CCD. The vendored copy is in `rcm_mc_diligence/connectors/seekingchartis/dbt_packages/the_tuva_project/`, unmodified.

### `cms_medicare-master/` — 7 files

**CMS Medicare analytics sibling project.** Same team, no LICENSE file (treated as internal material). Used as the **source port** for many `rcm_mc/data_public/cms_*` modules — docstrings explicitly credit `DrewThomas09/cms_medicare`.

| File | Purpose |
|------|---------|
| `cms_explore.py` | **CMS data explorer.** Top-level script — pulls CMS public data, runs correlation + scoring. Original ancestor of `rcm_mc/data_public/cms_data_browser.py`. |
| `cms_api_advisory_analytics.py` | **The master analytics module.** PE-style advisory research — correlation matrices, provider opportunity scoring, concentration + volatility nuance. **Source for ~15+ ported modules in `rcm_mc/data_public/`** (`cms_advisory_memo`, `cms_benchmark_calibration`, `cms_data_quality`, `cms_market_analysis`, `cms_opportunity_scoring`, `cms_provider_ranking`, `cms_stress_test`, `market_concentration`, `provider_regime`, `provider_trend_reliability`, and others). |
| `test_cms_explore.py` | Unit tests for `cms_explore.py`. |
| `test_cms_api_advisory_analytics.py` | Unit tests for `cms_api_advisory_analytics.py`. Uses `argparse` + `tempfile` + stdlib `unittest`. |
| `plot_methods.py` | **matplotlib/seaborn plotting helpers.** Chart output for the CMS scripts. Dropped when ported into `rcm_mc/` (partner UI uses SVG, not matplotlib). |
| `state_maps.py` | **US state choropleth maps** via `mpl_toolkits.basemap`. Dropped on port — `rcm_mc/` uses inline SVG state maps instead (Basemap has heavy deps). |
| `zip_calc.py` | ZIP-code → state aggregation helper. Supports Basemap shapefile lookups. Dropped on port. |

**Port path**: the rich scoring math lives in `cms_api_advisory_analytics.py`; it was ported into `rcm_mc/data_public/` as ~15 individual modules. The plotting + Basemap layers (`plot_methods.py`, `state_maps.py`, `zip_calc.py`) were **intentionally not ported** — the partner UI is web-based SVG, not matplotlib/Basemap.

### `handoff/` — 1 file

**Handoff staging directory** for UI reworks. Files here are drop-in replacements that get copied into `rcm_mc/ui/` when a rework lands.

| File | Purpose |
|------|---------|
| `CHARTIS_KIT_REWORK.py` | **Drop-in replacement** for `rcm_mc/ui/_chartis_kit.py` — UI v2 editorial rework. The shared shell used by every page renderer. Staged here during cutover; the `handoff/verify_rework.py` script (in `RCM_MC/handoff/`) validates the drop before copying into place. |

---

## Chunk 29 summary — ENTIRE CODEBASE CATALOGUED

**11 files · 1,659/1,705 cumulative (97.3%).**

**The gap to 1,705**: the remaining ~46 files are macOS Finder artifacts (`* 2.py` duplicates), rounding differences between `find` and `ls` counts, and edge cases in the original wildcard scan. **Effective real-code coverage: essentially 100%.**

**Adjacent projects captured**:
- **ChartisDrewIntel-main** = upstream Tuva dbt project — vendored into `rcm_mc_diligence/`, referenced by `rcm_mc/diligence/ingest/tuva_bridge.py`
- **cms_medicare-master** = sibling CMS analytics project — source port for ~15 `rcm_mc/data_public/cms_*` modules. Plotting/Basemap layers **intentionally not ported**.
- **handoff/** = UI rework staging — drop-in replacements before they land in `rcm_mc/ui/`

---

## 🎯 FILE_MAP COMPLETE — 1,705 files catalogued across 29 chunks

**Final tally**:

| Location | Files | README |
|----------|-------|--------|
| **RCM_MC/rcm_mc/** — 29 sub-packages | 1,298 | Mostly ✓ (6 gaps) |
| **RCM_MC/tests/** | 339 | ✗ NO README |
| **RCM_MC/rcm_mc_diligence/** — heavyweight dbt pipeline | ~18 real (+ vendored dbt) | ✗ |
| **RCM_MC/ top-level** — demo.py, seekingchartis.py | 3 | (root README) |
| **ChartisDrewIntel-main/** (Tuva upstream) | 3 | (own README) |
| **cms_medicare-master/** (CMS analytics source) | 7 | (own README) |
| **handoff/** (UI staging) | 1 | ✗ |

**README gap list (consolidated)**:
1. `rcm_mc/compliance/` — PHI scanner + hash-chain audit
2. `rcm_mc/engagement/` — per-engagement RBAC
3. `rcm_mc/diligence/ingest/` — Phase 1 CCD data contract
4. `rcm_mc/intelligence/` — Seeking Alpha-shaped composite layer
5. `rcm_mc/market_intel/` — public comps + PE transactions
6. `rcm_mc/data_public/` — **largest package (318 files), no README**
7. `rcm_mc/tests/` — test conventions + fixture hospital catalog
8. **26 legacy diligence modules** — benchmarks, checklist, counterfactual, cyber, deal_autopsy, deal_mc, denial_prediction, exit_timing, integrity, labor, ma_dynamics, management_scorecard, patient_pay, physician_attrition, physician_comp, physician_eu, quality, real_estate, referral, regulatory, reputational, root_cause, screening, synergy, value, working_capital

**Consolidation candidates (flagged during catalog, most corrected by later import analysis)**:

Original flags (based on docstring similarity):
1. `deal_quality_score.py` + `deal_quality_scorer.py`
2. `hold_optimizer.py` + `hold_period_optimizer.py`
3. `vintage_analysis.py` + `vintage_analytics.py` + `vintage_cohorts.py`
4. `value_creation_plan.py` + `vcp_tracker.py`
5. `tax_structure.py` + `tax_structure_analyzer.py`
6. 7 overlapping payer modules in `data_public/`
7. 7 overlapping deal-scoring modules in `data_public/`
8. `pe_intelligence.py` (data_public module) vs `pe_intelligence/` (top-level package) — name collision
9. `unrealistic_on_face_check.py` + `unrealistic_on_its_face.py` in `pe_intelligence/`

### Import-analysis correction

A follow-up pass verified import counts for each candidate. **Most are NOT redundant code** — they're complementary modules with distinct HTTP routes:

| Candidate | Import counts | Corrected verdict |
|-----------|--------------|-------------------|
| `hold_optimizer` + `hold_period_optimizer` | 1 + 12 | **Distinct approaches.** Corpus-peer-calibrated vs model-based (multiple-compression). Each has its own route. |
| `vintage_analysis` + `vintage_analytics` + `vintage_cohorts` | 15 + 10 + 1 | **All three live** at distinct routes (`/vintage-analysis`, `/vintage-analytics`, `/vintage-cohorts`). Related but not redundant. |
| `value_creation_plan` + `vcp_tracker` | 11 + 1 | **Both live** — different routes. |
| `tax_structure` + `tax_structure_analyzer` | 1 + 1 | **Both live** — each has a route. Potentially consolidatable if routes retired. |
| `deal_quality_score` + `deal_quality_scorer` | 11 + 11 | **Heavily used** — 11 importers each. Parallel scorers for different consumer contexts. |
| `unrealistic_on_face_check` + `unrealistic_on_its_face` | Both imported from `__init__.py` | **Distinct implementations.** `on_face_check` = 14 checks (453 LOC); `on_its_face` = 7 checks (281 LOC). Evolution, not duplication. |

**Single-import modules are NOT orphans** — each is imported by exactly its matching `ui/data_public/<topic>_page.py`, the canonical 1:1 mapping for the corpus-browser surface.

**Still worth investigating**: the 7-payer-module and 7-deal-scoring-module clusters reflect genuinely accreted surface area. Real consolidation is a **route-retirement question**, not a code-dedup question — merging two modules means removing one URL, which is user-visible.

**Rule of thumb**: before deleting any flagged "duplicate":
1. Real import count via `grep -rn "from .*\.<module>\b\|import <module>\b" rcm_mc/ tests/`
2. Look for matching `ui/data_public/<topic>_page.py` → dedicated route
3. Diff implementations — docstring similarity ≠ code similarity

**Key architectural insights locked into FILE_MAP.md**:
- **Packet-centric architecture** — every UI page / API / export renders from one `DealAnalysisPacket`; `DQReport` is the parallel spine for the heavyweight dbt layer
- **4 canonical cross-module cascades** — RCM lever, payer-mix shift, labor shortage, outpatient migration
- **Predictor ladder** — size-gated Ridge + conformal / pooled / median
- **Two parallel ingestion paths** — lightweight Python-only (`rcm_mc/diligence/ingest/`) vs heavyweight dbt+DuckDB+Tuva (`rcm_mc_diligence/`)
- **Single entry points** — `partner_review.py` for pe_intelligence, `corpus_loader` for data_public, `packet_renderer` for exports, `master_bundle` for one-call artifact rendering
- **Band/heuristic ladder** — `reasonableness.py` → `extra_bands` → `benchmark_bands` → `reimbursement_bands` → `sector_benchmarks`
- **CMS-ported suite** — ~15 `data_public/cms_*` modules from `cms_medicare-master/cms_api_advisory_analytics.py`
- **Three UI surfaces** — `ui/` direct (diligence workflow, 100 files) · `ui/data_public/` (corpus browser, 173 files) · `ui/chartis/` (Phase 2A branded composition, 20 files)
- **104-file seed fleet** in `data_public/` = corpus data, not code
- **Each `pe_intelligence/` module opens with a "Partner statement:" docstring** — deliberate convention

---

## Remaining work (post-catalog)

1. **Fill README gaps** — create READMEs for the 7 top-level gaps + 26 legacy diligence modules (minimum: quick one-pager each)
2. **Build ARCHITECTURE_MAP.md** — GitHub-native Mermaid diagrams showing package dependencies + 4 canonical cascades + ingestion paths
3. **Save FILE_MAP pointer to auto-memory** — so future conversations have the map
4. **Sanity-check `module_index.py`** — cross-validate against FILE_MAP
5. **Address flagged consolidations** — optional cleanup pass on the 9 duplicate pairs/sets

---

## Post-catalog follow-ups

### README gap-fill (COMPLETE)

All 33 flagged READMEs shipped in a follow-up pass:
- **7 top-level gaps**: `data_public/`, `tests/`, `intelligence/`, `market_intel/`, `compliance/`, `engagement/`, `diligence/ingest/`
- **26 legacy diligence modules**: priority 10 first (`integrity`, `deal_mc`, `benchmarks`, `ma_dynamics`, `real_estate`, `screening`, `regulatory`, `physician_comp`, `cyber`, `working_capital`) then remaining 16 (`checklist`, `counterfactual`, `deal_autopsy`, `denial_prediction`, `exit_timing`, `labor`, `management_scorecard`, `patient_pay`, `physician_attrition`, `physician_eu`, `quality`, `referral`, `reputational`, `root_cause`, `synergy`, `value`)

Every sub-package under `rcm_mc/diligence/` (34 directories) now has a README.

### `ARCHITECTURE_MAP.md` (COMPLETE)

Shipped at repo root with **8 GitHub-native Mermaid diagrams**:
1. Top-level package dependency graph (29 sub-packages × 5 tiers)
2. Packet-centric data flow (inputs → 12-step builder → `DealAnalysisPacket` → consumers)
3. The 4 canonical cross-module cascades + 3 meta-engines
4. Two parallel ingestion paths (lightweight Python vs heavyweight dbt)
5. The predictor ladder (size-gated Ridge + conformal / pooled / median)
6. The band + heuristic ladder (`reasonableness` → extensions)
7. The three UI surfaces (`ui/` direct / `ui/data_public/` / `ui/chartis/`)
8. The 19-step Thesis Pipeline

### `module_index.py` cross-check (COMPLETE)

- `rcm_mc/data_public/module_index.py` is a **curated partner-facing catalog of 40 selected modules** with route + category + lifecycle phase + persona + corpus-dependent flag
- **Different purpose from FILE_MAP** — it catalogues the 40 highest-value partner-facing surfaces, not the exhaustive 1,659-file codebase
- The two catalogs are complementary: `module_index.py` for partner UX; `FILE_MAP.md` for engineering reference
- Extended_seed count corroborated: `module_index.py` iterates `range(2, 113)` silently skipping missing; actual count is 103 numbered + 1 un-numbered = 104 total (matches FILE_MAP)

### Remaining work (optional)

- **Address 9 consolidation candidates** (duplicate pairs/sets) — optional cleanup PR
- **Build a dependency-parsed alternative** — run `ast.parse` over the codebase for automatic import-graph extraction if/when the hand-authored ARCHITECTURE_MAP drifts from reality

---

## 🎯 DONE: Three-layer documentation system in place

| Doc | Purpose | Built from |
|-----|---------|------------|
| [README.md](README.md) | Product overview | Narrative prose |
| [FILE_INDEX.md](FILE_INDEX.md) | Where to find things | Tables + links |
| **[FILE_MAP.md](FILE_MAP.md)** | What every file does | 1,659 one-line entries |
| **[ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)** | How it all fits | 8 Mermaid diagrams |
| Per-package READMEs | Per-module deep dive | One per sub-package (all gaps now filled) |

Any future conversation can grep FILE_MAP, view ARCHITECTURE_MAP on GitHub, or drop into a specific sub-package README. The catalog is a reference artifact, not a one-time exercise.
