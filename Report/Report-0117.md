# Report 0117: Schema / Type Inventory — `mc_simulation_runs` SQLite Table

## Scope

Schema-walks `mc_simulation_runs` table — owned by `RCM_MC/rcm_mc/mc/mc_store.py` (202 lines). Closes Report 0110 MR616 backlog (carried 7+ iterations). Sister to Reports 0017 (deals), 0047 (runs), 0077 (analysis_runs), 0087 (audit_events), 0102 (hospital_benchmarks), 0104 (webhooks/webhook_deliveries), 0107 (data_source_status).

## Findings

### Schema definition (`mc/mc_store.py:25-37`)

```sql
CREATE TABLE IF NOT EXISTS mc_simulation_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    analysis_run_id TEXT,
    scenario_label TEXT NOT NULL DEFAULT '',
    n_simulations INTEGER NOT NULL DEFAULT 0,
    result_json BLOB NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
        ON DELETE CASCADE
)
```

### Field inventory

| # | Field | Type | NULL? | Default | Constraint | Note |
|---|---|---|---|---|---|---|
| 1 | `run_id` | INTEGER PRIMARY KEY AUTOINCREMENT | NO | rowid | PK | per-row id |
| 2 | `deal_id` | TEXT | NOT NULL | — | **FK → deals(deal_id) ON DELETE CASCADE** | references Report 0017 schema |
| 3 | `analysis_run_id` | TEXT | YES | NULL | — | optional cross-ref to `analysis_runs.run_id` (Report 0077) |
| 4 | `scenario_label` | TEXT | NOT NULL | `''` | — | "v2:..." prefix for v2 simulator outputs |
| 5 | `n_simulations` | INTEGER | NOT NULL | 0 | — | Monte Carlo iteration count |
| 6 | `result_json` | BLOB | NOT NULL | — | — | **zlib-compressed JSON** of `MonteCarloResult.to_dict()` |
| 7 | `created_at` | TEXT | NOT NULL | — | — | ISO-8601 UTC |

**7 fields. 1 PRIMARY KEY. 1 FOREIGN KEY (with CASCADE). 1 secondary index.**

### HIGH-PRIORITY DISCOVERY: First foreign key found

**`mc_simulation_runs` is the FIRST audited table with an explicit FOREIGN KEY constraint.**

Cross-reference to prior schema audits:
| Table | FK |
|---|---|
| `deals` (Report 0017) | none |
| `runs` (Report 0047) | none |
| `analysis_runs` (Report 0077) | none (but `deal_id` is the join field) |
| `audit_events` (Report 0087) | none (intentional — denormalized actor) |
| `hospital_benchmarks` (Report 0102) | none |
| `webhooks` / `webhook_deliveries` (Report 0104) | none (no FK between them — Report 0104 MR577) |
| `data_source_status` (Report 0107) | none |
| **`mc_simulation_runs`** (this) | **YES — `deal_id → deals(deal_id) ON DELETE CASCADE`** |

**Schema-discipline inconsistency**: 8+ tables have no FKs; this one does. **MR668 below.** Cross-link Report 0104 MR577 (webhook_deliveries lacks FK to webhooks).

### Index

```sql
CREATE INDEX IF NOT EXISTS ix_mc_deal ON mc_simulation_runs(deal_id, created_at)
```

Composite on `(deal_id, created_at)` — supports the dominant query pattern: "latest run for a deal" via `ORDER BY created_at DESC LIMIT 1`.

### Public API surface (5 functions)

| Function | Line | Signature |
|---|---|---|
| `_ensure_table(store)` | 21 | private, idempotent CREATE |
| `save_mc_run(store, deal_id, result: MonteCarloResult, *, analysis_run_id=None) -> int` | 81 | v1 path |
| `save_v2_mc_run(store, deal_id, result, *, analysis_run_id=None) -> int` | 45 | v2 path; prefixes label `"v2:"` |
| `load_latest_mc_run(store, deal_id, *, scenario_label=None) -> Optional[MonteCarloResult]` | 105 | latest by deal/scenario |
| `list_mc_runs(store, deal_id=None) -> List[Dict[str, Any]]` | 137 | listing without result_json |
| `_mc_from_dict(d) -> MonteCarloResult` | 157 | private rehydrator |

### Storage encoding

`save_mc_run` line 89-90:

```python
payload = json.dumps(result.to_dict(), default=str).encode("utf-8")
blob = zlib.compress(payload, level=6)
```

