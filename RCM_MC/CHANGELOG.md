# Changelog

## Unreleased (2026-08-17) — third and fourth sweeps: the bloat, and the duplicates

Two sweeps against the same sentence — **healthcare-PE deal tracking on
top of aggregated CMS data** — narrowing what the product *offers* down
to the three things it does well: display information about hospitals,
health systems and the other outpatient services; scan that universe;
and track deals in the space. Nothing is deleted. All **378** routes,
hidden and visible alike, still return 200, verified against a live
server.

**Third sweep — the named bloat.** Portfolio operations (running your own
book, as opposed to tracking the market), the graphics toolkit (/visuals,
Chart Builder, Pie Chart, Exhibit Composer, Saved Charts, Excel Mapping
and Templates — generators that start empty and draw whatever you type),
the interactive regressions (/portfolio/regression, /ml-insights), the
state-map surfaces (/geo-map, /geo-metrics), the model plumbing, the
deal-workflow chrome, and the HFMA revenue-cycle benchmark bands. The
**Portfolio tab was dropped** from the topbar: every surface under it was
own-book ops, and an empty tab is worse than no tab.

**Fourth sweep — the duplicates and the near-misses.**

- **Nine data catalogs became three.** /data (the canonical inventory),
  /cms-sources (the CMS-specific registry — dataset IDs, granularity,
  cadence, key columns) and /data-quality (the surface that admits what
  is missing) each have a distinct job. The other six duplicated those,
  catalogued data the product does *not* hold (/tools/nonpublic-cms
  describes itself as an internal staging surface over the *credentialed*
  ResDAC/CCW/LDS/RIF programs; /data-apis lists free third-party APIs it
  "can draw on"), or inventoried connectors rather than datasets.
- **A filing, not a model.** /payer-stress, /diligence/payer-stress and
  /cost-structure rode the "X-rays" carve-out through three sweeps. Each
  takes a CCN, seeds two or three real HCRIS figures, then hands the
  reader sliders; /cost-structure's own registry entry concedes its COGS
  / SG&A / labor split "stays illustrative-labeled". The real HCRIS opex
  figures underneath them are on /diligence/hcris-xray, which prints what
  the cost report says. /diligence/hcris-xray, /diligence/xray and
  /diligence/benchmarks remain the X-rays and are pinned by test.
- **Build-your-own analysis** joins the graphics toolkit: /cross-analysis
  (pick an X and a Y, get a Pearson r and a least-squares trendline) and
  /further-analysis (a Tableau-style explorer). The data behind them is
  real; a correlation you configured yourself is not a provider report.
- **Licensed narrative reference** — /industry (IBISWorld-derived),
  /healthcare-verticals and its reference/unit-economics cuts,
  /payer-system ("the four payer-economics CDD exhibits"),
  /benchmark-reference, /market-intel and /market-intel/geo. /market-intel
  reads as live market context and is hand-edited YAML: its own
  public_comps.yaml says "no live API call is made", it was last reviewed
  in April 2026, and its earnings calendar derives dates by adding 90 days
  to the previous report. The CMS-backed /verticals index stays.
- **/predictive-screener** was the last visible surface that
  `classify_surface` still tiered YELLOW — an RCM EBITDA-uplift estimate
  over the illustrative seed corpus, shaped like the screeners that rank
  on filed figures.
- Also hidden: /market-data (an OLS panel and a choropleth over state
  roll-ups /state-rankings already prints, crediting FRED and Capital IQ
  it never reads), /module-index (43 hand-maintained Module() literals
  standing in for the live route registry /tools renders, with sparklines
  its own docstring calls decorative), /global-search (a second results
  page over the same entities as /search), /exports (the output shelf for
  LP updates and IC packets, every producer of which is hidden),
  /comparable-outcomes, /pipeline/bridge and /import.
- **Eleven operator surfaces moved to Internal, not Hidden** — /jobs,
  /runs, /audit, /admin/audit-chain, /admin/data-sources, /ops, /team,
  /guide/context-debug and the three /settings routes. They are wanted
  from the user and admin menus; they are just never carded in a catalog.
