# Portfolio

Portfolio-level data store, monitoring, dashboards, and cross-deal analytics. Manages the SQLite-backed deal snapshot store and provides digest, synergy, and monitoring capabilities across the full portfolio.

---

## `store.py` — Core PortfolioStore (SQLite)

**What it does:** The single SQLite connection manager for the entire platform. Every module that reads or writes deal data goes through this store. Manages the 17+ table schema, WAL mode, busy timeout, and FK enforcement.

**How it works:** `PortfolioStore(db_path)` manages a `sqlite3` connection pool with `WAL` mode, `busy_timeout=5000`, and `PRAGMA foreign_keys=ON`. `connect()` is a context manager that returns a `sqlite3.Connection` with row_factory set to `sqlite3.Row`. `init_db()` runs all idempotent `CREATE TABLE IF NOT EXISTS` migrations plus the `infra/migrations.py` registry on startup. Core tables: `deals` (17 columns), `deal_notes`, `deal_tags`, `deal_owners`, `deal_deadlines`, `deal_sim_inputs`, `deal_overrides`, `alert_events`, `alert_acks`, `alert_history`, `analysis_runs`, `portfolio_snapshots`, `audit_events`, `sessions`, `users`, `custom_metrics`, `mc_runs`. Provides `_beta_params_from_mean_sd()` and `extract_primitives_from_config()` utility methods for calibration parameter extraction.

**Data in:** All platform modules write through this store. External data flows in via `data/data_refresh.py` (HCRIS, CMS) and analyst uploads.

**Data out:** SQLite rows to every module via the `connect()` context manager. The single `.db` file is the entire persistent state of the system.

---

## `portfolio_snapshots.py` — Append-Only Deal Snapshots

**What it does:** Records point-in-time deal snapshots at key milestones (IOI, LOI, SPA, close, quarterly re-mark, exit) so the portfolio's history is preserved and auditable.

**How it works:** `portfolio_snapshots` table with deal_id, snapshot_type (ioi/loi/spa/close/quarterly/exit), ev_mm, ebitda_mm, moic_estimate, irr_estimate, stage, notes, created_at, created_by. `record_snapshot()` always inserts (never updates). `latest_per_deal()` uses a `GROUP BY deal_id` with `MAX(created_at)` to return the most recent snapshot per deal — used by the portfolio dashboard. `snapshot_history(deal_id)` returns the full timeline for the deal page.

**Data in:** Analyst-triggered snapshots at stage transitions; quarterly marks from the deal page.

**Data out:** Latest snapshots for the portfolio dashboard; full history for the deal snapshot trail panel.

---

## `portfolio_dashboard.py` — Self-Contained HTML Portfolio Dashboard

**What it does:** Generates the portfolio overview HTML page: weighted MOIC/IRR, stage pipeline funnel, covenant heatmap, and a full deal table. No external JS dependencies — works offline and in email.

**How it works:** Queries `store.py` for all active deals and their latest snapshots. Builds an SVG pipeline funnel, a covenant heatmap (deal × leverage ratio cells colored by distance to covenant), and a KPI banner (deployed capital, weighted MOIC, weighted IRR, average hold). Renders as a single self-contained HTML string using the `ui/_ui_kit.py` shell with inline `<style>` and `<svg>` tags. All numeric formatting follows CLAUDE.md conventions (dollars 2dp, percentages 1dp, multiples 2dp with `x`).

**Data in:** `portfolio/store.py` deal data; `portfolio_snapshots.py` latest snapshots; `deals/health_score.py` health scores.

**Data out:** HTML string for `GET /` and `GET /api/portfolio/dashboard`.

---

## `portfolio_digest.py` — Early-Warning Change Digest

**What it does:** Surfaces only material changes since the last review (new deals, stage moves, covenant crossings, new critical alerts). The "Monday morning" view — not a full re-read, just the diff.

**How it works:** Compares current state to a `last_digest_at` timestamp stored per user. Finds: deals that changed stage since then, deals that crossed a covenant threshold (leverage ratio moved across the 6.0× line), new CRITICAL/HIGH alerts, new deals added. Returns a `DigestReport` with each change categorized and its business implication. The digest timestamp is updated on viewing.

**Data in:** `portfolio/store.py` stage history; `alerts/alert_history.py` new alerts; `pe/debt_model.py` covenant status.

**Data out:** `DigestReport` for the portfolio digest page and optionally emailed via `infra/notifications.py`.

---

## `portfolio_monitor.py` — Per-Deal Delta Detection

**What it does:** Compares a deal's latest `DealAnalysisPacket` against its previous packet and surfaces newly appeared risk flags, threshold crossings, and metric regressions.

**How it works:** Loads the two most recent `analysis_runs` for each deal from `analysis/analysis_store.py`. Performs a structured diff: new risk flags that weren't in the prior packet, risk flags that escalated in severity, metrics that moved across monitoring thresholds (denial rate crossed 12%, AR days crossed 60), MOIC P50 that dropped >0.25× since last run. Returns a `MonitorReport` per deal for the portfolio monitor page.

**Data in:** Last two `DealAnalysisPacket` blobs from `analysis/analysis_store.py`.

**Data out:** `MonitorReport` for the `/portfolio/monitor` page and alert trigger evaluation.

---

## `portfolio_synergy.py` — Cross-Platform RCM Synergy Math

**What it does:** Estimates cross-platform cost synergies from shared denial management teams, shared technology, and consolidated payer contracting across 3+ portfolio companies in the same sector.

**How it works:** Takes a list of portfolio company deal profiles. Computes: (1) shared denial management savings = (combined denial volume × avoided-FTE cost at centralized scale); (2) technology consolidation = (sum of per-company tech spend) × (1 − scale_factor); (3) payer leverage = combined claim volume gives negotiating leverage for a 0.5–2% rate improvement. Returns a `SynergyEstimate` with a dollar range (conservative/base/optimistic) and the assumptions behind each line.

**Data in:** Portfolio company deal profiles from `store.py`; denial team cost benchmarks from `hospital_benchmarks`.

**Data out:** `SynergyEstimate` for the portfolio strategy panel and LP reporting.

---

## `portfolio_cli.py` — Portfolio CLI Entry Point

**What it does:** CLI commands for portfolio store operations: snapshot recording, deal listing, metric queries, and CSV export.

**How it works:** `argparse`-based CLI with subcommands: `snapshot` (record a milestone snapshot), `list` (tabulate all deals), `query` (filter deals by metric thresholds), `export` (dump portfolio to CSV). Wraps `store.py`, `portfolio_snapshots.py`, and `portfolio_dashboard.py`. Entry point for `rcm-mc portfolio` subcommands.

**Data in:** CLI arguments; `portfolio/store.py` data.

**Data out:** Terminal output for the `list` and `query` commands; CSV file for `export`.

---

## Key Concepts

- **Append-only snapshots**: The audit trail from IOI through exit is preserved; `latest_per_deal()` aggregates to current state.
- **Digest over dashboard**: The digest surfaces the *diff* since last review; the dashboard is the point-in-time snapshot. Together they eliminate Monday-morning re-reading.
- **No external JS**: Dashboard renders with inline styles + SVG so it works offline, in email, and pastes into Notion.