`load_latest_mc_run` line 130-133:

```python
try:
    payload = zlib.decompress(row["result_json"]).decode("utf-8")
    data = json.loads(payload)
except (zlib.error, json.JSONDecodeError, UnicodeDecodeError):
    return None
```

**zlib level 6 (default).** Same pattern as Report 0077 `analysis_runs.packet_json`. Decode failures → silent None (no logger).

### `MonteCarloResult` dataclass shape (per `_mc_from_dict` lines 184-202)

13 top-level fields:

| Field | Type | Source |
|---|---|---|
| `n_simulations` | int | direct |
| `ebitda_impact` | DistributionSummary | sub-dataclass |
| `moic` | DistributionSummary | sub-dataclass |
| `irr` | DistributionSummary | sub-dataclass |
| `working_capital_released` | DistributionSummary | sub-dataclass |
| `probability_of_negative_impact` | float | direct |
| `probability_of_covenant_breach` | float | direct |
| `probability_of_target_moic` | Dict[str, float] | dict |
| `variance_contribution` | Dict[str, float] | dict |
| `tornado_data` | List[TornadoBar] | sub-dataclass list |
| `histogram_data` | List[HistogramBin] | sub-dataclass list |
| `convergence_check` | ConvergenceReport | sub-dataclass |
| `scenario_label` | str | direct |

### Sub-dataclass shapes

**`DistributionSummary` (per `_ds` whitelist at line 170-172)**: 9 fields — `p5`, `p10`, `p25`, `p50`, `p75`, `p90`, `p95`, `mean`, `std` (all `float`).

**`ConvergenceReport` (per lines 175-183)**: 7 fields — `converged: bool`, `n_simulations: int`, `window: int`, `tolerance: float`, `last_window_range: float`, `recommended_n: int`, `p50_final: float`.

**`TornadoBar`** and **`HistogramBin`** — rehydrated via `**kwargs` (line 198-199) — shape unknown without reading `mc/ebitda_mc.py` (Q3 below).

### Two-version coexistence

`save_mc_run` (v1) and `save_v2_mc_run` (v2) share the SAME table. The v2 variant prefixes `scenario_label` with `"v2:"` (lines 62-64) so consumers can disambiguate. **No `version` column** — discriminator is encoded in the label string itself.

**Per docstring lines 56-59**: "We don't currently ship a typed `load_latest_v2_mc_run` — the JSON blob roundtrips through `V2MonteCarloResult.to_dict()` on write and is read back as a plain dict by the API caller."

So `load_latest_mc_run` ALWAYS returns `MonteCarloResult` (v1 type), not v2. **API consumers reading v2 data via this function get a TYPE MISMATCH** — Pydantic-style validation would catch it; this code does not. **MR669 below.**

### `_mc_from_dict` is hand-written, fragile

Lines 157-202 manually whitelist fields and reconstruct nested dataclasses. **A new field added to `MonteCarloResult` is silently DROPPED on read** unless `_mc_from_dict` is updated.

Cross-link Report 0058 MR417 (PACKET_SCHEMA_VERSION enforcement honor-system) — same risk class. **MR670 below.**

### Importers (5 production + 4 test)

| File | Use |
|---|---|
| `server.py` | likely `/api/mc/...` routes |
| `ui/deal_timeline.py` | timeline rendering |
| `infra/data_retention.py` | **NEW UNMAPPED MODULE** — likely retention/prune for MC runs |
| `infra/consistency_check.py` (Report 0110) | orphan check |
| `portfolio/store.py` | possibly cross-references |

**NEW unmapped module**: `infra/data_retention.py`. Cross-link Report 0087 MR487 (audit retention concern), Report 0117 retention question.

### Test coverage

`tests/test_hardening.py`, `test_infra_hardening.py`, `test_ebitda_mc.py`, `test_v2_monte_carlo.py` — 4 test files reference. Coverage exists; Report 0091 ~280-test backlog.

### Cross-link to schema inventory progress

After this report:

| Table | Walked? |
|---|---|
| `deals` | Report 0017 ✓ |
| `runs` | Report 0047 ✓ |
| `analysis_runs` | Report 0077 ✓ |
| `audit_events` | Report 0087 ✓ |
| `hospital_benchmarks` | Report 0102 ✓ |
| `webhooks` | Report 0104 ✓ |
| `webhook_deliveries` | Report 0104 ✓ |
| `data_source_status` | Report 0107 ✓ |
| **`mc_simulation_runs`** | **0117 ✓** |
| `deal_sim_inputs` | named (Report 0110) |
| `generated_exports` | named (Report 0110) |

