# PE Desk — Data Layer

> What data PE Desk uses, where it lives, how it gets in, and how the app tells partners what's **real vs modeled**. See [PEDESK_OVERVIEW.md](PEDESK_OVERVIEW.md) for the system map and [PEDESK_ALGORITHMS.md](PEDESK_ALGORITHMS.md) for the math that consumes this data.

PE Desk runs on **free public data + a curated realized-deal corpus + seller-provided diligence data**. Nothing is bought. Three things make the data defensible: a single SQLite gateway, a provenance/trust-tagging system on every metric, and honest empty states instead of fabricated numbers.

---

## 1. External data sources

### Core CMS / IRS public sources (`rcm_mc/data/`)
These seven are the orchestrated "data refresh" sources (`data_refresh.KNOWN_SOURCES`). All write into the unified `hospital_benchmarks` table.

| Source | What it is | Key fields | Loader | Scale |
|---|---|---|---|---|
| **CMS HCRIS** (Hospital Cost Reports) | The financial backbone | beds, discharges, case-mix index, gross/net patient revenue, operating expenses/margin, bad debt, charity care, DSH/IME, teaching status, urban/rural, payer-day mix | `data/cms_hcris.py` (loader) + `data/hcris.py` (parser) | shipped pre-parsed `hcris.csv.gz` ≈ **~18k hospital rows** |
| **CMS Care Compare** | Quality + patient experience | star rating, hospital type, HCAHPS experience, complications/readmissions | `data/cms_care_compare.py` | 3 CSVs merged per provider |
| **CMS Medicare Inpatient Utilization** | One row per (provider, DRG) | charge-to-payment ratio, top-DRG volume, service-line concentration (DRG Herfindahl), Medicare discharges | `data/cms_utilization.py` | — |
| **IRS Form 990** | Non-profit hospital filings (~58% of US hospitals) via ProPublica API; cross-checks 990 vs HCRIS (>15% variance flagged) | total revenue, functional expenses, net assets, derived net income | `data/irs990.py` + `irs990_loader.py` + `irs990_trends.py` | per-EIN, cached |
| **CMS Provider of Services (POS)** | Facility ownership file | **chain_identifier** (rollup/sector gold), provider subtype, ownership type, multi-hospital flag | `data/cms_pos.py` → `cms_pos` | quarterly |
| **CMS HRRP** | Readmissions penalty file | readmission penalty %, **dollar penalty exposure** per CCN | `data/cms_hrrp.py` → `cms_hrrp` | per CCN |
| **CMS Hospital General Info** | General attributes | star rating, type, address | `data/cms_hospital_general.py` → `cms_hospital_general` | — |

### Additional CMS-family loaders (own cache tables, not in the core refresh loop)
Open Payments (`cms_open_payments`), Part B / Part D metrics, OPPS outpatient, MA enrollment / benchmarks / star ratings, quality metrics, DRG weights. Plus health context: Census demographics, CDC PLACES county health, AHRQ HCUP discharges, State APCD prices, SEC EDGAR, state regulatory.

### NPPES provider registry
`data_public/nppes_api_client.py` (live CMS NPI Registry API) + `nppes_cache.py` (SQLite cache `nppes_live_cache`, 30-day TTL, keyed by CCN/taxonomy). Per-deal, not bulk — fetched via `rcm-mc data refresh-nppes --ccn ...` during commercial DD. Backs `/hospital/<ccn>/providers`.

### The realized-deal corpus (`rcm_mc/data_public/`)
The empirical anchor for base rates & benchmarking, loaded into the `public_deals` table.
- **`deals_corpus.py`** — `_SEED_DEALS` = **35 real, publicly-disclosed hospital M&A deals** (SEC filings / press releases / investor decks). Schema: source_id, deal_name, year, buyer, seller, ev_mm, ebitda_at_entry_mm, hold_years, **realized_moic, realized_irr**, payer_mix, notes.
- **`extended_seed.py` … `extended_seed_104.py`** — 103 extended-seed batches (~20 deals each).
- **Total ≈ 1,041 deal entries** on disk (verified count). *Caveat: some docstrings cite "~1,815" — that's aspirational; trust the on-disk count or caveat it.*
- **Provenance split** (`corpus_provenance.py`): `_SEED_DEALS` + `extended_seed` are tagged **"real"**; `extended_seed_2`–`104` are tagged **"synthetic"** (a spot-check found fabrications, so the whole range is flagged synthetic and must not be shown to partners as real). Canonical loader: `corpus_loader.load_corpus_deals(mode="all"|"real"|"synthetic")` injects a `provenance` field on every row.

### Computed-from-corpus + ~290 analytic modules
- **Base rates** (`base_rates.py`) — P25/P50/P75 of realized MOIC/IRR, segmented by size/payer/deal-type/buyer (percentiles, because hospital returns are fat-tailed).
- **GP benchmarking / vintage** — `gp_benchmarking_page.py`, `vintage_*` engines, `corpus_vintage_risk_model.py`.
- **~290 analytic data modules** in `data_public/` — each `<topic>.py` engine maps ~1:1 to a `ui/data_public/<topic>_page.py`. Notable: `market_concentration.py` (HHI/CR3/CR5), `medicaid_unwinding.py`, `telehealth_econ.py`, `tax_credits.py`.

