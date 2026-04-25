# Changelog

## Unreleased — feature/deals-corpus

### 2026-04-25 — J2 Regulatory-Arbitrage Collapse Detector
- New module: `rcm_mc/data_public/regulatory_arbitrage_collapse.py` — scores every corpus deal against five named regulatory arbitrages (NSA, 340B contract-pharmacy, MA V28 upcoding, Medicaid MCO concentration, ACO REACH transition) on a 0-100 fragility index with a weight-quadratic roll-up
- New UI route `/reg-arbitrage` at `rcm_mc/ui/data_public/regulatory_arbitrage_collapse_page.py` — KPI strip + arbitrage definitions + portfolio rollup + top-25 most-fragile deals + Steward-pattern matches with NF-XX parallels and pre-mortem recommendations
- Word-boundary keyword matcher (`_has_keyword`) prevents short-token substring false positives (the 467→79 high+ deal reduction story); pinned by regression tests
- Steward-pattern flag triggers when ≥3 arbitrages reach high severity; pre-mortem recommendation `STOP` / `PROCEED_WITH_CONDITIONS` / `PROCEED` keyed off composite collapse index
- ProvenanceTracker invariant: 5 `ProvenanceEntry` records per scored deal, every entry carrying a primary-source citation (NSA statute, 45 CFR, HRSA OPAIS, CMS-HCC v28, MedPAC, KFF, MACPAC, CMS Innovation Center)
- 17 unit tests at `tests/test_regulatory_arbitrage_collapse.py` covering positive/negative scoring per arbitrage, Steward stacking, determinism, provenance invariant, score range
- Smoke harness at `tests/test_data_public_smoke.py` extended with backend + UI parametrize entries; full smoke 58/58 green
- Documentation: `docs/CHANGES_2026-04-25.md` records the full ship; README + CHANGELOG cross-link
- Numpy-only · stdlib parsers · DealAnalysisPacket invariant preserved · additive-only modifications to `server.py`, `_chartis_kit.py`, smoke test
- Live numbers (1,705-deal corpus, 745 scored): 235 high-fragility deals, 2 Steward-pattern matches, 22.1 mean collapse index, 3,725 provenance entries

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