- **The keyboard shortcuts were chrome nobody had checked.** The vim-style
  "g + letter" jump table ships on every page and still navigated to
  /portfolio and /diligence/deal after both were hidden. `g o` is gone and
  `g d` points at the /diligence catalog; a test now parses the table
  directly so a future hide cannot leave a shortcut behind.
- Section landings and nav rails were rebuilt around what survived:
  Pipeline gained a "Keep it current" pillar, Research became "Provider
  universes & context" (the universes lead, then rate environment and the
  rule calendar), and Library gained a **Provider identity files** pillar
  — the crosswalk, master NPI, NPPES organization registry, system
  mapping and ownership-cluster CSVs, which no catalog had ever offered.
- Visible surface: **137 → 55**.

## Unreleased (2026-08-16b) — second sweep: deal EXECUTION and single-sector studies

Sharpens the framing from "public-data platform" to what it actually is:
**healthcare-PE deal tracking on top of aggregated CMS data**, with the
X-rays at the centre. That sentence has a seam in it, and this sweep cuts
along it. As before, nothing is deleted — all 137 visible routes and every
hidden one still return 200.

- **Two new rationales** in `_surface_visibility`. `_DEAL_EXECUTION_ROUTES`
  separates *tracking* a transaction (stays: /deal-library + sponsors +
  comps, /verified-deals, /news, /market-scan, /pipeline, /portfolio) from
  the artifacts of *running* one (hidden: IC packets, QoE memos, CDD hub +
  scope, expert calls, CIM cross-check, counterfactuals, covenant stress,
  deal Monte Carlo, autopsies, checklists + question ledgers, value plans,
  roll-up models, LP reporting, /pressure). `_NAMED_ROUTES` carries
  /conferences — a networking planner, not a dataset.
- **Single-sector studies** join the Texas-infusion and IFT suites:
  /radiology-imaging (an atlas organized around named sponsor-backed
  operators) and /market plus its ~80 `/market/<sector>` M&A writeups
  (which include the infusion and interfacility-transport reports by
  name). The line is sector BREADTH, not subject: /nursing-homes,
  /home-health, /hospice, /dialysis, /inpatient-rehab and
  /long-term-care-hospital stay, because each reads a whole CMS program's
  Care Compare universe nationally.
- **The X-rays stay, and now lead.** /diligence is the CMS filing-read
  section: its bar and catalog lead with the HCRIS X-Ray, and its pillars
  became "The X-Rays" and "Regulatory & Outcomes". A test pins the X-rays
  against every future sweep by name.
- Fixed the topbar's global diligence-questions pill (a hidden destination
  reachable from chrome on every page), and repointed ~20 contextual
  "→ next step" links at the filings.
- Visible surface: **173 → 137**.

## Unreleased (2026-08-16) — surface cleanup: hide the pages that aren't public data

Reframes what the platform *offers* around its actual strength: public
CMS / Medicare / Medicaid / hospital data, verifiable to the filing and
visualized in seconds. Pages that work against that promise are now
hidden from every listing surface. **Nothing is deleted** — every route
still serves, so deep links and in-page references keep working.

- **The ruling now lives in one place.** `rcm_mc/ui/_surface_visibility`
  gains `HIDDEN_ROUTES` / `HIDDEN_PREFIXES` + `is_hidden` / `is_visible`
  / `visible_links` / `visible_modules`, alongside the existing
  `INTERNAL_ROUTES`. Three rationales, kept as separate sets so a page's
  reason for hiding stays legible: 172 **illustrative-figure** pages
  (numbers from a hardcoded dataclass, not a filing), the
  **single-study** suites (Texas infusion scan, the IFT/MMT transport
  study — real work, legible only inside one engagement), and the
  **sponsor-corpus / PE-narrative** tail. A hidden route hides its
  sub-paths too. The old `server._TOOLS_ILLUSTRATIVE_ROUTES` was a
  second copy of the first list scoped to /tools only — which is how
  those pages stayed off the card grid while still *leading* the
  Diligence mega-menu; it's gone, and discovery asks the registry.