## 2. SQLite table registry (~89 tables, grouped)

To enumerate live: `grep -rh "CREATE TABLE IF NOT EXISTS" rcm_mc/ | grep -oE "EXISTS [a-z_][a-z0-9_]*" | sort -u`

- **Portfolio / deals (core):** `deals`, `runs`, `deal_notes`, `deal_tags`, `deal_stars`, `deal_deadlines`, `deal_sim_inputs`, `deal_overrides`, `deal_snapshots`, `deal_stage_history`, `deal_owner_history`, `deal_health_history`, `deal_fund_assignments`, `funds`, `comments`, `custom_metrics`, `covenant_metrics`, `public_deals` (the corpus).
- **Alerts / workflow:** `alert_history`, `alert_acks`, `approval_requests`, `automation_rules`, `automation_log`, `notification_configs`.
- **Analysis / predictions / ML:** `analysis_runs` (the packet cache), `mc_simulation_runs`, `predictions`, `prediction_actuals`, `model_performance_log`, `benchmark_snapshots`, `saved_analyses`, `saved_searches`.
- **Provenance:** `metric_provenance`, `data_room_entries`, `data_room_calibrations`.
- **Engagement (consulting):** `engagements`, `engagement_members`, `engagement_comments`, `engagement_deliverables`, `external_user_assignments`, `team_activity`, `pipeline_hospitals`.
- **Value creation / actuals:** `value_creation_plans`, `value_creation_actuals`, `initiative_actuals`, `quarterly_actuals`.
- **Corpus / CMS caches:** `hospital_benchmarks`, `data_source_status`, `cms_pos`, `cms_hrrp`, `cms_hospital_general`, `cms_open_payments_npi`, `cms_opps_outpatient`, `cms_part_b_metrics`, `cms_part_d_metrics`, `cms_ma_*`, `census_demographics`, `cdc_county_health`, `ahrq_hcup_discharges`, `state_apcd_prices`, `nppes_live_cache`, `irs990_filings`, `pricing_*` (5).
- **Auth / sessions / audit:** `users`, `sessions`, `user_preferences`, `audit_events`, `webhooks`, `generated_exports`, `_migrations`.

### The ~20 most important tables
| Table | Purpose / key columns |
|---|---|
| `deals` | Master deal record. `deal_id` PK, name, `profile_json`, `archived_at` (soft-delete). |
| `runs` | MC sim runs. config_yaml, summary_json, `primitives_json` (per-payer IDR/FWR/DAR mean/sd → empirical priors). |
| `analysis_runs` | **The DealAnalysisPacket cache.** deal_id (CASCADE), as_of, model_version, `packet_json`, `hash_inputs` (cache key). |
| `hospital_benchmarks` | Unified CMS benchmark store. `(provider_id, source, metric_key, period)` unique; value/text_value, quality_flags. |
| `data_source_status` | Refresh-freshness ledger. last_refresh_at, record_count, status (OK/STALE/ERROR). |
| `public_deals` | Realized-deal corpus. ev_mm, ebitda_at_entry_mm, hold_years, realized_moic, realized_irr, payer_mix. |
| `metric_provenance` | Per-metric source ledger. metric_name, value, source, confidence, `upstream_json` (DAG edges). |
| `data_room_entries` | Seller-provided diligence data. ccn, metric, value, sample_size, source, `superseded_by` (supersession chain). |
| `data_room_calibrations` | Bayesian blend: ml_predicted + seller_value → `bayesian_posterior` + CI. This is the "CALIBRATED" source. |
| `predictions` / `prediction_actuals` | ML prediction ledger (conformal CIs) + backtest loop (predicted vs realized). |
| `irs990_filings` | ein, tax_year, ccn, total_revenue/expenses, net_assets. |
| `cms_pos` / `cms_hrrp` | chain_identifier for rollup intel / dollar Medicare penalty exposure. |
| `nppes_live_cache` | Provider roster by CCN/taxonomy, 30-day TTL. |
| `value_creation_plans` / `initiative_actuals` | VCP initiatives + realized actuals (drive launched-vs-realized). |
| `generated_exports` | Export artifacts; `deal_id` FK uses **ON DELETE SET NULL** (survives deal deletion). |
| `users` / `sessions` | scrypt auth + session cookies. |

## 3. Ingestion pipelines

**CLI** (`rcm_mc/cli.py`):
- `rcm-mc data status` — read-only freshness table.
- `rcm-mc data refresh [--source hcris|care_compare|utilization|irs990|cms_pos|cms_general|cms_hrrp|all]` — download + load.
- `rcm-mc data refresh-nppes --ccn <CCN>` — per-CCN live provider roster.

