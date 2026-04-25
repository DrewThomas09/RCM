# Changelog

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