- **Applied on every listing surface**, not just /tools: the topbar
  mega-menus and their ranked backfill, the Cmd-K palette (caller-supplied
  module lists included), /tools, /best/<section>, every section landing,
  /diligence, /cdd, /module-index, /research, /exports, /industry, the
  app quick-access + deliverable widgets, the deal-profile analytics
  grid, the editorial sidebar rail, checklist evidence links, and global
  search. Counts derive from the filtered lists, so no masthead claims
  surfaces its page doesn't show; a pillar left empty drops rather than
  rendering as a bare heading.
- **Deal trackers stay.** /deal-library, /verified-deals, /news,
  /market-scan and /pipeline follow real, publicly-reported
  transactions — the good version of the corpus idea — and are pinned
  visible by test.
- **Reframed copy** on the surfaces the cleanup emptied: Library is now
  the dataset catalog + "trace a number back to its filing" + the deal
  trackers; Research is now chart-it / provider-universes /
  cross-dataset comparison. Contextual "→ next step" links that pointed
  at newly-hidden pages were repointed at their sourced equivalents
  (e.g. HCRIS X-Ray's "→ Bear Case" dropped; the deal profile's "Run
  Full Pipeline" CTA removed).
- Guarded by `tests/test_hidden_surfaces.py`, which pins both halves of
  the ruling: nothing offers a hidden route, **and** every hidden route
  still returns 200.

## Unreleased (2026-07-05) — UI polish loop: alert rows, chart-label fixes, dev-copy sweep

Two review passes over ~60 partner-facing routes (screenshot-driven,
three parallel reviewers per pass), fixes landed in seven slices.

- **HIGH**: Day One + morning-dashboard alert rows rendered empty —
  the loader read a nonexistent `message` attribute off
  `alerts.Alert` (which carries `title`/`detail`), and the severity
  maps checked critical/high/medium against live red/amber/info
  values. Rows now show headline + detail with correct badge tones.
- **HIGH**: /rcm-benchmarks chart labels were 100× off — `_fmt_value`
  formatted stored fractions without ×100 ("0.1%" beside a table
  showing 11.0%). Charts, tooltips, and gridlines now agree with the
  tables.
- **HIGH**: /payer-stress rendered eight identical scenarios (0.000×
  deltas) with no explanation. The payer-mix regressions genuinely
  carry no signal (R² ≤ 0.0016; bootstrap sign-flips), so the R²
  gate stays — but the page now says so: weak-signal banner,
  "no signal" cells, dash KPI tiles, documented R² floor.
- **MEDIUM**: Command Center KPI cards tile cleanly (uniform 4x1 —
  the 5x2 hero + 4/3 mix left dead holes in the 12-col grid);
  /diligence/risk-workbench no longer stacks a double masthead
  (auto-h1 backstop fired over an as_subhead hero).
- **MEDIUM**: dev-facing copy removed from partner pages:
  /cms-sources Python API-client docs, /deal-library "run
  scripts/ingest…" empty state, /escalations "(future: …)"
  placeholder + "/alerts call", market-intel Yahoo-Finance note,
  rxnorm "a row, not code" captions, risk-workbench "(Prompts G-O)".
- **MEDIUM**: honest-data fixes: market-intel earnings estimates roll
  forward (no more "next expected" dates in the past), /market-data
  state map legend names the HCRIS metric instead of "portfolio
  exposure", insights prose names deals instead of internal ids.
- **LOW**: formatting sweep — activity feed KPIs ($13.00M, not
  ebitda=13000000.0), lp-update change labels, "$26.0B" style on
  healthcare verticals, "21.4M" volumes on radiology atlas,
  -$0.12 EPS, 1dp HCAHPS, thousands separators on Analysis Hub,
  ck_bar_row label track 120→200px (unclips labels platform-wide),
  ck-table styling on /deadlines + /cohorts, /cohorts moved off the
  legacy shell, weekday-aware Day One brief title, screen filter
  chips drop ∞ endpoints, drift-chart label clipping, deal-name
  truncation and SVG label collisions on portfolio monitor.

## Unreleased (2026-07-05) — Tools index: double-render fix, dedup, ?view=all deep link, jump rails

- **HIGH**: /tools no longer renders both views stacked. The inactive
  view carried class `hidden` but no `.ti-main.hidden{display:none}`
  rule existed, so the workspace grid AND the Full A–Z grid were both
  visible — every tool appeared twice (398 cards on a ~23k-px page),
  which read as double counting. One CSS rule collapses the inactive
  view; regression-tested in `test_tools_index_cards.py`.
- **HIGH**: De-duplicated the tools card grid (199 → 187 cards):
  `/diligence/comparable-outcomes`, `/diligence/regulatory-calendar`
  (same renderer + params as their bare Research routes) and
  `/market-data/map` (same combined handler as `/market-data`) are now
  safe-merged into their canonical cards; POST-only
  `/npi-cleaner/{detect,upload}` no longer render as dead 404 tiles
  (fixes `test_every_az_card_returns_200`); byte-serving downloads
  (`/npi-cleaner/sample`, `/rxnorm/export.csv`, the five
  `/diligence/texas-infusion/*.csv`) come off the grid — the owning
  pages carry the download buttons.
- **MEDIUM**: `/tools?view=all` now opens the Full A–Z view
  server-side (the dispatch previously ignored the query and always
  landed on the workspace view, leaving the tools-showcase link
  broken); the client toggle keeps the URL in sync so the view is
  shareable. Removed the unreachable legacy `_route_tools_index_full`
  handler it superseded.
- **MEDIUM**: Jump rails on both /tools views — one chip per
  workspace/bucket (with counts) so partners hop straight to a section
  instead of scrolling ~190 cards; rails hide while a search/status
  filter is active.
- **MEDIUM**: Fixed unclosed `<div>` in the Texas-infusion J-code
  benchmark heat legend that nested the "J-code reference" and
  "Methodology & evidence" panels inside the heatmap panel body.
- **LOW**: NPI Cleaner / Claims Analysis pages no longer print their
  own source-file path in the masthead (`code=` debug kicker removed);
  the engine source note is rewritten in partner language.

## v1.1.0 (2026-05-17) — Ridge predictor: per-cohort α tuning + diagnostic chips

The ridge regression predictor moves from a fixed demo-grade penalty
(`α = 1.0`) to per-cohort RidgeCV with leave-one-out cross-validation.
Adds five orthogonal post-fit diagnostics with literature-anchored
thresholds, surfaces α-disclosure on the analysis workbench, and
versions the prediction ledger so threshold recalibration stays clean
across the methodology cutover. See [`docs/METHODOLOGY_RIDGE.md`](docs/METHODOLOGY_RIDGE.md)
for the partner-facing reference.

- **HIGH**: Per-cohort RidgeCV (was fixed α=1.0); LOO via hat-matrix
  shortcut (Allen 1974 / Hastie ESL §7.10 eq 7.65); alpha grid
  `logspace(-3, 3, 25)`. `EnsemblePredictor` uses the same path so the
  two predictor branches report the same R² (and the same diagnostic
  chips) on the same metric. Cross-validated R² shifts upward
  ~5-15% on most metrics; categorical signals (quality bars,
  reliability grades, validation letter grades) have had their
  thresholds recalibrated to preserve the partner-facing label
  distribution across the methodology change.
- **HIGH**: Five new diagnostic chips fire on per-cohort ridge fits
  when partner-relevant failure modes are detected: `MULTICOLLINEAR`
  (max VIF > 10), `INFLUENTIAL_OUTLIER` (max Cook's D > 4/N),
  `HETEROSCEDASTIC` (Breusch-Pagan p < 0.05, computed via
  Wilson-Hilferty χ² survival without a scipy dependency),
  `HIGH_LEVERAGE` (max hat > 2p/N), `NONLINEAR_PATTERN` (RESET-style
  resid-vs-fitted² t-slope). Multi-fire composes to
  `DIAGNOSTIC_SUSPECT` with all reasons listed in the chip tooltip
  (tier-severity ordered). `R2_NEGATIVE` + Cook's D actually
  recomputes LOO R² without the high-Cook's-D row to verify whether
  the outlier caused the negative R² (rather than assuming).
- **HIGH**: `ALPHA_AT_BOUNDARY` chip fires when RidgeCV picks the
  grid's lowest or highest α AND y has non-trivial variance —
  signals the search grid was too narrow for the cohort. Near-constant
  y legitimately picks the maximum α (over-regularize to mean) and
  correctly does NOT fire the chip.
- **MEDIUM**: α-disclosure inline with the quality bar on workbench
  metric cells (`α=0.43` adjacent to the bar, tooltip carries the
  one-line methodology explanation). Renders only for tuned-α
  predictions; legacy pre-cutover PMs and observed/auto-populated
  sources show nothing extra.
- **MEDIUM**: `methodology_version` column on `predictions` table;
  `_THRESHOLDS_BY_METHODOLOGY` dispatch in
  `rcm_mc/analysis/thresholds.py` routes quality/grade/validation/color
  cutoffs through methodology_version lookup so future
  threshold adjustments touch one file. `/models/validation`
  dashboard defaults to tuned-α only with an opt-in toggle for
  pre-2026-05 legacy rows.
- **MEDIUM**: One-week-TTL calibration-in-progress banner on
  `/analysis/<deal>` while the placeholder thresholds tune to the
  new R² distribution. Auto-removes after 2026-05-25 (date check
  at render time).
- **LOW**: Wilson-Hilferty chi-squared survival approximation
  (Johnson-Kotz-Balakrishnan 1994 §17.6) added inline in
  `rcm_mc/ml/ridge_predictor.py`; precision verified to ±0.01
  p-value against `scipy.stats.chi2.sf` in
  `tests/test_b1_bp_precision.py` (scipy-gated; CI runs it).

## v1.0.0 (2026-04-26) — Reconcile version + audit/fix loop hardening

Brings the CHANGELOG in line with the install-time and runtime sources of truth: `pyproject.toml` and `rcm_mc/__init__.py` both already pin `1.0.0`. Substantive changes since v0.6.1:

- **CRITICAL**: Fixed unparseable `configs/playbook.yaml` — six top-level keys had a leading space, silently breaking the Action Plan section of every HTML report since 2026-04-17. (`33fda80`)
- **CRITICAL**: Tightened `pyarrow` pin from `>=10.0` to `>=18.1,<19.0` to close CVE-2023-47248 (RCE on user-uploaded Parquet) and CVE-2024-52338. (`cb84f07`)
- **CRITICAL**: Restored the broken `rcm-intake` console-script — added the missing `rcm_mc/intake.py` shim mirroring `rcm_mc/lookup.py`. (`5d91bda`)
- **HIGH**: Added a stderr advisory at server startup when bound to a non-loopback host with no auth and no DB users; default laptop flow unchanged. (`9287908`)
- **HIGH**: Blocked future `profiles.yml` commits inside `RCM_MC/` via `.gitignore` while preserving the shipped `profiles.example.yml` template. (`b31aecd`)
- **HIGH**: Fixed `infra/README.md` references to nonexistent `ConfigValidationError` + `write_yaml`; real names are `ConfigError` and `core/calibration.write_yaml`. (`a53321f`)
- **HIGH**: Corrected `CLAUDE.md` SQLite table count (was 17, now ~89 with grep recipe) and Python version (was 3.14, now "Python 3.10+" matching pyproject). (`f4ffdac`, `f1039f8`)

## v0.6.1 (2026-04-25) — Repo cleanup + go-live hardening

### Front-page reorganization
- Moved Heroku artifacts (Procfile, app.json, runtime.txt, requirements.txt, run_local.sh, web/) → `legacy/heroku/`
- Moved vendored projects (ChartisDrewIntel, cms_medicare) → `vendor/`
- Moved cycle summaries + historical docs (SESSION_SUMMARY, COMPUTER_24HOUR_UPDATE, FEATURE_DEALS_CORPUS, NEXT_CYCLE.md, REDESIGN_LOG.md) → `RCM_MC/docs/cycle_summaries/`
- Moved reverted UI handoff → `legacy/handoff/`
- Deleted superseded `RCM_MC/Dockerfile`, `RCM_MC/docker-compose.yml`, `RCM_MC/DEMO.md`, root `docs/` (4 stale files)
- Moved `run_all.sh` + `run_everything.sh` → `RCM_MC/scripts/`

### Azure deploy infrastructure
- New canonical 1-page guide: `AZURE_DEPLOY.md`
- Fixed compose path bug in `vm_setup.sh` and `rcm-mc.service` (was `/opt/rcm-mc/deploy/...`; actual path is `/opt/rcm-mc/RCM_MC/deploy/...`) — would have failed first deploy
- Added `.dockerignore` for lean build context
- Untracked stray SQLite DBs (`seekingchartis.db`, `output v1/portfolio.db`) that would have overwritten production data on `git pull`

### GitHub Actions
- Moved 4 workflows from `RCM_MC/.github/` → `.github/` (workflows only run from repo root)
- Set `defaults.run.working-directory: ./RCM_MC` on ci, release, regression-sweep
- Gated `deploy.yml` to `workflow_dispatch` only until SSH secrets are configured

### Documentation coverage
- Added READMEs to 28 previously-undocumented subfolders: diligence, screening, causal, comparables, ic_memo, ic_binder, qoe, portfolio_monitor, regulatory, pricing, site_neutral, vbc, vbc_contracts, buyandbuild, exit_readiness, irr_attribution, management, montecarlo_v3, negotiation, portfolio_synergy, referral, sector_themes, diligence_synthesis, esg, scripts, rcm_mc_diligence, configs, scenarios
- Updated surface READMEs (top-level, RCM_MC/, ml/, data/, ui/, docs/) for the Apr 2026 cycle
- 15 new strategic planning docs in `RCM_MC/docs/`: PRODUCT_ROADMAP_6MO, BETA_PROGRAM_PLAN, BUSINESS_MODEL, COMPETITIVE_LANDSCAPE, PARTNERSHIPS_PLAN, MULTI_ASSET_EXPANSION, MULTI_USER_ARCHITECTURE, PHI_SECURITY_ARCHITECTURE, INTEGRATIONS_PLAN, REGULATORY_ROADMAP, DATA_ACQUISITION_STRATEGY, LEARNING_LOOP, V2_PLAN, NEXT_CYCLE_PLAN, MD_DEMO_SCRIPT
- Added `tests/test_readme_links.py` (3 tests: surface READMEs, strategy docs, tree-wide subfolders); caught 8 stale-path links during cleanup

### Engineering (Apr 2026 cycle)
- 4 new public-data ingest modules: CDC PLACES, state APCD, AHRQ HCUP, CMS MA enrollment
- 13 new ML predictors: denial rate, days-in-AR, collection rate, forward distress, improvement potential, contract strength, service-line profitability, labor efficiency, volume forecaster, regime detection, ensemble methods, feature importance, geographic clustering, payer-mix cascade
- 14+ reusable UI components: power_table, power_chart, semantic colors, metric tooltips, breadcrumbs+keyboard, skeletons, empty states, responsive utils, dark/light theme toggle, comparison surface, provenance badges, global search, preferences, canonical UI kit

### Verified
- 1,498 / 1,498 `rcm_mc` submodules import cleanly
- 161 / 161 go-live test subset passes (auth + portfolio + alerts + smoke + resilience + exports + pipeline + READMEs)
- All 4 schema migrations apply on fresh DB
- `/health` + `/healthz` return 200 with body `"ok"`
- 0 secrets, `.env`, `.pem`, or DBs tracked
- 109 READMEs scanned, 315 / 316 links resolve (one false positive in vendored dbt-expectations package, excluded from checker)

## v0.5.0 (2026-04-04)

### Phase 1: Fix What is Broken (Steps 1-15)
- Guard against division by zero in type_mix and stage_probs (simulator)
- Added centralized logging module (`rcm_mc.logger`)
- Fixed silent exception swallowing in CLI full-report shock loading
- Removed hardcoded seed=123 from claim bucket generation (uses per-iteration RNG)
- Made backlog stage shift L2/L3 split configurable via `backlog.stage_shift_l2_share`
- Made scrub caps configurable via config `scrub` section
- Fixed unused `cfg` parameter in `scrub_simulation_data`
- Consolidated duplicate defaults between config.py and simulator.py
- Added distribution spec validation (`_validate_dist_spec`)
- Added denial_types structure validation (shares, fwr_odds_mult, stage_bias)
- Added `underpay_delay_spillover` to config validation
- Fixed dead `df_summary` parameter in full_report.py
- Fixed normal_trunc moment calculation (uses scipy truncnorm when available)
- Added scrub statistics to provenance.json output

### Phase 2: Handle Messy Data (Steps 16-30)
- Added `DataQualityReport` with ingestion audit trail
- Extended column name matching with fuzzy/alias mapping
- Added payer name alias resolution (BCBS, UHC, Medi-Cal, etc.)
- Multiple fallback strategies for missing writeoff_amount
- Support for Excel (.xlsx/.xls) file ingestion
- CSV encoding detection (UTF-8, Latin-1, CP1252)
- Smart duplicate handling (dedup by claim_id when available)
- Currency formatting cleanup ($, commas, parentheses)
- Date format auto-detection
- Partial calibration reporting (what was/wasn't calibrated)
- Revenue share auto-inference with 3pp threshold
- Support for pipe and tab delimited files
- Row-level validation with skip-and-report
- Support for multiple data directories
- Automatic data dictionary generation

### Phase 3: Config Flexibility (Steps 31-45)
- Removed mandatory 4-payer constraint (any payer set now works)
- Added payer grouping/alias mapping in config
- Config templates: community_hospital_500m, rural_critical_access
- Config inheritance via `_extends` key
- Per-payer working_days support
- Config diff tool (`--diff` CLI flag)
- Config validation CLI (`--validate-only`)
- Environment variable overrides (`${VAR}` and `${VAR:default}`)
- Schema versioning
- Per-payer denial_mix_concentration
- Configurable appeal stages (not hardcoded to L1/L2/L3)
- Capacity model alternatives: unlimited, outsourced
- Multi-site config structure
- Scenario preset library
- Config export/import (JSON, flattened CSV)

### Phase 4: Engine Hardening (Steps 46-60)
- Standalone capacity module (`rcm_mc.capacity`)
- Progress callback support (every 1000 iterations)
- Simulation timing and performance logging
- Convergence detection with early stopping
- Empirical distribution type
- Per-payer simulation summary
- Centralized RNG manager using SeedSequence
- Batch comparison mode
- Warm-start from prior simulation
- Sobol sensitivity indices module
- Time-series monthly simulation mode

### Phase 5: Testing and Quality (Steps 61-75)
- Added type hints across config, distributions, data_scrub, reporting
- Edge case tests for empty/degenerate DataFrames
- Distribution validation tests
- CLI integration tests
- Property-based distribution tests
- Data contract tests (output schema verification)
- Performance benchmark tests
- Config round-trip tests

### Phase 6: New Capabilities (Steps 76-85)
- Automated anomaly detection on calibration inputs
- Run comparison tool
- Programmatic scenario builder
- Deal screening mode (`--screen`)
- SQLite-based run history
- Natural language result summary
- FastAPI endpoint (`rcm_mc.api`)

### Phase 7: Output and Reporting (Steps 86-95)
- JSON output format (`--json-output`)
- Markdown report generation (`--markdown`)
- Report theme system (default, dark, print, minimal)
- Comparison report (`--compare-to`)
- CSV column documentation
- PowerPoint export module
- Slack/email notification module

### Phase 8: Packaging and DevOps (Steps 96-100)
- pyproject.toml with proper packaging and entry points
- Dockerfile and docker-compose.yml
- Pre-commit hooks configuration
- GitHub Actions CI workflow
- Versioned release workflow

## v0.4.0

Initial production release with Monte Carlo simulation, HTML reporting,
calibration, stress testing, and attribution analysis.