**Orchestrator** (`data/data_refresh.py:refresh_all_sources`): each source is an opaque `(name, refresh_fn)` pair returning records-loaded. **Partial-failure tolerant** — a source exception marks its `data_source_status` row ERROR and the loop continues; produces a `RefreshReport`.

**Download primitive** (`data/_cms_download.py`): atomic `.part` writes, on-disk cache under `$RCM_MC_DATA_CACHE` or `~/.rcm_mc/data/<source>`. `ssl_context()` uses `certifi`'s CA bundle when importable (fixes `CERTIFICATE_VERIFY_FAILED` on python.org macOS builds), else stdlib. Tests monkey-patch `fetch_url` to avoid live CMS hits.

**HCRIS two-step:** the expensive `HOSP10FY{year}.zip → CSV` parse runs once per CMS release; the hot path parses the shipped `hcris.csv.gz` (authoritative, so a refresh doesn't require re-download) into `hospital_benchmarks`.

**Corpus seed:** `corpus_loader.load_corpus_deals()` enumerates the provenance registry, imports each seed module, injects provenance tags, upserts into `public_deals` (idempotent on UNIQUE source_id).

## 4. Provenance & source-tagging (how partners know real vs modeled)

Three layered systems:

**(a) UI source badges** (`ui/provenance.py`) — the trust layer. The `Source` enum, each with a trust level:
| Source | Meaning | Trust |
|---|---|---|
| `HCRIS` | CMS cost-report public filing | **high** |
| `SELLER` | Seller-provided diligence data | **high** |
| `CALIBRATED` | Bayesian posterior blending ML + seller | **high** |
| `COMPUTED` | Derived from other observed values | **high** |
| `ML_PREDICTION` | ML prediction from HCRIS features | **medium** |
| `BENCHMARK` | Industry P50 for hospital type/size | **low** |
| `DEFAULT` | Model default — no hospital-specific data | **low** |

`source_tag(...)` renders an inline badge; `source_tag_with_n(...)` adds sample size ("HCRIS FY2022 (n=5,808)"). `classify_metric_source()` picks the best source by priority **calibrated > seller > hcris > ml > default**.

**(b) Rich provenance DAG** (`provenance/graph.py`) — the "why is this number 8.2%?" explorer. Typed nodes (SOURCE / OBSERVED / PREDICTED / CALCULATED / AGGREGATED / BENCHMARK / CCD_DERIVED) + typed edges (input_to / derived_from / weighted_by / calibrated_against), built on demand per `/api/provenance`.

**(c) Persistent ledger** (`provenance/registry.py`) — the `metric_provenance` table records source + confidence + upstream edges for every metric in a packet build.

**(d) Config source-map** (`data/sources.py`) — classifies config params into **observed / prior / assumed**, computes `observed_fraction()` and an A/B/C/D `confidence_grade()`.

> **Defensibility principle:** the app never presents synthetic/illustrative numbers as real. Synthetic backtests are labeled; the corpus synthetic range is gated; benchmark fallbacks are graded `D`; missing data shows honest empty states, not zeros dressed as values.

## 5. Storage layer (`portfolio/store.py`)

The **only** module that talks to SQLite. Connection PRAGMAs (in the `connect()` context manager):
- `row_factory = sqlite3.Row` — dict-style rows everywhere.
- `PRAGMA busy_timeout = 5000` — 5s retry on lock so concurrent handler threads don't immediately raise "database is locked".
- `PRAGMA foreign_keys = ON` — opt-in per connection (off by default in SQLite) so orphan inserts raise IntegrityError.
- Always `con.close()` on exit (sqlite3's own CM commits/rolls back but doesn't close).

Check-then-write paths wrap `BEGIN IMMEDIATE` (`upsert_deal`, `delete_deal`, `clone_deal`) to serialize and avoid UNIQUE-violation races. **Parameterised SQL only.**

### Delete-policy matrix (five deliberate behaviors — pick one per child table)
| Behavior | When | Examples |
|---|---|---|
| **CASCADE** | derivative analytics meaningless without parent | `analysis_runs`, `mc_simulation_runs`, `deal_overrides` |
| **SET NULL** | audit/export artifact that should survive | `generated_exports.deal_id` |
| **NO ACTION** (default) | operator must clear children first (documented) | `sessions`, `initiative_actuals`, `engagement_*` |
| **soft-delete** | partner-visible, may need undelete | `deal_notes`, `deals.archived_at` |
| **hard-delete** | conceptual parent / write-only log | `deal_overrides` |

`delete_deal()` cascades across ~23 child tables in one `BEGIN IMMEDIATE` transaction.

`store.py` also closes the **calibration loop**: `add_run()` stores per-payer primitives; `export_priors()` aggregates them across runs into Beta/Normal priors written to YAML, feeding back into the simulator.

---
*Caveats flagged during mapping: corpus on-disk count ≈1,041 (not the docstring's ~1,815); table count ≈89 (CLAUDE.md canonical); two HCRIS modules (`hcris.py` heavy parser vs `cms_hcris.py` benchmark loader) and two `ProvenanceGraph` classes (packet snapshot vs rich explorer) are both intentional, not duplicates.*