**9 walked + 2 named.** Per Report 0091: ≥22 total. ~11+ in backlog.

### `n_simulations DEFAULT 0` schema concern

A row inserted with all fields except `n_simulations` (or n_simulations=0) is **valid per schema** but represents a degenerate "MC ran 0 iterations." No CHECK constraint guards this. **MR671 low.**

### Append-only invariant (per docstring line 4)

> "Append-only so partners can diff runs over time; the `latest` endpoint just picks the most recent row."

**No DELETE in this module.** Retention happens via `infra/data_retention.py` (newly discovered). Cross-link MR487 (audit retention pattern).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR668** | **Schema-discipline inconsistency: 8+ audited tables have NO FKs, this one DOES** | Either FKs should be added project-wide for referential integrity OR this one's FK is the outlier and should be re-evaluated. SQLite FKs are off-by-default per session unless `PRAGMA foreign_keys=ON`. | **High** |
| **MR669** | **`load_latest_mc_run` may return a `MonteCarloResult` for a row written via `save_v2_mc_run`** — type mismatch | v2 result has a different shape; rehydrator drops fields silently. API consumers expecting v2 fields get None/missing. | **High** |
| **MR670** | **`_mc_from_dict` whitelist drops new fields silently** | Adding a field to `MonteCarloResult` requires updating `_mc_from_dict` AND `to_dict`. Easy to forget. | **High** |
| **MR671** | **`n_simulations DEFAULT 0` allows degenerate row** | No CHECK constraint. Could be a "MC ran 0 simulations" row that breaks downstream stats. | Low |
| **MR672** | **`infra/data_retention.py` never reported** | NEW unmapped module discovered in this iteration's importer scan. Cross-link Report 0087 MR487. | **High** |
| **MR673** | **SQLite FOREIGN KEYS need `PRAGMA foreign_keys = ON`** to be enforced | If `PortfolioStore.connect()` (Report 0017) doesn't set this PRAGMA, the FK is **decorative only**. | **High** |
| **MR674** | **Two save variants (`save_mc_run` / `save_v2_mc_run`) into the same table** with no DDL discriminator | Discriminator is `scenario_label LIKE 'v2:%'`. Fragile pattern — a v3 would compound. Should be a `version` INTEGER column. | Medium |
| **MR675** | **Decode failure on `result_json` returns silent None** (lines 132-133) | A corrupt zlib blob makes the whole row vanish from `load_latest_mc_run` without a log. Cross-link Report 0024 logging cross-cut. | Medium |
| **MR676** | **`scenario_label` is free-form TEXT** | Cross-link Report 0087 MR483, Report 0102 MR560, Report 0104 MR580, Report 0107 free-form pattern. Fifth instance now. | (carried) |

## Dependencies

- **Incoming:** server.py (routes), ui/deal_timeline, infra/data_retention, infra/consistency_check, portfolio/store, 4 test files.
- **Outgoing:** stdlib (`json`, `zlib`, `datetime`, `typing`); `mc/ebitda_mc.py` (`MonteCarloResult` + sub-dataclasses); SQLite via `store.connect()`.

## Open questions / Unknowns

- **Q1.** Does `PortfolioStore.connect()` enable `PRAGMA foreign_keys = ON`? **Critical** — answer determines whether MR668's FK actually enforces.
- **Q2.** What's in `infra/data_retention.py`? Retention policy for MC runs (and presumably other tables)?
- **Q3.** `TornadoBar` and `HistogramBin` field shapes (per `mc/ebitda_mc.py`)?
- **Q4.** Schema-walk `deal_sim_inputs` and `generated_exports` next (still in backlog).

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0118** | Read `infra/data_retention.py` (closes Q2, MR672). |
| **0119** | Verify `PortfolioStore.connect()` PRAGMA foreign_keys (closes Q1, MR673). |
| **0120** | Schema-walk `deal_sim_inputs` (Report 0110 MR616 backlog continued). |
| **0121** | Read `_route_quick_import_post` (Report 0114 MR639 confirmation). |

---

Report/Report-0117.md written.
Next iteration should: read `infra/data_retention.py` — closes Q2 + MR672 high (newly discovered unmapped module).
