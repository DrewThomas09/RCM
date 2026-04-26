# Report 0167: Database Layer — `initiative_actuals` SQLite Table

## Scope

Schema-walks `initiative_actuals` — the **8th unidentified table** discovered in Report 0157 MR853. Owner: `rcm/initiative_tracking.py:49`. Sister to all prior schema reports (now 16 tables walked).

## Findings

### Schema (rcm/initiative_tracking.py:49-58)

```sql
CREATE TABLE IF NOT EXISTS initiative_actuals (
    init_actual_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    initiative_id TEXT NOT NULL,
    quarter TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ebitda_impact REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
)
```

### Field inventory (7 fields)

| # | Field | Type | NULL? | Note |
|---|---|---|---|---|
| 1 | `init_actual_id` | INTEGER PK AUTOINCREMENT | NO | rowid |
| 2 | `deal_id` | TEXT | NOT NULL | **FK → deals(deal_id)** (no cascade specified — defaults to NO ACTION) |
| 3 | `initiative_id` | TEXT | NOT NULL | free-form initiative key |
| 4 | `quarter` | TEXT | NOT NULL | e.g., "2025Q3" |
| 5 | `created_at` | TEXT | NOT NULL | ISO-8601 |
| 6 | `ebitda_impact` | REAL | NOT NULL | dollar value, can be negative |
| 7 | `notes` | TEXT | (nullable) | free-form |

Plus `UNIQUE INDEX idx_init_actuals ON (deal_id, initiative_id, quarter)` — UPSERT key.

### MAJOR FINDING — 6th FK + 4th NO-ACTION

Per Report 0148 FK frontier "complete":
- CASCADE × 3: analysis_runs, mc_simulation_runs, deal_overrides
- SET NULL × 1: generated_exports
- NO ACTION × 1: sessions

**This iteration adds**: `initiative_actuals.deal_id → deals(deal_id)` with **unspecified cascade (NO ACTION default)**.

**6 FK-bearing tables now confirmed**, **2 of them with unspecified cascade**: sessions + initiative_actuals.

**MR889 below** — Report 0148 FK-frontier-complete claim was premature; PRAGMA comment in Report 0118 missed BOTH `sessions` AND `initiative_actuals`.

### Same NO-ACTION concern as sessions (cross-link MR818 high)

Per Report 0147 MR818: deleting a user with sessions FAILS with IntegrityError. **Same here**: deleting a deal with `initiative_actuals` rows FAILS unless those are pre-cleared.

### Schema inventory progress

After this report: **16 tables walked.** Per Report 0091/0151: 22+ in DB. ~6 unidentified remain.

| Table | Walked? |
|---|---|
| 1-15 (per Report 0148) | ✓ |
| 16. `initiative_actuals` | **0167 (this)** |

### Cross-link to Report 0157 (feat/ui-rework-v3 seeder)

Per Report 0157: feat/ui-rework-v3 seeder writes `initiative_actuals`. Now confirmed: this is the table the seeder targets. **MR853 closes.**

### Importers

`grep "initiative_actuals\|record_initiative_actual"` (not run this iteration). Per Report 0163 cli.py imports `pe.breakdowns.simulate_compare_with_breakdowns` and per CLAUDE.md: initiative tracking feeds variance calculations.

### `notes TEXT` nullable

Free-form notes column. Cross-link Report 0117 MR676 + 0102 MR560 + 0104 MR580 + 0107 + 0117 + 0133 + 0147 free-form pattern. **8th instance** of project-wide free-form-text classification.

### `quarter TEXT` format

Per CLAUDE.md "Dates → ISO-like (`2026Q1` for quarter)". `quarter` is a TEXT column following that convention. **Application-level format discipline.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR889** | **6th FK confirmed: `initiative_actuals.deal_id`** + **`sessions.username`** were BOTH missed by Report 0118 PRAGMA comment | Cross-correction Report 0148 (FK-frontier "complete") was wrong. **There may be more.** Need full PRAGMA cross-check across ALL ~22 tables. | **High** |
| **MR890** | **`initiative_actuals.deal_id` has NO ACTION cascade** | Same risk class as Report 0147 MR818 (sessions). Deleting a deal with actuals fails until those rows cleared. | Medium |
| **MR891** | **`notes TEXT` is 8th free-form-text classification** project-wide | Carried pattern. | (carried) |
| **MR892** | **MR853 CLOSED**: `initiative_actuals` schema-walked. `feat/ui-rework-v3` seeder targets this table per Report 0157. | (closure) |

## Dependencies

- **Incoming:** seeder (per Report 0157 commit 6725a3e), cli (per breakdowns import).
- **Outgoing:** SQLite via store.connect().

## Open questions / Unknowns

- **Q1.** Are there MORE FK-bearing tables not in Report 0118 PRAGMA comment? **Likely.**
- **Q2.** What's `record_initiative_actual` signature?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0168** | Entry point (in flight). |

---

Report/Report-0167.md written.
